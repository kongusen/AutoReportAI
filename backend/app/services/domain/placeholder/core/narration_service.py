"""
Narration Service (Domain)

Generates concise (<=20 chars) descriptions for placeholder outputs to be
embedded into reports during assembly.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class NarrationService:
    def summarize_period(self, time_ctx: Dict[str, Any]) -> str:
        start = time_ctx.get("start_date") or time_ctx.get("data_start_date")
        end = time_ctx.get("end_date") or time_ctx.get("data_end_date")
        if start and end:
            return f"统计区间：{start}~{end}"[:20]
        return "统计区间：动态"[:20]

    def summarize_stat(self, result_meta: Dict[str, Any]) -> str:
        metric = result_meta.get("metric") or result_meta.get("field") or "结果"
        val = result_meta.get("value")
        if val is not None:
            return f"{metric}：{val}"[:20]
        return f"{metric}已更新"[:20]

    def summarize_chart(self, chart_type: str, rows: int) -> str:
        chart_map = {"bar": "柱状图", "line": "折线图", "pie": "饼图"}
        label = chart_map.get(chart_type, "统计图")
        return f"{label}（{rows}行）"[:20]

