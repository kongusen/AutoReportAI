"""
上下文和提示词控制器

统一管理上下文构建和提示词生成
为不同阶段提供优化的提示词模板
"""

import logging
from typing import Any, Dict, List
from enum import Enum

from .types import AgentInput


class ContextPromptController:
    """上下文和提示词控制器"""

    def __init__(self) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)

    async def build_plan_prompt(self, ai: AgentInput, stage: Enum, available_tools: List[Dict[str, str]]) -> str:
        """构建计划生成提示词"""

        # 工具列表
        tools_desc = "\n".join([f"- {tool['name']}: {tool['desc']}" for tool in available_tools])

        # 基础上下文
        context_info = []
        if ai.schema.tables:
            context_info.append(f"可用数据表: {', '.join(ai.schema.tables)}")
        if ai.schema.columns:
            for table, columns in ai.schema.columns.items():
                context_info.append(f"{table}表字段: {', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}")

        context_str = "\n".join(context_info) if context_info else "无具体schema信息"

        prompt = f"""
你是一个智能Agent计划生成器，需要为以下任务生成执行计划。

任务信息:
- 用户需求: {ai.user_prompt}
- 占位符描述: {ai.placeholder.description}
- 占位符类型: {ai.placeholder.type}
- 执行阶段: {stage.value}
- 期望输出: {ai.constraints.output_kind}

数据上下文:
{context_str}

可用工具:
{tools_desc}

请生成一个JSON格式的执行计划，包含以下结构:
{{
    "thought": "分析用户需求，确定执行策略",
    "steps": [
        {{
            "action": "tool_call",
            "tool": "工具名称",
            "reason": "执行这个工具的原因",
            "input": {{
                "参数名": "参数值"
            }}
        }}
    ],
    "expected_outcome": "sql|chart|report"
}}

注意事项:
1. 根据执行阶段选择合适的工具序列
2. 每个step必须有明确的reason说明
3. 工具名称必须在可用工具列表中
4. 按逻辑顺序排列步骤
5. 返回纯JSON格式，不要包含其他解释文字
"""
        return prompt.strip()

    def build_finalize_prompt(self, ai: AgentInput, plan: Dict[str, Any], exec_result: Dict[str, Any]) -> str:
        """构建最终决策提示词"""

        # 执行摘要
        observations = exec_result.get("observations", [])
        context = exec_result.get("context", {})

        execution_summary = []
        if observations:
            execution_summary.append("执行观察:")
            for i, obs in enumerate(observations[-5:], 1):  # 只显示最后5个观察
                execution_summary.append(f"  {i}. {obs}")

        # 结果信息
        result_info = []
        if context.get("current_sql"):
            result_info.append(f"生成的SQL: {context['current_sql']}")
        if context.get("execution_result"):
            rows = context["execution_result"].get("rows", [])
            result_info.append(f"数据行数: {len(rows)}")
        if context.get("chart_spec"):
            result_info.append("已生成图表配置")
        if context.get("chart_image_path"):
            result_info.append(f"图表文件: {context['chart_image_path']}")

        execution_info = "\n".join(execution_summary + result_info)

        prompt = f"""
你是一个智能Agent决策器，需要基于执行结果做出最终决策。

原始任务:
- 用户需求: {ai.user_prompt}
- 占位符描述: {ai.placeholder.description}
- 期望输出类型: {ai.constraints.output_kind}

执行情况:
{execution_info}

请分析执行结果并做出最终决策，返回JSON格式:
{{
    "success": true/false,
    "result": "最终结果内容",
    "reasoning": "决策理由",
    "quality_score": 0.8
}}

决策标准:
1. SQL任务: 必须返回有效的SELECT语句
2. 图表任务: 必须有图表配置和图片路径
3. 报告任务: 必须有完整的报告内容
4. 数据质量: 检查数据的完整性和合理性

注意: 返回纯JSON格式，不要包含其他解释文字
"""
        return prompt.strip()

    def build_context(self, ai: AgentInput) -> Dict[str, Any]:
        """构建执行上下文"""
        return {
            "user_prompt": ai.user_prompt,
            "placeholder_description": ai.placeholder.description,
            "placeholder_type": ai.placeholder.type,
            "schema_tables": ai.schema.tables,
            "schema_columns": ai.schema.columns,
            "output_kind": ai.constraints.output_kind,
            "task_time": ai.context.task_time,
            "timezone": ai.context.timezone,
        }