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

        # Schema信息 - 优先使用详细字段信息
        if ai.schema.tables:
            context_info.append(f"可用数据表: {', '.join(ai.schema.tables)}")

        # 检查是否有详细字段信息（从task_driven_context获取）
        column_details = None
        if hasattr(ai, 'task_driven_context') and ai.task_driven_context:
            if isinstance(ai.task_driven_context, dict):
                column_details = ai.task_driven_context.get('column_details')

        if column_details and isinstance(column_details, dict):
            # 使用详细字段信息构建丰富的schema描述
            self._logger.info(f"📋 [ContextPromptController] 发现详细字段信息，表数量: {len(column_details)}")
            for table, cols_data in column_details.items():
                if isinstance(cols_data, dict):
                    # cols_data 格式: {"field_name": {"name": "", "type": "", "comment": "", ...}}
                    field_descriptions = []
                    for field_name, field_info in list(cols_data.items())[:5]:  # 限制显示前5个字段
                        if isinstance(field_info, dict):
                            desc = field_name
                            if field_info.get("type"):
                                desc += f"({field_info['type']})"
                            if field_info.get("comment"):
                                desc += f" '{field_info['comment']}'"
                            field_descriptions.append(desc)

                    field_count = len(cols_data)
                    ellipsis = "..." if field_count > 5 else ""
                    fields_text = "; ".join(field_descriptions) + ellipsis
                    context_info.append(f"🔍 {table}表字段({field_count}个): {fields_text}")
                    self._logger.info(f"📋 [ContextPromptController] 使用详细字段信息(dict格式) - {table}: {field_count}个字段")
                elif isinstance(cols_data, list):
                    # 备用格式: list of dicts
                    field_descriptions = []
                    for field_info in cols_data[:5]:
                        if isinstance(field_info, dict) and field_info.get("name"):
                            desc = field_info["name"]
                            if field_info.get("type"):
                                desc += f"({field_info['type']})"
                            if field_info.get("comment"):
                                desc += f" '{field_info['comment']}'"
                            field_descriptions.append(desc)

                    field_count = len(cols_data)
                    ellipsis = "..." if field_count > 5 else ""
                    fields_text = "; ".join(field_descriptions) + ellipsis
                    context_info.append(f"🔍 {table}表字段({field_count}个): {fields_text}")
                    self._logger.info(f"📋 [ContextPromptController] 使用详细字段信息(dict格式) - {table}: {field_count}个字段")
        elif ai.schema.columns:
            # 回退到基础字段信息
            self._logger.info(f"📋 [ContextPromptController] 回退到基础字段信息，表数量: {len(ai.schema.columns)}")
            for table, columns in ai.schema.columns.items():
                context_info.append(f"{table}表字段: {', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}")

        # 时间上下文信息 - 关键用于计算统计范围
        if hasattr(ai, 'context') and ai.context and hasattr(ai.context, 'window'):
            window = ai.context.window
            if isinstance(window, dict):
                cron_expr = window.get('cron_expression', '未知')
                start_date = window.get('start_date', '未知')
                end_date = window.get('end_date', '未知')
                context_info.append(f"⏰ 调度周期: {cron_expr}")
                context_info.append(f"📅 统计时间范围: {start_date} ~ {end_date}")
                if window.get('time_column'):
                    context_info.append(f"🕒 时间列推荐: {window.get('time_column')}")

        # 任务驱动上下文中的时间信息
        if hasattr(ai, 'task_driven_context') and ai.task_driven_context:
            if isinstance(ai.task_driven_context, dict):
                # 上一轮规划提示（来自执行上下文）
                hints = ai.task_driven_context.get('planning_hints', {})
                if hints:
                    if hints.get('has_current_sql'):
                        context_info.append("✅ 已有SQL代码（待验证/执行）")

                # 显示当前SQL代码（如果存在）
                current_sql = ai.task_driven_context.get('current_sql')
                self._logger.info(f"📋 [ContextPromptController] task_driven_context中的current_sql: {current_sql}")
                if current_sql and isinstance(current_sql, str) and current_sql.strip():
                    context_info.append(f"🔍 当前SQL代码: {current_sql}")
                    context_info.append(f"📋 SQL代码长度: {len(current_sql)} 字符")
                    self._logger.info(f"📋 [ContextPromptController] 已将SQL添加到context_info: {len(current_sql)}字符")

                if hints:
                    if hints.get('last_step'):
                        context_info.append(f"🔁 上一步: {hints.get('last_step')}")
                    recs = hints.get('next_recommendations') or []
                    if recs:
                        context_info.append(f"👉 建议: {', '.join(recs[:3])}{'...' if len(recs) > 3 else ''}")
                    v_issues = hints.get('validation_issues') or []
                    if v_issues:
                        context_info.append(f"⚠️ 验证问题: {', '.join(v_issues[:3])}{'...' if len(v_issues) > 3 else ''}")

                # 调度表达式
                cron_expr = ai.task_driven_context.get('cron_expression')
                if cron_expr:
                    context_info.append(f"🔄 任务调度: {cron_expr}")

                # 时间范围信息
                time_range = ai.task_driven_context.get('time_range', {})
                if time_range:
                    start_date = time_range.get('start_date')
                    end_date = time_range.get('end_date')
                    time_column = time_range.get('time_column')
                    if start_date and end_date:
                        context_info.append(f"📊 统计时间范围: {start_date} ~ {end_date}")
                        if time_column:
                            context_info.append(f"🕒 推荐时间列: {time_column}")

                # 调度信息详情
                scheduling_info = ai.task_driven_context.get('scheduling_info', {})
                if scheduling_info:
                    schedule_type = scheduling_info.get('schedule_type', 'daily')
                    period_desc = scheduling_info.get('previous_period_desc', '')
                    context_info.append(f"⏳ 调度类型: {schedule_type}")
                    if period_desc:
                        context_info.append(f"📈 统计周期: {period_desc}")

        context_str = "\n".join(context_info) if context_info else "无具体上下文信息"

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

请分析当前状态并决定下一步行动，返回JSON格式:
{{
    "thought": "基于当前信息分析，我需要什么？",
    "current_state": "描述当前掌握的信息状况",
    "next_action": {{
        "action": "tool_call|sql_generation|complete",
        "tool": "工具名称（仅当action=tool_call时需要，从上面的'可用工具'列表中选择）",
        "reason": "为什么选择这个行动",
        "input": {{
            "参数名": "参数值"
        }}
    }},
    "goal_progress": "离最终SQL生成目标还差什么"
}}

**动作类型说明**：
- **tool_call**: 调用上面列出的工具（必须在tool字段指定工具名称，如schema.get_columns、sql.validate等）
- **sql_generation**: 基于已有信息直接生成SQL（这是一个动作类型，不是工具名称，无需指定tool字段）
- **complete**: 任务已完成

**重要：工具输入示例**
- sql.validate调用示例：
  ```json
  "input": {{"current_sql": "SELECT COUNT(*) FROM table_name WHERE date_col = '2025-09-26'"}}
  ```
  ⚠️ 绝对不要使用描述性文本如"当前候选SQL"、"已生成的SQL"等，必须是实际的SQL代码

- schema.get_columns调用示例：
  ```json
  "input": {{"tables": ["table1", "table2"]}}
  ```
  🎯 **表选择决策原则（PTAV - Plan阶段必须明确指定）**：
  1. 分析占位符描述中的关键词（如"退货"→查找包含refund/return的表）
  2. 基于"可用数据表"列表，优先选择表名与需求最匹配的2-3张表
  3. 如果已有column_details（见上方🔍标记），优先选择包含时间字段的表
  4. 避免选择过多表（建议2-5张），可分批获取
  ⚠️ **PTAV关键原则**：表选择是Plan阶段的决策责任，必须在input中明确指定tables参数！

**单步骤决策原则**:
1. **分析当前掌握的信息是否足够生成SQL**
2. **缺什么信息就调用对应工具获取（如需表结构：先schema.list_tables再schema.get_columns）**
3. **信息足够就生成SQL**
4. **⚠️ 生成SQL时必须包含时间范围过滤条件，基于调度周期推测前一个统计周期**
5. **SQL生成后必须通过实际执行验证**
6. **验证失败就基于错误重新生成**
7. **只规划下一步，不做多步骤计划**

若已存在SQL代码（见上方SQL信息），优先选择：
- 调用 sql.validate 进行验证；若有问题则修正或重新生成
- ⚠️ 重要：sql.validate的input必须传递实际的SQL代码，不要传递描述性文本
- 通过 sql.policy 应用安全策略与LIMIT
- 使用 sql.execute 进行小样本执行验证

**强约束的前置条件（请严格遵守）**:
- 如果 `current_sql` 已存在：下一步优先选择 `sql.validate`（如有问题再修正或重生）。
  ⚠️ 关键：在input中必须传递context中的实际SQL代码，而不是描述性文本。
  从上方"🔍 当前SQL代码:"信息中复制完整的SQL语句作为current_sql参数值。
  绝对不要使用"当前候选SQL"、"已有SQL"、"候选SQL内容"等描述性文本！
- 如果缺少时间范围（start_date/end_date）：请先调用 `time.window` 计算时间窗，再进行其他步骤。
- 如果缺少表结构（无 `schema_summary` 且 `columns` 未获取）：请先 `schema.list_tables`，然后 `schema.get_columns`（可显式指定 tables 或让系统自动筛选）。
- 在未满足以上前置信号时，请不要直接进行 `sql_generation`。

**时间范围推测规则**:
- **每日任务** (如 0 9 * * *): 统计昨天的数据
  `WHERE DATE(时间列) = CURDATE() - INTERVAL 1 DAY`
- **每周任务** (如 0 9 * * 1): 统计上周的数据
  `WHERE 时间列 >= 上周一 AND 时间列 < 本周一`
- **每月任务** (如 0 9 1 * *): 统计上月的数据
  `WHERE 时间列 >= 上月1日 AND 时间列 < 本月1日`
- **每年任务** (如 0 0 1 1 *): 统计去年的数据
  `WHERE YEAR(时间列) = YEAR(CURDATE()) - 1`
- **如果有具体的统计时间范围，直接使用提供的start_date和end_date**
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

        # 结果信息 - 增强React能力
        result_info = []

        # SQL生成信息
        if context.get("sql_generation_prompt"):
            result_info.append(f"SQL生成提示已准备: {context['sql_generation_prompt'][:200]}...")
        if context.get("current_sql"):
            result_info.append(f"🔍 当前SQL代码: {context['current_sql']}")
            result_info.append(f"📋 SQL代码长度: {len(context['current_sql'])} 字符")

        # 验证信息 - 关键的React触发点
        validation_issues = []
        if context.get("issues"):
            validation_issues = context["issues"]
            result_info.append(f"SQL验证问题: {'; '.join(validation_issues)}")
        if context.get("warnings"):
            warnings = context["warnings"]
            result_info.append(f"SQL警告: {'; '.join(warnings)}")
        if context.get("corrected_sql"):
            result_info.append(f"修正建议SQL: {context['corrected_sql']}")

        # 执行信息
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

请分析执行结果并做出最终决策。如果SQL验证失败，请基于错误信息重新生成正确的SQL。

返回JSON格式:
{{
    "success": true/false,
    "result": "最终SQL语句",
    "test_result": {{
        "executed": true/false,
        "rows": [...],
        "columns": [...],
        "row_count": 数字,
        "message": "执行结果描述"
    }},
    "reasoning": "决策理由",
    "quality_score": 0.8,
    "action": "continue/regenerate_sql"
}}

**React决策逻辑**:
1. 如果SQL验证失败：设置 "action": "regenerate_sql"，在result中提供修正后的SQL
2. 如果执行失败但有修正建议：使用修正建议的SQL作为result
3. 如果需要重新生成：基于schema信息、时间上下文、验证错误信息生成新SQL
4. 如果所有步骤成功：设置 "action": "continue"，返回最终结果

**填充test_result的规则**:
- 如果SQL已成功执行：从execution_result提取rows、columns、row_count，设置executed=true
- 如果SQL验证失败但重新生成：设置executed=false，message="SQL已重新生成，等待执行"
- 如果SQL执行失败：设置executed=false，填入错误信息

**决策标准**:
- result中必须包含完整的SQL语句
- test_result必须包含执行状态和结果数据
- SQL必须使用真实存在的表名和列名（严格匹配schema）
- ⚠️ **重要：所有SQL必须包含时间范围过滤，基于cron表达式计算前一个周期**

**时间范围计算规则**:
- 每日任务(0 9 * * *)：统计昨天数据 `WHERE DATE(time_column) = CURDATE() - INTERVAL 1 DAY`
- 每周任务(0 9 * * 1)：统计上周数据 `WHERE time_column >= DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) + 7 DAY) AND time_column < DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)`
- 每月任务(0 9 1 * *)：统计上月数据 `WHERE time_column >= DATE_SUB(DATE_SUB(CURDATE(), INTERVAL DAY(CURDATE()) - 1 DAY), INTERVAL 1 MONTH) AND time_column < DATE_SUB(CURDATE(), INTERVAL DAY(CURDATE()) - 1 DAY)`
- 每年任务(0 0 1 1 *)：统计去年数据 `WHERE YEAR(time_column) = YEAR(CURDATE()) - 1`

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
