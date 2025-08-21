from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict
import time


@dataclass
class MetricsCollector:
    """极简指标收集器占位实现"""

    counters: Dict[str, int] = field(default_factory=dict)
    timers: Dict[str, float] = field(default_factory=dict)

    def incr(self, name: str, value: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + value

    def start_timer(self, name: str) -> None:
        self.timers[name] = time.time()

    def end_timer(self, name: str) -> float:
        start = self.timers.pop(name, None)
        if start is None:
            return 0.0
        return time.time() - start


