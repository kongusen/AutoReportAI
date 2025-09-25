"""
统一编排器 (Unified Orchestrator)

实现简洁的PTOF (Plan-Tool-Observe-Finalize) 工作流程:
1. Plan: 生成执行计划
2. Tool: 执行工具序列
3. Observe: 观察和总结
4. Finalize: 最终决策

适配到backup系统的服务容器
"""

import json
import time
import uuid
import logging
from typing import Any, Dict

from .types import AgentInput, AgentOutput
from .planner import AgentPlanner
from .context_prompt_controller import ContextPromptController
from .executor import StepExecutor
from .auth_context import auth_manager
from .config_context import config_manager
from .llm_strategy_manager import llm_strategy_manager


class UnifiedOrchestrator:
    """统一编排器 - 实现PTOF工作流程"""

    def __init__(self, container) -> None:
        """
        初始化编排器

        Args:
            container: backup系统的服务容器
        """
        self.container = container
        self.planner = AgentPlanner(container)
        self.executor = StepExecutor(container)
        self._ctrl = ContextPromptController()
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, ai: AgentInput) -> AgentOutput:
        """
        执行PTOF工作流程

        Args:
            ai: Agent输入

        Returns:
            AgentOutput: 执行结果
        """
        iteration_id = str(uuid.uuid4())

        self._logger.info(f"开始Agent执行 {iteration_id}: {ai.user_prompt}")

        try:
            # Phase 1: Plan - 生成执行计划
            plan_start = time.time()
            plan_result = await self.planner.generate_plan(ai)
            plan_duration = int((time.time() - plan_start) * 1000)

            self._logger.info(f"计划生成完成 {iteration_id}: {plan_duration}ms")

            if not plan_result.get("success"):
                self._logger.error(f"计划生成失败 {iteration_id}: {plan_result}")
                return AgentOutput(False, "", plan_result)

            plan = plan_result["plan"]

            # Phase 2: Tool - 执行工具
            tools_start = time.time()
            exec_result = await self.executor.execute(plan, ai)
            tools_duration = int((time.time() - tools_start) * 1000)

            self._logger.info(f"工具执行完成 {iteration_id}: {tools_duration}ms")

            # Phase 3: Observe - 观察和总结
            observe_start = time.time()
            observation_report = self._build_observation_report(plan, exec_result)
            observe_duration = int((time.time() - observe_start) * 1000)

            self._logger.info(f"观察总结完成 {iteration_id}: {observe_duration}ms")

            # Phase 4: Finalize - 最终决策
            finalize_start = time.time()
            finalize_prompt = self._ctrl.build_finalize_prompt(ai, plan, exec_result)

            # 适配backup系统的LLM服务
            llm_service = getattr(self.container, 'llm_service', None) or getattr(self.container, 'llm', None)
            if not llm_service:
                raise ValueError("LLM service not found in container")

            # 调用LLM生成最终决策
            user_id = ai.user_id or auth_manager.get_current_user_id() or "system"

            # 使用策略管理器构建finalize阶段的LLM策略
            finalize_llm_policy = llm_strategy_manager.build_llm_policy(
                user_id=user_id,
                stage="finalize",
                complexity="high",  # finalize阶段总是高复杂度
                output_kind=ai.constraints.output_kind if ai.constraints else "sql"
            )

            llm_decision = await self._call_llm(llm_service, finalize_prompt, user_id, finalize_llm_policy)
            decision = self._parse_final_decision(llm_decision, ai)
            finalize_duration = int((time.time() - finalize_start) * 1000)

            self._logger.info(f"最终决策完成 {iteration_id}: {finalize_duration}ms")

            # 返回结果
            if decision.get("success"):
                self._logger.info(f"Agent执行成功 {iteration_id}")
                return AgentOutput(True, decision.get("result", ""), decision)
            else:
                self._logger.warning(f"Agent执行失败 {iteration_id}: {decision}")
                return AgentOutput(False, "", decision)

        except Exception as e:
            error = {"error": f"agents_orchestrator_exception: {str(e)}"}
            self._logger.error(f"Agent执行异常 {iteration_id}: {str(e)}")
            return AgentOutput(False, "", error)

    async def _call_llm(self, llm_service, prompt: str, user_id: str = "system", llm_policy: Dict[str, Any] = None) -> str:
        """
        调用LLM服务，适配backup系统的不同接口

        Args:
            llm_service: LLM服务实例
            prompt: 提示词
            user_id: 用户ID

        Returns:
            str: LLM响应
        """
        # 尝试不同的LLM服务接口
        try:
            # 默认LLM策略（如果没有提供）
            if not llm_policy:
                llm_policy = {
                    "stage": "finalize",
                    "complexity": "high",
                    "output_kind": "sql"
                }

            # 尝试方式1: ask方法 (类似当前系统)
            if hasattr(llm_service, 'ask'):
                result = await llm_service.ask(
                    user_id=user_id,
                    prompt=prompt,
                    response_format={"type": "json_object"},
                    llm_policy=llm_policy
                )
                return result.get("response", "{}") if isinstance(result, dict) else (result or "{}")

            # 尝试方式2: generate_response方法
            elif hasattr(llm_service, 'generate_response'):
                result = await llm_service.generate_response(
                    prompt=prompt,
                    user_id=user_id,
                    response_format={"type": "json_object"}
                )
                return result.get("response", "{}") if isinstance(result, dict) else (result or "{}")

            # 尝试方式3: 直接调用
            elif callable(llm_service):
                result = await llm_service(prompt)
                return result

            else:
                raise ValueError("Unsupported LLM service interface")

        except Exception as e:
            self._logger.error(f"LLM调用失败: {str(e)}")
            return '{"success": false, "error": "llm_call_failed"}'

    def _build_observation_report(self, plan: Dict[str, Any], exec_result: Dict[str, Any]) -> str:
        """构建观察报告"""
        obs = exec_result.get("observations", [])
        lines = [
            f"计划步骤: {len(plan.get('steps', []))}",
            f"成功步骤: {exec_result.get('successful_steps', 0)}/{exec_result.get('total_steps', 0)}",
            "",
            "观测记录:",
        ]

        for i, o in enumerate(obs, 1):
            lines.append(f"{i}. {o}")

        # 添加上下文信息
        ctx = exec_result.get("context", {})
        if ctx.get("current_sql"):
            lines.extend(["", f"当前SQL: {ctx['current_sql']}"])
        if ctx.get("execution_result"):
            rows = ctx["execution_result"].get("rows", [])
            lines.append(f"执行行数: {len(rows)}")
        if ctx.get("chart_spec"):
            lines.append("已生成图表配置")
        if ctx.get("chart_image_path"):
            lines.append(f"图表图片路径: {ctx['chart_image_path']}")

        return "\n".join(lines)

    def _parse_final_decision(self, text: str, ai: AgentInput) -> Dict[str, Any]:
        """解析最终决策"""
        try:
            t = (text or "").strip()
            if t.startswith("```json"):
                t = t.replace("```json", "").replace("```", "").strip()

            data = json.loads(t)

            if not isinstance(data.get("success"), bool):
                return {"success": False, "error": "invalid_decision_format"}

            if data.get("success") and not data.get("result"):
                return {"success": False, "error": "missing_result"}

            # SQL结果验证
            if (ai.constraints.output_kind or "sql").lower() == "sql" and data.get("success"):
                sql = str(data.get("result", ""))
                if "SELECT" not in sql.upper():
                    return {"success": False, "error": "invalid_sql_in_decision"}

            return data

        except Exception as e:
            return {
                "success": False,
                "error": f"decision_parse_failed: {str(e)}",
                "raw": text
            }
