"""
Report Assembly Usecase (Domain)

Performs placeholder replacement during report assembly using three contexts.
Period placeholders compute directly; statistical/chart placeholders use
pre-resolved data and add short narration.
"""

from __future__ import annotations

from typing import Any, Dict
import re

from app.services.domain.placeholder.core.narration_service import NarrationService
from app.services.domain.placeholder.core.handlers.period_handler import PeriodHandler


class ReportReplacer:
    def __init__(self) -> None:
        self._narr = NarrationService()
        self._period = PeriodHandler()

    async def replace(self, template_content: str, contexts: Dict[str, Any], resolved: Dict[str, Dict[str, Any]]) -> str:
        """Replace placeholders using resolved data map.

        resolved: name -> { kind, value/meta | columns/rows/chart }
        contexts contains time context for period summaries.
        """
        def _replacement(match: re.Match) -> str:
            raw = match.group(1)
            key = raw.strip()
            item = resolved.get(key)
            if not item:
                return match.group(0)

            kind = item.get("kind")
            if kind == "period":
                # 直接输出当前周期：日=昨日（YYYY-MM-DD），周=昨日往前7天范围，月=上月完整范围
                meta = item.get("meta") or {}
                start = meta.get('start_date') or ''
                end = meta.get('end_date') or ''
                return start if start == end else f"{start}～{end}"
            if kind == "statistical":
                # show a value + narration
                val = item.get("value")
                narration = self._narr.summarize_stat({"metric": item.get("metric"), "value": val})
                return f"{val}（{narration}）" if val is not None else f"（{narration}）"
            if kind == "chart":
                # embed a reference token; actual renderer will replace it with image
                rows = len(item.get("rows", []))
                narration = self._narr.summarize_chart(item.get("chart_type", "bar"), rows)
                return f"[图表:{item.get('artifact','')}]（{narration}）"
            return match.group(0)

        return re.sub(r"\{\{([^}]+)\}\}", _replacement, template_content)
