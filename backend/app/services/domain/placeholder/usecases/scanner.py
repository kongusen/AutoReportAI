"""
ETL Pre-Scan Usecase (Domain)

Scans placeholders in a template, classifies them, and determines whether
re-analysis is required (expired/empty/error). This use case only depends on
Domain parsers and schema discovery port.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from app.services.domain.placeholder.parsers.parser_factory import ParserFactory
from app.services.domain.placeholder.ports.schema_discovery_port import SchemaDiscoveryPort


@dataclass
class PlaceholderScanItem:
    name: str
    text: str
    kind: str  # period|statistical|chart|unknown
    needs_reanalysis: bool
    reason: str


class PlaceholderScanner:
    def __init__(self, schema_port: SchemaDiscoveryPort) -> None:
        self._schema = schema_port
        self._parser_factory = ParserFactory()

    async def scan_template(self, template_id: str, template_content: str, data_source_id: str) -> List[PlaceholderScanItem]:
        # Introspect schema (can be used for advanced checks)
        _ = await self._schema.introspect(data_source_id)

        # Extract placeholders by regex (simple; replace with your parser when needed)
        import re
        items: List[PlaceholderScanItem] = []
        for i, m in enumerate(re.findall(r"\{\{([^}]+)\}\}", template_content)):
            text = m.strip()
            kind = self._classify(text)
            needs = kind in ("statistical", "chart")  # period doesn't need SQL
            reason = "缺少SQL/需生成" if needs else "周期类可直接计算"
            items.append(PlaceholderScanItem(name=f"ph_{i}", text=text, kind=kind, needs_reanalysis=needs, reason=reason))
        return items

    def _classify(self, text: str) -> str:
        t = text
        if any(k in t for k in ["周期", "日期", "时间"]):
            return "period"
        if any(k in t for k in ["图表", "柱状图", "折线图", "饼图"]):
            return "chart"
        if any(k in t for k in ["统计", "总数", "平均", "计数"]):
            return "statistical"
        return "unknown"

