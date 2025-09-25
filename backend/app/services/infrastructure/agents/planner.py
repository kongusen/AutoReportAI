"""
Agent计划生成器

基于任务类型和上下文生成结构化的执行计划
输出JSON格式的步骤列表供执行器使用
"""

import json
import logging
from typing import Any, Dict, List, Optional
from enum import Enum

from .types import AgentInput
from .context_prompt_controller import ContextPromptController
from .auth_context import auth_manager
from .config_context import config_manager
from .llm_strategy_manager import llm_strategy_manager


class StageType(Enum):
    """执行阶段类型"""
    TEMPLATE = "template"           # 模板阶段：生成参数化SQL
    TASK_EXECUTION = "task"         # 任务阶段：执行完整数据获取流程
    CHART_GENERATION = "chart"      # 图表阶段：生成图表和可视化


class AgentPlanner:
    """Agent计划生成器"""

    def __init__(self, container) -> None:
        """
        初始化计划生成器

        Args:
            container: backup系统的服务容器
        """
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)
        self._ctrl = ContextPromptController()

    async def generate_plan(self, ai: AgentInput) -> Dict[str, Any]:
        """
        生成执行计划

        Args:
            ai: Agent输入

        Returns:
            Dict: 包含计划的结果
        """
        # 推断执行阶段
        stage = self._infer_stage(ai)
        available_tools = self._get_available_tools(stage)

        self._logger.info(f"推断执行阶段: {stage.value}, 可用工具: {len(available_tools)}个")

        # 构建计划提示词
        plan_prompt = await self._build_plan_prompt(ai, stage, available_tools)

        try:
            # 调用LLM生成计划
            llm_service = getattr(self.container, 'llm_service', None) or getattr(self.container, 'llm', None)
            if not llm_service:
                raise ValueError("LLM service not found in container")

            user_id = ai.user_id or auth_manager.get_current_user_id() or "system"

            # 使用策略管理器构建plan阶段的LLM策略
            plan_llm_policy = llm_strategy_manager.build_llm_policy(
                user_id=user_id,
                stage="plan",
                complexity="high",  # plan阶段总是高复杂度
                output_kind=ai.constraints.output_kind if ai.constraints else "sql"
            )

            llm_result = await self._call_llm(llm_service, plan_prompt, user_id, plan_llm_policy)
            plan = self._parse_plan(llm_result)

            if not plan:
                self._logger.warning("LLM计划解析失败，使用备用计划")
                plan = self._fallback_plan(ai, stage)

            # 验证计划
            validation = self._validate_plan(plan, available_tools)
            if not validation.get("valid"):
                return {
                    "success": False,
                    "error": f"invalid_plan: {validation.get('error')}",
                    "stage": stage.value,
                }

            return {
                "success": True,
                "stage": stage.value,
                "plan": plan,
                "available_tools": available_tools,
            }

        except Exception as e:
            self._logger.error(f"计划生成异常: {e}")
            return {
                "success": False,
                "error": f"planner_exception: {str(e)}",
                "stage": stage.value
            }

    async def _call_llm(self, llm_service, prompt: str, user_id: str = "system", llm_policy: Dict[str, Any] = None) -> str:
        """调用LLM服务生成计划"""
        try:
            # 默认LLM策略（如果没有提供）
            if not llm_policy:
                llm_policy = {
                    "stage": "plan",
                    "complexity": "high",
                    "output_kind": "sql"
                }

            if hasattr(llm_service, 'ask'):
                result = await llm_service.ask(
                    user_id=user_id,
                    prompt=prompt,
                    response_format={"type": "json_object"},
                    llm_policy=llm_policy
                )
                return result.get("response", "{}") if isinstance(result, dict) else str(result)
            elif hasattr(llm_service, 'generate_response'):
                result = await llm_service.generate_response(
                    prompt=prompt,
                    user_id=user_id,
                    response_format={"type": "json_object"}
                )
                return result.get("response", "{}") if isinstance(result, dict) else str(result)
            elif callable(llm_service):
                return await llm_service(prompt)
            else:
                raise ValueError("Unsupported LLM service interface")
        except Exception as e:
            self._logger.error(f"LLM调用失败: {str(e)}")
            return "{}"

    def _infer_stage(self, ai: AgentInput) -> StageType:
        """推断执行阶段"""
        # 图表阶段判断
        if (ai.constraints.output_kind == "chart" or
            ai.placeholder.type == "图表类" or
            "图表:" in ai.placeholder.description or
            "图表：" in ai.placeholder.description):
            return StageType.CHART_GENERATION

        # 任务阶段判断
        if ai.task_driven_context:
            return StageType.TASK_EXECUTION

        # 默认模板阶段
        return StageType.TEMPLATE

    def _get_available_tools(self, stage: StageType) -> List[Dict[str, str]]:
        """获取阶段可用工具"""
        if stage == StageType.TEMPLATE:
            return [
                {"name": "schema.list_columns", "desc": "列出表的列信息（识别维度/度量/时间列）"},
                {"name": "sql.draft", "desc": "根据描述和schema生成SQL（支持ranking的Top N、compare的双周期对比）"},
                {"name": "sql.validate", "desc": "验证SQL正确性并输出问题"},
                {"name": "sql.policy", "desc": "执行SQL策略检查与LIMIT（大表建议加LIMIT或时间过滤）"},
            ]
        elif stage == StageType.TASK_EXECUTION:
            return [
                {"name": "time.window", "desc": "计算或修正任务执行时间窗口（compare可推导双周期）"},
                {"name": "schema.list_columns", "desc": "列出表的列信息（识别维度/度量/时间列）"},
                {"name": "sql.draft", "desc": "生成或更新SQL（ranking可用RANK/LIMIT N，compare输出基准/对比/差值/百分比）"},
                {"name": "sql.validate", "desc": "验证并定位问题"},
                {"name": "sql.refine", "desc": "依据问题修正SQL（命名清晰、口径一致、过滤合理）"},
                {"name": "sql.policy", "desc": "执行SQL策略检查与LIMIT（按策略限制返回规模）"},
                {"name": "sql.execute", "desc": "执行SQL获取数据"},
                {"name": "data.quality", "desc": "执行结果数据质量检查"},
            ]
        else:  # CHART_GENERATION
            return [
                {"name": "schema.list_columns", "desc": "列出表的列信息（识别维度/度量/时间列）"},
                {"name": "sql.draft", "desc": "根据描述和schema生成SQL（图表优先准备x/y/series字段；ranking/compare规则同上）"},
                {"name": "sql.validate", "desc": "验证SQL正确性并输出问题"},
                {"name": "sql.policy", "desc": "执行SQL策略检查与LIMIT（大表建议加LIMIT或时间过滤）"},
                {"name": "sql.execute", "desc": "执行SQL获取数据"},
                {"name": "data.quality", "desc": "执行结果数据质量检查"},
                {"name": "chart.spec", "desc": "基于执行结果生成图表配置"},
                {"name": "word_chart_generator", "desc": "将ETL数据生成可插入Word的图表"},
            ]

    async def _build_plan_prompt(self, ai: AgentInput, stage: StageType, available_tools: List[Dict[str, str]]) -> str:
        """构建计划提示词"""
        return await self._ctrl.build_plan_prompt(ai, stage, available_tools)

    def _parse_plan(self, text: str) -> Optional[Dict[str, Any]]:
        """解析LLM生成的计划"""
        t = (text or "").strip()
        try:
            if t.startswith("{"):
                data = json.loads(t)
            else:
                # 提取JSON块
                start = t.find("{")
                end = t.rfind("}")
                if start >= 0 and end >= 0:
                    data = json.loads(t[start:end + 1])
                else:
                    return None

            if "steps" in data and isinstance(data["steps"], list):
                return data
            elif "tool_calls" in data and isinstance(data["tool_calls"], list):
                # 转换为steps格式
                steps = []
                for call in data["tool_calls"]:
                    steps.append({
                        "action": "tool_call",
                        "tool": call.get("tool"),
                        "reason": call.get("reason") or f"调用{call.get('tool')}工具",
                        "input": call.get("input") or {},
                    })
                return {
                    "thought": data.get("thought", ""),
                    "steps": steps,
                    "expected_outcome": data.get("finalize", {}).get("format", "sql")
                }
        except Exception as e:
            self._logger.warning(f"计划解析失败: {e}")
        return None

    def _validate_plan(self, plan: Dict[str, Any], available: List[Dict[str, str]]) -> Dict[str, Any]:
        """验证计划有效性"""
        if not plan or not isinstance(plan.get("steps"), list):
            return {"valid": False, "error": "steps_missing"}

        avail = {a["name"] for a in available}
        for i, step in enumerate(plan["steps"]):
            if step.get("action") != "tool_call":
                return {"valid": False, "error": f"step_{i}_unsupported_action"}
            if step.get("tool") not in avail:
                return {"valid": False, "error": f"step_{i}_invalid_tool:{step.get('tool')}"}

        return {"valid": True}

    def _fallback_plan(self, ai: AgentInput, stage: StageType) -> Dict[str, Any]:
        """生成备用计划"""
        if stage == StageType.TASK_EXECUTION:
            return {
                "thought": "基本任务：时间→列→起草→验证→策略→执行→质量",
                "steps": [
                    {"action": "tool_call", "tool": "time.window", "reason": "计算任务时间窗口", "input": {}},
                    {"action": "tool_call", "tool": "schema.list_columns", "reason": "确认列信息", "input": {"tables": ai.schema.tables}},
                    {"action": "tool_call", "tool": "sql.draft", "reason": "生成SQL", "input": {
                        "placeholder": {"description": ai.placeholder.description, "granularity": ai.placeholder.granularity},
                        "schema": {"tables": ai.schema.tables, "columns": ai.schema.columns},
                    }},
                    {"action": "tool_call", "tool": "sql.validate", "reason": "验证SQL", "input": {}},
                    {"action": "tool_call", "tool": "sql.policy", "reason": "策略检查与加LIMIT", "input": {}},
                    {"action": "tool_call", "tool": "sql.execute", "reason": "执行SQL获取数据", "input": {}},
                    {"action": "tool_call", "tool": "data.quality", "reason": "检查数据质量", "input": {}},
                ],
                "expected_outcome": "sql",
            }
        elif stage == StageType.CHART_GENERATION:
            return {
                "thought": "图表任务：列→起草→验证→执行→图表配置→图片",
                "steps": [
                    {"action": "tool_call", "tool": "schema.list_columns", "reason": "确认列信息", "input": {"tables": ai.schema.tables}},
                    {"action": "tool_call", "tool": "sql.draft", "reason": "生成用于图表的数据SQL", "input": {
                        "placeholder": {"description": ai.placeholder.description, "granularity": ai.placeholder.granularity},
                        "schema": {"tables": ai.schema.tables, "columns": ai.schema.columns},
                    }},
                    {"action": "tool_call", "tool": "sql.validate", "reason": "验证SQL", "input": {}},
                    {"action": "tool_call", "tool": "sql.policy", "reason": "策略检查与加LIMIT", "input": {}},
                    {"action": "tool_call", "tool": "sql.execute", "reason": "执行SQL获取图表数据", "input": {}},
                    {"action": "tool_call", "tool": "data.quality", "reason": "检查图表数据质量", "input": {}},
                    {"action": "tool_call", "tool": "chart.spec", "reason": "生成图表配置", "input": {}},
                    {"action": "tool_call", "tool": "word_chart_generator", "reason": "生成图片", "input": {}},
                ],
                "expected_outcome": "chart",
            }
        else:  # TEMPLATE
            return {
                "thought": "模板任务：列→起草→验证",
                "steps": [
                    {"action": "tool_call", "tool": "schema.list_columns", "reason": "确认列信息", "input": {"tables": ai.schema.tables}},
                    {"action": "tool_call", "tool": "sql.draft", "reason": "生成参数化SQL", "input": {
                        "placeholder": {"description": ai.placeholder.description, "granularity": ai.placeholder.granularity},
                        "schema": {"tables": ai.schema.tables, "columns": ai.schema.columns},
                    }},
                    {"action": "tool_call", "tool": "sql.validate", "reason": "验证SQL", "input": {}},
                ],
                "expected_outcome": "sql",
            }
