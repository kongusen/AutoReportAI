"""
步骤执行器

执行计划中的工具步骤序列
维护执行上下文并产生观察记录
支持简单的重试和错误处理
"""

import time
import logging
from typing import Any, Dict, List

from .types import AgentInput
from .tools.registry import ToolRegistry


class StepExecutor:
    """步骤执行器"""

    def __init__(self, container) -> None:
        """
        初始化执行器

        Args:
            container: backup系统的服务容器
        """
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)
        self.registry = ToolRegistry()
        self._setup_tools()

    def _setup_tools(self) -> None:
        """设置和注册工具"""
        # 导入核心工具 (稍后创建)
        from .tools.sql_tools import SQLDraftTool, SQLValidateTool, SQLExecuteTool, SQLRefineTool, SQLPolicyTool
        from .tools.schema_tools import SchemaListColumnsTool
        from .tools.chart_tools import ChartSpecTool, WordChartGeneratorTool
        from .tools.time_tools import TimeWindowTool
        from .tools.data_quality_tools import DataQualityTool

        # 注册基础工具
        self.registry.register(SchemaListColumnsTool(self.container))
        self.registry.register(SQLDraftTool(self.container))
        self.registry.register(SQLValidateTool(self.container))
        self.registry.register(SQLRefineTool(self.container))
        self.registry.register(SQLExecuteTool(self.container))
        self.registry.register(SQLPolicyTool(self.container))
        self.registry.register(ChartSpecTool(self.container))
        self.registry.register(WordChartGeneratorTool(self.container))
        self.registry.register(TimeWindowTool(self.container))
        self.registry.register(DataQualityTool(self.container))

        self._logger.info(f"已注册 {len(self.registry._tools)} 个工具")

    async def execute(self, plan: Dict[str, Any], ai: AgentInput) -> Dict[str, Any]:
        """
        执行计划步骤

        Args:
            plan: 执行计划
            ai: Agent输入上下文

        Returns:
            Dict: 执行结果
        """
        steps = plan.get("steps", [])
        observations = []
        # 从任务上下文中提取可选的语义与参数（如 top_n）
        semantic_info = self._extract_semantic_info(ai)

        # 将约束传入上下文（policy工具可读取）
        constraints_dict = None
        try:
            c = ai.constraints
            constraints_dict = {
                "sql_only": c.sql_only,
                "output_kind": c.output_kind,
                "max_attempts": c.max_attempts,
                "policy_row_limit": c.policy_row_limit,
                "quality_min_rows": c.quality_min_rows,
            }
        except Exception:
            constraints_dict = None

        # 从 task_driven_context 中获取 user_id（用于数据源解析）
        user_id = None
        try:
            if ai.task_driven_context and isinstance(ai.task_driven_context, dict):
                user_id = ai.task_driven_context.get("user_id")
        except Exception:
            user_id = None

        context = {
            "user_prompt": ai.user_prompt,
            "placeholder_description": ai.placeholder.description,
            "tables": ai.schema.tables,
            "columns": ai.schema.columns,
            "window": ai.context.window,
            "data_source": ai.data_source,
            "user_id": user_id,
            "constraints": constraints_dict,
            # 语义与可选参数（供工具使用）
            "semantic_type": semantic_info.get("semantic_type"),
            "top_n": semantic_info.get("top_n"),
        }

        successful_steps = 0
        total_steps = len(steps)

        self._logger.info(f"开始执行计划，共 {total_steps} 个步骤")

        for i, step in enumerate(steps):
            step_start = time.time()
            step_name = f"Step {i+1}"

            try:
                # 获取工具
                tool_name = step.get("tool")
                tool_input = step.get("input", {})
                reason = step.get("reason", f"执行{tool_name}")

                tool = self.registry.get(tool_name)
                if not tool:
                    error_msg = f"工具 {tool_name} 未找到"
                    observations.append(f"{step_name}: {error_msg}")
                    self._logger.error(error_msg)
                    continue

                # 合并上下文到工具输入
                enriched_input = {**tool_input, **context}

                # 执行工具
                self._logger.info(f"执行 {step_name}: {tool_name} - {reason}")
                result = await tool.execute(enriched_input)

                step_duration = int((time.time() - step_start) * 1000)

                # 处理结果
                if result.get("success"):
                    successful_steps += 1
                    observations.append(f"{step_name}: {reason} - 成功 ({step_duration}ms)")

                    # 更新上下文
                    if isinstance(result, dict):
                        for key, value in result.items():
                            if key != "success":
                                context[key] = value

                    # 特殊处理一些关键结果
                    if tool_name == "sql.draft" and result.get("sql"):
                        context["current_sql"] = result["sql"]
                    elif tool_name == "sql.execute" and result.get("rows"):
                        context["execution_result"] = {
                            "rows": result["rows"],
                            "columns": result.get("columns", [])
                        }
                    elif tool_name == "chart.spec" and result.get("chart_spec"):
                        context["chart_spec"] = result["chart_spec"]
                    elif tool_name == "word_chart_generator" and result.get("chart_image_path"):
                        context["chart_image_path"] = result["chart_image_path"]

                else:
                    error_msg = result.get("error", "未知错误")
                    observations.append(f"{step_name}: {reason} - 失败: {error_msg}")
                    self._logger.warning(f"工具执行失败: {tool_name} - {error_msg}")

            except Exception as e:
                step_duration = int((time.time() - step_start) * 1000)
                error_msg = f"执行异常: {str(e)}"
                observations.append(f"{step_name}: {error_msg} ({step_duration}ms)")
                self._logger.error(f"步骤执行异常 {step_name}: {str(e)}")

        # 构建执行结果
        execution_success = successful_steps > 0
        result = {
            "success": execution_success,
            "successful_steps": successful_steps,
            "total_steps": total_steps,
            "observations": observations,
            "context": context,
            "execution_summary": f"{successful_steps}/{total_steps} 步骤成功"
        }

        self._logger.info(f"计划执行完成: {successful_steps}/{total_steps} 步骤成功")
        return result

    async def execute_single_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个工具 (用于调试和测试)

        Args:
            tool_name: 工具名称
            tool_input: 工具输入

        Returns:
            Dict: 工具执行结果
        """
        tool = self.registry.get(tool_name)
        if not tool:
            return {"success": False, "error": f"工具 {tool_name} 未找到"}

        try:
            result = await tool.execute(tool_input)
            return result
        except Exception as e:
            return {"success": False, "error": f"工具执行异常: {str(e)}"}

    def list_available_tools(self) -> List[str]:
        """列出可用工具"""
        return list(self.registry._tools.keys())

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """获取工具信息"""
        tool = self.registry.get(tool_name)
        if not tool:
            return {"exists": False}

        return {
            "exists": True,
            "name": tool.name,
            "description": getattr(tool, 'description', 'No description available'),
            "type": tool.__class__.__name__
        }

    def _extract_semantic_info(self, ai: AgentInput) -> Dict[str, Any]:
        """从AgentInput的task_driven_context中提取占位符语义信息（semantic_type、top_n）。"""
        info: Dict[str, Any] = {}
        try:
            tdc = ai.task_driven_context or {}
            # 优先使用占位符ID、其次描述，尽量匹配模板上下文中的placeholder_name
            ph_candidates = []
            try:
                if ai.placeholder.id:
                    ph_candidates.append(str(ai.placeholder.id))
            except Exception:
                pass
            try:
                if ai.placeholder.description:
                    ph_candidates.append(str(ai.placeholder.description))
            except Exception:
                pass
            # 去重
            ph_candidates = list(dict.fromkeys(ph_candidates))
            contexts = tdc.get("placeholder_contexts") or []
            match = None
            for c in contexts:
                pname = c.get("placeholder_name")
                if not pname:
                    continue
                if any(pname == cand or pname in cand or cand in pname for cand in ph_candidates):
                    match = c
                    break
            if match:
                info["semantic_type"] = match.get("semantic_type")
                params = match.get("parsed_params") or {}
                if isinstance(params, dict):
                    info["top_n"] = params.get("top_n")
        except Exception:
            pass
        return info
