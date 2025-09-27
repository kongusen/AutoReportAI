"""
Chart Rendering Port (Domain Port)

Turns a chart spec and tabular data into a rendered artifact (e.g., image).
Implementation belongs to Infrastructure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ChartSpec:
    chart_type: str            # bar|line|pie|area|table
    x: Optional[str] = None
    y: Optional[str] = None
    series: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChartArtifact:
    path: str
    mime_type: str = "image/png"
    width: int = 1200
    height: int = 800
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChartRenderingPort(ABC):
    @abstractmethod
    async def render(self, spec: ChartSpec, data_columns: list[str], data_rows: list[list[Any]]) -> ChartArtifact:
        pass

