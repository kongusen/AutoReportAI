"""
Chart Rendering Adapter (Infrastructure)

Implements Domain ChartRenderingPort by delegating to your charting toolchain
(e.g., matplotlib, plotly, or existing agents chart tools).
"""

from __future__ import annotations

from typing import Any, List

from app.services.domain.placeholder.ports.chart_rendering_port import (
    ChartRenderingPort, ChartSpec, ChartArtifact,
)


class ChartRenderingAdapter(ChartRenderingPort):
    async def render(self, spec: ChartSpec, data_columns: List[str], data_rows: List[List[Any]]) -> ChartArtifact:
        # Stub implementation returns a non-existent path as placeholder
        chart_type = getattr(spec, 'chart_type', 'bar') if spec else 'bar'
        return ChartArtifact(path="/tmp/chart_stub.png", mime_type="image/png", width=1200, height=800, metadata={"spec": chart_type})
