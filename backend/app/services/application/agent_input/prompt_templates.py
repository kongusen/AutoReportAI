"""
Prompt templates (type-aware) for dynamic user_prompt composition.

按占位符类型定制动态提示词：
- stat: 统计/聚合型，占位符常见“统计类”
- chart: 图表型，占位符常见“图表类”
- period: 周期/时间序列型，占位符常见“周期类”

可扩展：通过注册更多策略或细分类型（如 ranking/compare 等）。
"""
from __future__ import annotations

from typing import Any, Dict, List


class PromptComposer:
    """Compose dynamic user_prompt based on placeholder type and output kind."""

    def __init__(self) -> None:
        pass

    def compose(
        self,
        consolidated: Dict[str, Any],
        placeholder_name: str,
        output_kind: str,
        ph_meta: Dict[str, Any]
    ) -> str:
        # 基础信息
        template_info = consolidated.get("template_info", {})
        time_ctx = consolidated.get("time_context", {})
        rules = consolidated.get("business_rules", [])
        db_ctx = consolidated.get("database_context") or {}

        # schema 简述与列建议
        tables = db_ctx.get("tables") or []
        table_names = [t.get("table_name") for t in tables if t.get("table_name")]
        tables_str = ", ".join(table_names[:5]) + ("..." if len(table_names) > 5 else "") if table_names else "无"

        measure_suggestions, dimension_suggestions, time_columns = self._collect_schema_hints(tables)

        # 任务目标文案
        goal = self._compose_goal(placeholder_name, output_kind)

        # 类型特定指引
        ph_type = (ph_meta.get("type") or "stat").lower()
        guidance_lines = []
        if ph_type == "chart":
            guidance_lines.extend(self._chart_guidance())
        elif ph_type == "ranking":
            guidance_lines.extend(self._ranking_guidance())
        elif ph_type == "compare":
            guidance_lines.extend(self._compare_guidance())
        else:
            # 默认走统计类指引
            guidance_lines.extend(self._stat_guidance())

        # 周期/时间序列补充
        if (ph_meta.get("type_cn") or "").find("期") >= 0 or self._is_time_series_placeholder(ph_meta, time_columns):
            guidance_lines.extend(self._period_guidance())

        # 时间与业务规则
        time_hint = time_ctx.get("agent_instructions") or ""
        rules_hint = ("\n- ".join(rules)) if rules else ""

        # 组装
        lines: List[str] = [
            f"任务: {goal}",
            f"模板: {template_info.get('name') or template_info.get('id') or ''}",
            f"语境: {ph_meta.get('type_cn') or ph_meta.get('type') or ''}",
            f"可用表: {tables_str}",
        ]

        if dimension_suggestions:
            lines.append(f"维度建议: {', '.join(dimension_suggestions[:6])}")
        if measure_suggestions:
            lines.append(f"度量建议: {', '.join(measure_suggestions[:6])}")
        if time_columns:
            lines.append(f"时间字段: {', '.join(time_columns[:6])}")

        # 参数提示（如Top N）
        top_n = (ph_meta or {}).get("top_n")

        if top_n:
            lines.append(f"目标Top N: {top_n}")

        if guidance_lines:
            lines.append("执行指引:")
            lines.extend([f"- {g}" for g in guidance_lines])

        if time_hint:
            lines.append(f"时间指令: {time_hint.strip()}")
        if rules_hint:
            lines.append(f"业务规则:\n- {rules_hint}")

        return "\n".join([l for l in lines if l])

    # === helpers ===
    def _collect_schema_hints(self, tables: List[Dict[str, Any]]):
        measures: List[str] = []
        dimensions: List[str] = []
        time_cols: List[str] = []
        for t in tables:
            measures.extend(t.get("measure_columns") or [])
            dimensions.extend(t.get("dimension_columns") or [])
            time_cols.extend(t.get("time_columns") or [])
        # 去重保持顺序
        measures = list(dict.fromkeys(measures))
        dimensions = list(dict.fromkeys(dimensions))
        time_cols = list(dict.fromkeys(time_cols))
        return measures, dimensions, time_cols

    def _compose_goal(self, placeholder_name: str, output_kind: str) -> str:
        if output_kind == "chart":
            return f"为占位符《{placeholder_name}》生成图表所需的数据SQL与图表配置"
        if output_kind == "report":
            return f"为占位符《{placeholder_name}》生成报告段落所需的数据与文本"
        return f"为占位符《{placeholder_name}》生成SQL"

    def _is_time_series_placeholder(self, ph_meta: Dict[str, Any], time_columns: List[str]) -> bool:
        # 基于中文类型或存在时间字段简单判断
        tcn = (ph_meta.get("type_cn") or "")
        if any(k in tcn for k in ["周期", "月", "周", "季度", "年", "趋势"]):
            return True
        return bool(time_columns)

    def _stat_guidance(self) -> List[str]:
        return [
            "生成可执行的 SELECT 语句，包含明确的度量与必要的维度",
            "根据时间指令限定时间范围，注意时区处理",
            "对大表添加 WHERE、LIMIT 或策略限定（如仅最近N天）",
            "必要时使用聚合函数（SUM/COUNT/AVG等）与 GROUP BY",
            "字段命名清晰、添加别名，避免保留字",
        ]

    def _chart_guidance(self) -> List[str]:
        return [
            "首先生成用于绘图的数据SQL，包含 x 轴、y 度量、以及系列分组字段（如需要）",
            "确保时间/分类字段可用于分组或排序，度量字段可聚合",
            "数据准备完成后，再输出图表配置要素（类型、x/y 字段、系列、标题）",
        ]

    def _period_guidance(self) -> List[str]:
        return [
            "使用合适的时间粒度（日/周/月/季度）与分组函数",
            "注意首尾边界的包含/排除规则，统一时区",
        ]

    def _ranking_guidance(self) -> List[str]:
        return [
            "选择清晰的分组维度（如商品/地区），使用聚合作为度量",
            "按度量降序排序并取前N（或升序取后N），必要时使用窗口函数 RANK()",
            "结合时间指令限定时间范围，对大表添加 WHERE 与 LIMIT",
            "处理并列名次与NULL值，字段添加别名",
        ]

    def _compare_guidance(self) -> List[str]:
        return [
            "明确两个对比范围（如本期 vs 上期 / 本月 vs 上月），保持指标口径一致",
            "查询同时输出基准值、对比值、差值与百分比变化（(新-旧)/旧）",
            "根据时间指令推导两个周期的边界，注意时区与边界包含规则",
            "若基准为0，避免除0错误并给出合理的变化描述",
        ]
