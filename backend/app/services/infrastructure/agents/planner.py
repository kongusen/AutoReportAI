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

            user_id = ai.user_id or auth_manager.get_current_user_id()
            if not user_id:
                self._logger.warning("⚠️ [Planner] 未提供user_id，将使用全局模型配置")

            # 使用策略管理器构建plan阶段的LLM策略
            plan_llm_policy = llm_strategy_manager.build_llm_policy(
                user_id=user_id,
                stage="plan",
                complexity="high",  # plan阶段总是高复杂度
                output_kind=ai.constraints.output_kind if ai.constraints else "sql"
            )

            llm_result = await self._call_llm(llm_service, plan_prompt, user_id, plan_llm_policy)
            plan = self._parse_plan(llm_result)

            # 标准化Plan JSON，确保结构稳定
            try:
                from .utils.json_utils import normalize_plan
                plan = normalize_plan(plan)
            except Exception:
                pass

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

    async def _call_llm(
        self, llm_service, prompt: str, user_id: str = "system", llm_policy: Dict[str, Any] = None
    ) -> str:
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
        """获取阶段可用工具（简化务实版：两步Schema + 原子工具）"""
        if stage == StageType.TEMPLATE:
            return [
                {"name": "schema.list_tables", "desc": "列出数据库所有表名（不含列）"},
                {"name": "schema.get_columns", "desc": "获取指定表的列信息（必须指定tables）"},
                {"name": "workflow.stat_basic", "desc": "标准计数统计（固定工作流）"},
                {"name": "workflow.stat_ratio", "desc": "比例统计（固定工作流）"},
                {"name": "workflow.stat_category_mix", "desc": "分类构成/占比（固定工作流）"},
                {"name": "sql.validate", "desc": "验证SQL正确性并输出问题"},
                {"name": "sql.policy", "desc": "执行SQL策略检查与LIMIT（大表建议加LIMIT或时间过滤）"},
            ]
        elif stage == StageType.TASK_EXECUTION:
            return [
                {"name": "time.window", "desc": "计算或修正任务执行时间窗口（compare可推导双周期）"},
                {"name": "schema.list_tables", "desc": "列出数据库所有表名（不含列）"},
                {"name": "schema.get_columns", "desc": "获取指定表的列信息（必须指定tables）"},
                {"name": "workflow.stat_basic", "desc": "标准计数统计（固定工作流）"},
                {"name": "workflow.stat_ratio", "desc": "比例统计（固定工作流）"},
                {"name": "workflow.stat_category_mix", "desc": "分类构成/占比（固定工作流）"},
                {"name": "sql_generation", "desc": "基于schema和需求直接生成SQL（LLM主导，非工具调用）"},
                {"name": "sql.validate", "desc": "验证并定位问题"},
                {"name": "sql.refine", "desc": "依据问题修正SQL（命名清晰、口径一致、过滤合理）"},
                {"name": "sql.policy", "desc": "执行SQL策略检查与LIMIT（按策略限制返回规模）"},
                {"name": "sql.execute", "desc": "执行SQL获取数据"},
                {"name": "data.quality", "desc": "执行结果数据质量检查"},
            ]
        else:  # CHART_GENERATION
            return [
                {"name": "schema.list_tables", "desc": "列出数据库所有表名（不含列）"},
                {"name": "schema.get_columns", "desc": "获取指定表的列信息（必须指定tables）"},
                {"name": "workflow.stat_basic", "desc": "标准计数统计（固定工作流）"},
                {"name": "workflow.stat_ratio", "desc": "比例统计（固定工作流）"},
                {"name": "workflow.stat_category_mix", "desc": "分类构成/占比（固定工作流）"},
                {"name": "sql.validate", "desc": "验证SQL正确性并输出问题"},
                {"name": "sql.policy", "desc": "执行SQL策略检查与LIMIT（大表建议加LIMIT或时间过滤）"},
                {"name": "sql.execute", "desc": "执行SQL获取数据"},
                {"name": "data.quality", "desc": "执行结果数据质量检查"},
                {"name": "chart.spec", "desc": "基于执行结果生成图表配置"},
                {"name": "word_chart_generator", "desc": "将ETL数据生成可插入Word的图表"},
            ]

    async def _build_plan_prompt(self, ai: AgentInput, stage: StageType, available_tools: List[Dict[str, str]]) -> str:
        """构建计划提示词 - 支持SQL修复逻辑"""
        # 检查是否处于SQL修复循环中
        sql_fix_context = self._analyze_sql_fix_context(ai)

        if sql_fix_context["in_fix_cycle"]:
            # 构建SQL修复专用提示词
            return await self._build_sql_fix_prompt(ai, sql_fix_context, available_tools)
        else:
            # 正常计划提示词
            return await self._ctrl.build_plan_prompt(ai, stage, available_tools)

    def _analyze_sql_fix_context(self, ai: AgentInput) -> Dict[str, Any]:
        """分析SQL修复上下文"""
        task_context = getattr(ai, 'task_driven_context', {}) or {}
        planning_hints = task_context.get('planning_hints', {})

        # 检查是否有当前SQL和验证问题
        current_sql = task_context.get('current_sql', '')
        validation_issues = planning_hints.get('validation_issues', [])
        last_step = planning_hints.get('last_step', '')

        # 判断是否处于修复循环
        in_fix_cycle = (
            bool(current_sql) and
            bool(validation_issues) and
            last_step in ['sql.validate', 'sql.refine']
        )

        return {
            "in_fix_cycle": in_fix_cycle,
            "current_sql": current_sql,
            "issues": validation_issues,
            "last_step": last_step,
            "warnings": planning_hints.get('warnings', [])
        }

    async def _build_sql_fix_prompt(self, ai: AgentInput, fix_context: Dict[str, Any], available_tools: List[Dict[str, str]]) -> str:
        """构建SQL修复专用提示词"""
        current_sql = fix_context["current_sql"]
        issues = fix_context["issues"]
        warnings = fix_context["warnings"]

        # 获取schema信息
        task_context = getattr(ai, 'task_driven_context', {}) or {}
        schema_summary = task_context.get('schema_summary', '')
        column_details = task_context.get('column_details', {})

        # 构建工具列表
        tools_list = "\n".join([f"- {tool['name']}: {tool['desc']}" for tool in available_tools])

        # 构建问题分析
        issues_text = "\n".join([f"- {issue}" for issue in issues])
        warnings_text = "\n".join([f"- {warning}" for warning in warnings]) if warnings else "无警告"

        return f"""
你是SQL修复专家。当前SQL存在问题，需要你分析并制定修复计划。

当前SQL:
```sql
{current_sql}
```

发现的问题:
{issues_text}

警告信息:
{warnings_text}

数据库Schema信息:
{schema_summary}

可用工具:
{tools_list}

根据问题类型，请制定单步骤修复计划：

问题类型分析:
1. 如果是语法错误（括号不匹配、关键词拼写等）-> 使用 sql.refine 修复
2. 如果是表名/字段名错误 -> 使用 schema.get_columns 获取正确字段，再用 sql.refine 修复
3. 如果是危险关键词误报（如UPDATE在DATE_SUB中）-> 使用 sql.refine 重写避免误报
4. 如果是数据库连接/执行错误 -> 先用 sql.validate 重新验证

请返回JSON格式的修复计划:
{{
    "thought": "问题分析和修复策略",
    "current_state": "SQL存在问题需要修复",
    "next_action": {{
        "action": "tool_call",
        "tool": "选择的工具名",
        "reason": "为什么选择这个工具",
        "input": {{}}
    }},
    "goal_progress": "修复进度描述"
}}

注意事项:
- 每次只执行一个修复步骤
- 优先修复最严重的问题
- 保持原SQL的业务逻辑不变
- 确保修复后的SQL语法正确且可执行
"""

    def _parse_plan(self, text: str) -> Optional[Dict[str, Any]]:
        """解析LLM生成的单步骤决策"""
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

            # 检查是否是新的单步骤格式
            if "next_action" in data and isinstance(data["next_action"], dict):
                # 转换为单步骤格式
                next_action = data["next_action"]
                step = {
                    "action": next_action.get("action", "tool_call"),
                    "tool": next_action.get("tool"),
                    "reason": next_action.get("reason", "执行下一步"),
                    "input": next_action.get("input", {})
                }
                return {
                    "thought": data.get("thought", ""),
                    "current_state": data.get("current_state", ""),
                    "steps": [step],  # 单步骤包装为数组
                    "goal_progress": data.get("goal_progress", ""),
                    "expected_outcome": "sql"
                }
            # 兼容旧格式
            elif "steps" in data and isinstance(data["steps"], list):
                return data
        except Exception as e:
            self._logger.warning(f"单步骤决策解析失败: {e}")
        return None

    def _validate_plan(self, plan: Dict[str, Any], available: List[Dict[str, str]]) -> Dict[str, Any]:
        """验证计划有效性"""
        if not plan or not isinstance(plan.get("steps"), list):
            return {"valid": False, "error": "steps_missing"}

        avail = {a["name"] for a in available}
        for i, step in enumerate(plan["steps"]):
            action = step.get("action", "tool_call")

            # 支持的动作类型
            if action not in ["tool_call", "sql_generation"]:
                return {"valid": False, "error": f"step_{i}_unsupported_action:{action}"}

            # 对于tool_call动作，验证工具是否在可用列表中
            if action == "tool_call":
                if step.get("tool") not in avail:
                    return {"valid": False, "error": f"step_{i}_invalid_tool:{step.get('tool')}"}

            # 对于sql_generation动作，验证是否在可用工具中（作为虚拟工具）
            elif action == "sql_generation":
                if "sql_generation" not in avail:
                    return {"valid": False, "error": f"step_{i}_sql_generation_not_available"}

        return {"valid": True}

    def _fallback_plan(self, ai: AgentInput, stage: StageType) -> Dict[str, Any]:
        """生成智能备用计划 - 基于可用信息动态调整"""

        # 检查Schema可用性
        has_schema = self._check_schema_availability(ai)

        if stage == StageType.TASK_EXECUTION:
            if not has_schema:
                # Schema不可用时，优先获取Schema
                return self._schema_discovery_plan(ai)
            else:
                # Schema可用时，进行SQL生成
                return {
                    "thought": "基本任务：时间→列→起草→验证→策略→执行→质量",
                    "steps": [
                        {"action": "tool_call", "tool": "time.window", "reason": "计算任务时间窗口", "input": {}},
                    {
                        "action": "tool_call",
                        "tool": "schema.list_tables",
                        "reason": "列出所有可用表名，准备选择目标表",
                        "input": {}
                    },
                    {
                        "action": "tool_call",
                        "tool": "schema.get_columns",
                        "reason": "选择与需求最相关的表获取列信息（若未显式指定由Agent智能选择）",
                        "input": {}
                    },
                    {
                        "action": "sql_generation",
                        "reason": "LLM直接生成SQL",
                        "input": {
                            "placeholder": {
                                "description": ai.placeholder.description,
                                "granularity": ai.placeholder.granularity
                            },
                            "schema_info": "from_previous_tool",
                            "time_context": "from_time_window"
                        }
                    },
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
                    {
                        "action": "tool_call",
                        "tool": "schema.list_tables",
                        "reason": "列出所有可用表名，准备选择目标表",
                        "input": {}
                    },
                    {
                        "action": "tool_call",
                        "tool": "schema.get_columns",
                        "reason": "选择与图表数据最相关的表获取列信息",
                        "input": {}
                    },
                    {"action": "sql_generation", "reason": "LLM直接生成用于图表的数据SQL", "input": {
                        "placeholder": {"description": ai.placeholder.description, "granularity": ai.placeholder.granularity},
                        "schema_info": "from_previous_tool"
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
                    {
                        "action": "tool_call",
                        "tool": "schema.list_tables",
                        "reason": "列出所有可用表名，准备选择目标表",
                        "input": {}
                    },
                    {
                        "action": "tool_call",
                        "tool": "schema.get_columns",
                        "reason": "选择目标表获取详细列信息（若未指定由Agent智能选择）",
                        "input": {}
                    },
                    {"action": "sql_generation", "reason": "LLM直接生成参数化SQL", "input": {
                        "placeholder": {"description": ai.placeholder.description, "granularity": ai.placeholder.granularity},
                        "schema_info": "from_previous_tool"
                    }},
                    {"action": "tool_call", "tool": "sql.validate", "reason": "验证SQL", "input": {}},
                ],
                "expected_outcome": "sql",
            }

    def _check_schema_availability(self, ai: AgentInput) -> bool:
        """检查Schema信息是否可用"""
        try:
            # 检查AI输入中是否有Schema信息
            if hasattr(ai, 'schema') and ai.schema:
                if hasattr(ai.schema, 'tables') and ai.schema.tables:
                    return len(ai.schema.tables) > 0

            # 检查task_driven_context中是否有表信息
            if hasattr(ai, 'task_driven_context') and ai.task_driven_context:
                context = ai.task_driven_context
                if isinstance(context, dict):
                    if context.get("tables") and len(context.get("tables", [])) > 0:
                        return True
                    if context.get("schema_summary"):
                        return True

            return False
        except Exception:
            return False

    def _schema_discovery_plan(self, ai: AgentInput) -> Dict[str, Any]:
        """Schema发现计划 - 当Schema不可用时"""
        return {
            "thought": "Schema信息缺失，优先获取数据库结构",
            "steps": [
                {
                    "action": "tool_call",
                    "tool": "schema.list_tables",
                    "reason": "获取所有表名，为后续分析奠定基础",
                    "input": {}
                },
                {
                    "action": "tool_call",
                    "tool": "schema.get_columns",
                    "reason": "获取关键表的列信息，深入了解数据结构",
                    "input": {"batch_size": 5}  # 限制批次大小避免超时
                }
            ],
            "expected_outcome": "schema_info",
            "next_phase": "sql_generation"  # 提示下一阶段应该进行SQL生成
        }
