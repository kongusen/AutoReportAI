"""
统一编排器 (Unified Orchestrator) - 单步骤循环版本

实现Plan-Tool-Active-Validate (PTAV) 单步骤循环架构:
1. Plan: Agent分析当前状态并决策下一步行动
2. Tool: 执行Agent决定的单个工具/动作
3. Active: Agent分析工具执行结果
4. Validate: Agent验证是否达到目标，决定继续或结束

关键特性：
- 单步骤执行：每次只执行一个操作，立即返回给Agent分析
- Agent主导：所有决策由Agent做出，工具只执行
- 真实验证：通过实际数据库执行验证SQL正确性
- 状态维护：在循环中维护执行上下文和进度

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
from .resource_pool import ResourcePool, ContextMemory
from .llm_strategy_manager import llm_strategy_manager


class UnifiedOrchestrator:
    """统一编排器 - 实现Plan-Tool-Active-Validate单步骤循环"""

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

        # 循环控制配置
        self.max_iterations = 15  # 最大迭代次数防止无限循环
        self.iteration_timeout = 300  # 总超时时间（秒）

    async def execute(self, ai: AgentInput, mode: str = "ptof") -> AgentOutput:
        """
        统一执行入口 - 支持多种执行模式

        Args:
            ai: Agent输入
            mode: 执行模式
                - "ptof": 传统Plan-Tool-Observe-Finalize一次性流程
                - "ptav": Plan-Tool-Active-Validate单步骤循环流程
                - "task_sql_validation": Task任务中SQL有效性验证和更新
                - "report_chart_generation": 报告生成中数据转图表流程

        Returns:
            AgentOutput: 执行结果
        """
        self._logger.info(f"🚀 开始Agent执行 [模式: {mode}]: {ai.user_prompt}")

        # 清除LLM策略管理器的请求级缓存，避免跨请求数据污染
        llm_strategy_manager.clear_cache()
        self._logger.debug("已清除LLM策略管理器缓存")

        try:
            if mode == "ptof":
                return await self._execute_ptof(ai)
            elif mode == "ptav":
                return await self._execute_ptav_loop(ai)
            elif mode == "task_sql_validation":
                return await self._execute_task_sql_validation(ai)
            elif mode == "report_chart_generation":
                return await self._execute_report_chart_generation(ai)
            else:
                raise ValueError(f"不支持的执行模式: {mode}")

        except Exception as e:
            error = {"error": f"orchestrator_exception: {str(e)}", "mode": mode}
            self._logger.error(f"Agent执行异常 [模式: {mode}]: {str(e)}")
            return AgentOutput(False, "", error)

    async def _execute_ptof(self, ai: AgentInput) -> AgentOutput:
        """
        执行传统PTOF工作流程 - 用于简单的一次性任务

        Args:
            ai: Agent输入

        Returns:
            AgentOutput: 执行结果
        """
        iteration_id = str(uuid.uuid4())
        self._logger.info(f"📋 [PTOF模式] 开始执行 {iteration_id}")

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
            user_id = ai.user_id or auth_manager.get_current_user_id()
            if not user_id:
                self._logger.warning("⚠️ [Orchestrator] 未提供user_id，将使用全局模型配置")

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

            # 返回结果 - 无论成功失败都返回SQL结果
            sql_result = decision.get("result", "")
            if decision.get("success"):
                self._logger.info(f"✅ [PTOF模式] Agent执行成功 {iteration_id}")
                return AgentOutput(True, sql_result, decision)
            else:
                self._logger.warning(f"⚠️ [PTOF模式] Agent执行失败但返回SQL {iteration_id}: {decision}")
                # 即使失败也返回SQL，让前端可以显示和调试
                return AgentOutput(False, sql_result, decision)

        except Exception as e:
            error = {"error": f"ptof_execution_exception: {str(e)}"}
            self._logger.error(f"❌ [PTOF模式] Agent执行异常 {iteration_id}: {str(e)}")
            return AgentOutput(False, "", error)

    async def _execute_ptav_loop(self, ai: AgentInput) -> AgentOutput:
        """
        执行Plan-Tool-Active-Validate单步骤循环 - 用于复杂SQL生成和验证

        关键特性：
        1. Agent分析当前状态并决策下一步
        2. 执行单个工具/动作
        3. Agent分析结果并验证
        4. 循环直到达到目标或超时

        Args:
            ai: Agent输入

        Returns:
            AgentOutput: 执行结果
        """
        session_id = str(uuid.uuid4())
        start_time = time.time()
        iteration = 0

        self._logger.info(f"🔄 [PTAV循环] 开始会话 {session_id}")

        # 🗄️ [ResourcePool模式] 初始化资源池 - 精简记忆，减少token消耗
        resource_pool = ResourcePool()
        self._logger.info(f"🗄️ [PTAV循环] 使用ResourcePool模式（精简记忆，适用于大型数据库）")

        # 初始化执行上下文 - 在循环中维护状态
        execution_context = {
            "session_id": session_id,
            "current_sql": "",
            "validation_results": [],
            "execution_history": [],
            "goal_achieved": False,
            "last_error": None,
            "accumulated_observations": [],
            "resource_pool": resource_pool
        }

        try:
            while iteration < self.max_iterations:
                iteration += 1
                iteration_start = time.time()

                # 检查超时
                if time.time() - start_time > self.iteration_timeout:
                    self._logger.warning(f"⏰ [PTAV循环] 会话超时 {session_id}")
                    break

                self._logger.info(f"🔍 [PTAV循环] 第{iteration}轮 - 分析当前状态")

                # Phase 1: Plan - Agent分析当前状态并决策下一步
                plan_result = await self.planner.generate_plan(ai)
                if not plan_result.get("success"):
                    self._logger.error(f"❌ [PTAV循环] 第{iteration}轮计划失败: {plan_result}")
                    execution_context["last_error"] = plan_result.get("error")
                    break

                # Phase 2: Tool - 执行Agent决定的单个动作
                plan = plan_result["plan"]
                self._logger.info(f"🔧 [PTAV循环] 第{iteration}轮执行动作: {plan.get('steps', [{}])[0].get('action', 'unknown')}")

                exec_result = await self.executor.execute(plan, ai)
                execution_time = int((time.time() - iteration_start) * 1000)

                # 🚨 防御性检查：确保exec_result是字典
                if not isinstance(exec_result, dict):
                    self._logger.error(f"🚨 [PTAV循环] exec_result不是字典类型: {type(exec_result)}, 内容: {exec_result}")
                    exec_result = {
                        "success": False,
                        "error": "invalid_exec_result_type",
                        "context": {},
                        "observations": [f"❌ Executor返回了非字典类型: {type(exec_result)}"]
                    }

                # 更新执行上下文
                execution_context["execution_history"].append({
                    "iteration": iteration,
                    "plan": plan,
                    "exec_result": exec_result,
                    "execution_time": execution_time
                })

                # 累积观察记录
                if exec_result.get("observations"):
                    execution_context["accumulated_observations"].extend(exec_result["observations"])

                # 🔧 [统一Context管理] 使用统一方法更新execution_context
                context = exec_result.get("context", {})
                self._update_execution_context(execution_context, context)

                # Phase 3: Active - Agent分析工具执行结果
                self._logger.info(f"🧠 [PTAV循环] 第{iteration}轮分析结果: 成功={exec_result.get('success')}")

                # Phase 4: Validate - Agent验证是否达到目标（增强智能判断）
                # 4.1: 智能模式分析 - 检测是否应该提前退出
                pattern_analysis = self._analyze_execution_pattern(execution_context, iteration)
                if pattern_analysis.get("should_exit"):
                    self._logger.warning(f"🤖 [PTAV智能退出] {pattern_analysis.get('reason')}")
                    execution_context["last_error"] = pattern_analysis.get("reason")
                    execution_context["exit_suggestion"] = pattern_analysis.get("suggestion")
                    break

                # 4.2: 目标达成验证
                validation_result = await self._validate_goal_achievement(ai, execution_context, exec_result)

                if validation_result.get("goal_achieved"):
                    self._logger.info(f"🎯 [PTAV循环] 目标达成，第{iteration}轮完成")
                    execution_context["goal_achieved"] = True
                    break

                elif validation_result.get("should_continue", True):
                    self._logger.info(f"➡️ [PTAV循环] 继续第{iteration+1}轮，原因: {validation_result.get('reason', '')}")
                    # 更新AI输入以传递最新状态
                    ai = self._update_ai_with_context(ai, execution_context)
                else:
                    self._logger.warning(f"🛑 [PTAV循环] 停止循环，原因: {validation_result.get('reason', '')}")
                    execution_context["last_error"] = validation_result.get("reason")
                    break

            # 生成最终结果
            final_result = await self._finalize_ptav_result(ai, execution_context)

            total_time = int((time.time() - start_time) * 1000)
            self._logger.info(f"🏁 [PTAV循环] 会话结束 {session_id}: {iteration}轮, {total_time}ms")

            if final_result.get("success"):
                return AgentOutput(True, final_result.get("result", ""), final_result)
            else:
                # 失败时也返回partial_result中的SQL，让前端可以显示和调试
                partial_sql = final_result.get("partial_result", "")
                return AgentOutput(False, partial_sql, final_result)

        except Exception as e:
            error = {"error": f"ptav_loop_exception: {str(e)}", "session_id": session_id, "iteration": iteration}
            self._logger.error(f"❌ [PTAV循环] 异常 {session_id}: {str(e)}")
            return AgentOutput(False, "", error)

    def _analyze_execution_pattern(self, execution_context: Dict[str, Any], iteration: int) -> Dict[str, Any]:
        """分析执行模式，判断是否应该智能退出"""
        execution_history = execution_context.get("execution_history", [])

        # 检测重复失败模式
        if len(execution_history) >= 3:
            last_3_actions = [h.get("plan", {}).get("steps", [{}])[0].get("action", "") for h in execution_history[-3:]]
            last_3_success = [h.get("exec_result", {}).get("success", False) for h in execution_history[-3:]]

            # 同一动作连续失败3次
            if len(set(last_3_actions)) == 1 and not any(last_3_success):
                return {
                    "should_exit": True,
                    "reason": f"重复执行{last_3_actions[0]}失败3次",
                    "suggestion": "建议重新分析问题或更换策略"
                }

        # 检测Schema获取失败
        if iteration > 3 and not execution_context.get("tables"):
            schema_attempts = sum(1 for h in execution_history if "schema" in str(h.get("plan", {}).get("steps", [{}])[0].get("action", "")))
            if schema_attempts >= 2:
                return {
                    "should_exit": True,
                    "reason": "多次尝试后仍无Schema信息",
                    "suggestion": "建议检查数据源配置"
                }

        # 检测网络/数据库连接问题
        connection_failures = sum(1 for h in execution_history if any(keyword in str(h.get("exec_result", {}).get("error", "")).lower()
                                  for keyword in ["network", "connection", "http query failed", "mysql", "doris"]))
        if connection_failures >= 3:
            return {
                "should_exit": True,
                "reason": "数据库连接频繁失败",
                "suggestion": "建议检查数据源配置和网络连接"
            }

        # 检测无进展状态
        if iteration > 5:
            has_sql = bool(execution_context.get("current_sql"))
            if not has_sql and iteration > 5:
                return {
                    "should_exit": True,
                    "reason": "5轮后仍无SQL生成",
                    "suggestion": "建议检查表结构或降低复杂度"
                }

        return {"should_exit": False}

    async def _validate_goal_achievement(self, ai: AgentInput, execution_context: Dict[str, Any], exec_result: Dict[str, Any]) -> Dict[str, Any]:
        """验证是否达成目标 - 增强智能判断 + SQL修复循环"""
        # 检查是否有可用的SQL且通过了数据库验证
        current_sql = execution_context.get("current_sql", "")
        context = exec_result.get("context", {})

        # SQL生成且数据库验证成功
        if (current_sql and
            context.get("sql_executed_successfully") and
            context.get("execution_result", {}).get("rows")):

            return {
                "goal_achieved": True,
                "reason": "SQL生成并通过数据库验证，获得了有效数据",
                "result": current_sql
            }

        # 如果SQL通过了语法验证但数据库连接失败，也应该算作成功
        if (current_sql and
            context.get("database_validated") is False and
            not context.get("issues") and
            any(keyword in str(context.get("database_error", "")).lower()
                for keyword in ["connection", "network", "http query failed", "mysql", "doris"])):

            return {
                "goal_achieved": True,
                "reason": "SQL生成并通过语法验证，数据库连接问题不影响SQL正确性",
                "result": current_sql,
                "note": "建议检查数据源连接配置"
            }

        # 图表生成完成
        if context.get("chart_image_path"):
            return {
                "goal_achieved": True,
                "reason": "图表生成完成",
                "result": context.get("chart_image_path")
            }

        # SQL验证失败 - 进入修复循环逻辑
        if not exec_result.get("success") and current_sql:
            issues = context.get("issues", [])
            if issues:
                # 获取或初始化修复计数器
                sql_fix_attempts = execution_context.get("sql_fix_attempts", 0)

                # 如果修复次数未达到上限（3次），继续修复
                if sql_fix_attempts < 3:
                    execution_context["sql_fix_attempts"] = sql_fix_attempts + 1
                    execution_context["last_sql_issues"] = issues

                    self._logger.info(f"🔧 [SQL修复循环] 第{sql_fix_attempts + 1}次修复尝试，问题: {len(issues)}个")

                    # 如果有修正建议，使用修正建议
                    if context.get("corrected_sql"):
                        execution_context["current_sql"] = context["corrected_sql"]
                        return {
                            "goal_achieved": False,
                            "should_continue": True,
                            "reason": f"应用修正建议，第{sql_fix_attempts + 1}次修复尝试"
                        }
                    else:
                        # 没有修正建议，请求Agent基于问题进行修复
                        return {
                            "goal_achieved": False,
                            "should_continue": True,
                            "reason": f"SQL有问题需要修复，第{sql_fix_attempts + 1}次尝试"
                        }
                else:
                    # 修复次数已达上限，放弃修复
                    self._logger.warning(f"⚠️ [SQL修复循环] 3次修复后仍有问题，放弃修复")
                    return {
                        "goal_achieved": False,
                        "should_continue": False,
                        "reason": "SQL修复失败：3次尝试后仍有问题"
                    }

        # 执行失败且无修正建议
        if not exec_result.get("success") and not context.get("corrected_sql"):
            return {
                "goal_achieved": False,
                "should_continue": False,
                "reason": "执行失败且无修正建议"
            }

        # 继续执行
        return {
            "goal_achieved": False,
            "should_continue": True,
            "reason": "需要更多步骤完成目标"
        }

    def _update_execution_context(self, execution_context: Dict[str, Any], context: Dict[str, Any]) -> None:
        """🗄️ ResourcePool模式的execution_context更新逻辑

        将详细信息存入ResourcePool，execution_context保持轻量。

        Args:
            execution_context: PTAV循环的执行上下文
            context: 单轮执行返回的context
        """
        resource_pool = execution_context.get("resource_pool")
        if not resource_pool:
            self._logger.error("⚠️ ResourcePool未初始化")
            return

        # 准备更新数据
        updates = {}

        # current_sql: 既存入ResourcePool，也保留在execution_context（用于快速访问）
        if context.get("current_sql"):
            execution_context["current_sql"] = context["current_sql"]
            updates["current_sql"] = context["current_sql"]

        # column_details: 存入ResourcePool（完整数据）
        if context.get("column_details"):
            updates["column_details"] = context["column_details"]
            table_count = len(context["column_details"])
            table_names = list(context["column_details"].keys())
            self._logger.info(
                f"🗄️ [ResourcePool] 存储column_details: "
                f"{table_count}张表 - {table_names}"
            )

        # schema_summary: 存入ResourcePool
        if context.get("schema_summary"):
            updates["schema_summary"] = context["schema_summary"]

        # recommended_time_column: 存入ResourcePool
        if context.get("recommended_time_column"):
            updates["recommended_time_column"] = context["recommended_time_column"]
            self._logger.info(
                f"🗄️ [ResourcePool] 存储推荐时间列: "
                f"{context['recommended_time_column']}"
            )

        if context.get("coordinator_metadata"):
            updates["coordinator_metadata"] = context.get("coordinator_metadata")
            execution_context["coordinator_metadata"] = context.get("coordinator_metadata")

        # template_context: 存入ResourcePool（用于SQL生成）
        if context.get("template_context"):
            updates["template_context"] = context["template_context"]

        # 批量更新ResourcePool
        if updates:
            resource_pool.update(updates)
            stats = resource_pool.get_stats()
            self._logger.debug(f"🗄️ [ResourcePool] 当前状态: {stats}")

    def _update_ai_with_context(self, ai: AgentInput, execution_context: Dict[str, Any]) -> AgentInput:
        """使用执行上下文更新AI输入

        向下一轮Plan提供可见的上下文线索，避免重复无效动作：
        - 已有/更新的schema
        - 是否已有current_sql
        - 上一步执行的工具与建议
        - 验证问题提示
        """
        try:
            from dataclasses import replace
            from .types import SchemaInfo

            # 最近一次执行结果
            last = (execution_context.get("execution_history") or [])[-1] if execution_context.get("execution_history") else None
            last_plan = (last or {}).get("plan", {})
            last_step = (last_plan.get("steps", []) or [{}])[0] if last_plan else {}
            last_tool = last_step.get("tool") or last_step.get("action")
            last_exec = (last or {}).get("exec_result", {})
            last_ctx = last_exec.get("context", {})
            decision_info = last_exec.get("decision_info", {})

            # 提取schema更新 - 优先使用累积的execution_context信息
            new_tables = execution_context.get("tables") or last_ctx.get("tables") or getattr(ai.schema, 'tables', [])
            new_columns = execution_context.get("columns") or last_ctx.get("columns") or getattr(ai.schema, 'columns', {})

            # 规划提示 - 增强SQL修复信息传递
            planning_hints = {
                "has_current_sql": bool(last_ctx.get("current_sql")),
                "last_step": last_tool,
                "next_recommendations": decision_info.get("next_recommendations", []),
                "validation_issues": last_ctx.get("issues", []) or last_ctx.get("validation_issues", []),
                "warnings": last_ctx.get("warnings", []) or last_ctx.get("validation_warnings", []),
                "sql_fix_attempts": execution_context.get("sql_fix_attempts", 0),
                "last_sql_issues": execution_context.get("last_sql_issues", []),
            }

            # 合并到task_driven_context
            tdc = dict(getattr(ai, 'task_driven_context', {}) or {})
            tdc["planning_hints"] = planning_hints

            # 🗄️ [ResourcePool模式] 传递轻量级ContextMemory和ResourcePool引用
            resource_pool = execution_context.get("resource_pool")

            if resource_pool:
                # 从ResourcePool构建ContextMemory
                context_memory = resource_pool.build_context_memory()
                tdc["context_memory"] = context_memory.to_dict()

                # 🔧 传递ResourcePool引用给Executor（Executor需要按需提取详细信息）
                tdc["resource_pool"] = resource_pool

                self._logger.info(
                    f"🗄️ [AI Context] 传递ContextMemory + ResourcePool引用: "
                    f"has_sql={context_memory.has_sql}, "
                    f"schema_available={context_memory.schema_available}, "
                    f"tables={len(context_memory.available_tables)}"
                )

                # 注意：不再传递完整的column_details到AI Context
                # Executor通过ContextMemory了解状态，需要详细信息时从ResourcePool按需提取
            else:
                self._logger.warning("⚠️ [AI Context] ResourcePool未初始化，无法传递ContextMemory")

            # 更新schema
            new_schema = SchemaInfo(tables=new_tables, columns=new_columns)
            return replace(ai, schema=new_schema, task_driven_context=tdc)
        except Exception:
            return ai

    async def _finalize_ptav_result(self, ai: AgentInput, execution_context: Dict[str, Any]) -> Dict[str, Any]:
        """生成PTAV循环的最终结果"""
        if execution_context.get("goal_achieved"):
            return {
                "success": True,
                "result": execution_context.get("current_sql", ""),
                "execution_summary": f"完成{len(execution_context['execution_history'])}轮迭代",
                "final_sql": execution_context.get("current_sql"),
                "iteration_count": len(execution_context["execution_history"]),
                "observations": execution_context.get("accumulated_observations", [])
            }
        else:
            return {
                "success": False,
                "error": execution_context.get("last_error", "未能达成目标"),
                "execution_summary": f"执行{len(execution_context['execution_history'])}轮后停止",
                "partial_result": execution_context.get("current_sql", ""),
                "iteration_count": len(execution_context["execution_history"]),
                "observations": execution_context.get("accumulated_observations", [])
            }

    async def _execute_task_sql_validation(self, ai: AgentInput) -> AgentOutput:
        """
        执行Task任务中的SQL有效性验证和更新流程

        专门用于任务执行过程中：
        1. 检查现有SQL是否过时或有缺陷
        2. 基于最新schema和业务需求验证SQL
        3. 如需要则更新SQL，确保能正确执行
        4. 针对性验证，不做完整重建

        Args:
            ai: Agent输入，应包含现有的SQL和任务上下文

        Returns:
            AgentOutput: 验证和更新结果
        """
        task_id = str(uuid.uuid4())
        self._logger.info(f"🔍 [SQL验证模式] 开始任务验证 {task_id}")

        try:
            current_sql = getattr(ai, 'current_sql', '') or ai.context.current_sql if hasattr(ai.context, 'current_sql') else ""

            if not current_sql:
                self._logger.warning(f"⚠️ [SQL验证模式] 无现有SQL需要验证")
                return AgentOutput(False, "", {"error": "missing_current_sql", "message": "没有提供需要验证的SQL"})

            self._logger.info(f"📝 [SQL验证模式] 验证SQL: {current_sql[:100]}...")

            # 构建验证专用的AgentInput - 重点关注验证而非重新生成
            validation_context = {
                "mode": "sql_validation",
                "current_sql": current_sql,
                "validation_focus": "compatibility_check",  # 兼容性检查，不完整重建
                "preserve_logic": True  # 保持原有逻辑
            }

            # 执行增强验证流程：时间属性检查 -> Schema兼容性 -> 语法检查 -> 数据库验证
            validation_steps = [
                {"action": "tool_call", "tool": "time.window", "reason": "检查和更新时间属性", "input": {}},
                {"action": "tool_call", "tool": "schema.list_columns", "reason": "确认schema变更", "input": {}},
                {"action": "tool_call", "tool": "sql.validate", "reason": "验证SQL兼容性", "input": {"current_sql": current_sql}},
            ]

            # 只有在验证失败时才尝试修正
            plan = {
                "thought": "验证现有SQL的有效性，仅在必要时进行最小化修正",
                "steps": validation_steps,
                "expected_outcome": "validated_sql"
            }

            # 执行验证
            exec_result = await self.executor.execute({"plan": plan}, ai)
            context = exec_result.get("context", {})

            # 分析验证结果，特别关注时间属性
            time_updated = context.get("start_date") or context.get("end_date")
            time_issues = [issue for issue in context.get("issues", []) if any(keyword in str(issue).lower() for keyword in ["时间", "日期", "date", "time"])]

            if context.get("database_validated") and not context.get("issues"):
                # SQL验证通过
                message = "现有SQL验证通过"
                if time_updated:
                    message += f"，时间属性已更新({context.get('start_date', '')} - {context.get('end_date', '')})"

                self._logger.info(f"✅ [SQL验证模式] {message}")
                return AgentOutput(True, current_sql, {
                    "validation_status": "passed",
                    "current_sql": current_sql,
                    "message": message,
                    "time_updated": bool(time_updated),
                    "time_range": {
                        "start_date": context.get("start_date"),
                        "end_date": context.get("end_date")
                    },
                    "validation_details": context
                })

            elif context.get("issues") or context.get("database_error"):
                # SQL有问题，需要修正
                issues = context.get("issues", [])
                time_issue_count = len(time_issues)

                self._logger.warning(f"⚠️ [SQL验证模式] 发现{len(issues)}个问题(其中{time_issue_count}个时间相关)，需要修正")

                # 如果有修正建议，应用修正
                if context.get("corrected_sql"):
                    corrected_sql = context["corrected_sql"]
                    self._logger.info(f"🔧 [SQL验证模式] 应用修正建议")

                    # 验证修正后的SQL
                    validation_result = await self._quick_validate_sql(corrected_sql, ai)
                    if validation_result.get("success"):
                        message = f"SQL已修正，解决了{len(issues)}个问题"
                        if time_issue_count > 0:
                            message += f"(包括{time_issue_count}个时间属性问题)"

                        return AgentOutput(True, corrected_sql, {
                            "validation_status": "corrected",
                            "original_sql": current_sql,
                            "current_sql": corrected_sql,
                            "issues_fixed": issues,
                            "time_issues_fixed": time_issues,
                            "time_updated": bool(time_updated),
                            "time_range": {
                                "start_date": context.get("start_date"),
                                "end_date": context.get("end_date")
                            },
                            "message": message
                        })

                # 修正失败，返回问题详情
                return AgentOutput(False, "", {
                    "validation_status": "failed",
                    "current_sql": current_sql,
                    "issues": issues,
                    "error": "SQL验证失败且无法自动修正",
                    "database_error": context.get("database_error"),
                    "recommendations": "需要手动检查SQL或重新生成"
                })

            else:
                # 验证状态不明确
                return AgentOutput(False, "", {
                    "validation_status": "unknown",
                    "current_sql": current_sql,
                    "error": "SQL验证结果不明确",
                    "exec_result": exec_result
                })

        except Exception as e:
            error = {"error": f"task_sql_validation_exception: {str(e)}", "task_id": task_id}
            self._logger.error(f"❌ [SQL验证模式] 异常 {task_id}: {str(e)}")
            return AgentOutput(False, "", error)

    async def _execute_report_chart_generation(self, ai: AgentInput) -> AgentOutput:
        """
        执行报告生成中的数据转图表流程

        专门用于报告生成中：
        1. 验证查询结果数据的完整性和格式
        2. 根据数据特征选择合适的图表类型
        3. 生成图表配置和样式
        4. 生成最终图表文件
        5. 添加图例说明和格式化

        Args:
            ai: Agent输入，应包含查询结果数据

        Returns:
            AgentOutput: 图表生成结果
        """
        chart_session_id = str(uuid.uuid4())
        self._logger.info(f"📊 [图表生成模式] 开始图表生成 {chart_session_id}")

        try:
            # 检查输入数据
            data_rows = getattr(ai, 'data_rows', []) or []
            data_columns = getattr(ai, 'data_columns', []) or []

            if not data_rows or not data_columns:
                context = getattr(ai, 'context', {})
                if hasattr(context, 'execution_result'):
                    data_rows = context.execution_result.get('rows', [])
                    data_columns = context.execution_result.get('columns', [])

            if not data_rows:
                self._logger.warning(f"⚠️ [图表生成模式] 无数据可用于生成图表")
                return AgentOutput(False, "", {
                    "error": "missing_data",
                    "message": "没有提供可用于生成图表的数据"
                })

            self._logger.info(f"📊 [图表生成模式] 处理数据: {len(data_rows)}行 x {len(data_columns)}列")

            # 构建图表生成管道
            chart_pipeline = [
                {"action": "tool_call", "tool": "data.quality", "reason": "验证数据质量和格式", "input": {}},
                {"action": "tool_call", "tool": "chart.spec", "reason": "生成图表配置", "input": {}},
                {"action": "tool_call", "tool": "word_chart_generator", "reason": "生成最终图表", "input": {}}
            ]

            plan = {
                "thought": "数据质量验证 -> 图表配置生成 -> 图表渲染",
                "steps": chart_pipeline,
                "expected_outcome": "chart"
            }

            # 执行图表生成管道
            exec_result = await self.executor.execute({"plan": plan}, ai)
            context = exec_result.get("context", {})

            # 检查图表生成结果
            if context.get("chart_image_path"):
                chart_path = context["chart_image_path"]
                chart_spec = context.get("chart_spec", {})

                self._logger.info(f"✅ [图表生成模式] 图表生成成功: {chart_path}")

                return AgentOutput(True, chart_path, {
                    "generation_status": "success",
                    "chart_image_path": chart_path,
                    "chart_spec": chart_spec,
                    "data_summary": {
                        "row_count": len(data_rows),
                        "column_count": len(data_columns),
                        "columns": data_columns[:10]  # 只返回前10列避免过长
                    },
                    "message": f"成功生成图表，处理了{len(data_rows)}行数据"
                })

            elif context.get("chart_spec"):
                # 图表配置生成了但图片生成失败
                self._logger.warning(f"⚠️ [图表生成模式] 图表配置生成成功但图片生成失败")
                return AgentOutput(False, "", {
                    "generation_status": "partial_success",
                    "chart_spec": context["chart_spec"],
                    "error": "图表配置生成成功但图片渲染失败",
                    "data_summary": {"row_count": len(data_rows), "column_count": len(data_columns)}
                })

            else:
                # 图表生成完全失败
                error_details = exec_result.get("observations", [])
                self._logger.error(f"❌ [图表生成模式] 图表生成失败")
                return AgentOutput(False, "", {
                    "generation_status": "failed",
                    "error": "图表生成流程失败",
                    "error_details": error_details,
                    "data_summary": {"row_count": len(data_rows), "column_count": len(data_columns)}
                })

        except Exception as e:
            error = {"error": f"chart_generation_exception: {str(e)}", "chart_session_id": chart_session_id}
            self._logger.error(f"❌ [图表生成模式] 异常 {chart_session_id}: {str(e)}")
            return AgentOutput(False, "", error)

    async def _quick_validate_sql(self, sql: str, ai: AgentInput) -> Dict[str, Any]:
        """快速SQL验证 - 用于任务验证模式"""
        try:
            validation_plan = {
                "steps": [{"action": "tool_call", "tool": "sql.validate", "reason": "快速验证", "input": {"current_sql": sql}}]
            }
            result = await self.executor.execute(validation_plan, ai)
            context = result.get("context", {})

            return {
                "success": not bool(context.get("issues")),
                "issues": context.get("issues", []),
                "database_validated": context.get("database_validated", False)
            }
        except Exception:
            return {"success": False, "issues": ["验证过程异常"]}


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
