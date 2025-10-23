"""
时间窗口工具（Loom 版）
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from .base import Tool


class TimeWindowTool(Tool):
    """计算任务执行的时间窗口。"""

    def __init__(self, container: Any = None) -> None:
        super().__init__()
        self.name = "time.window"
        self.description = "根据任务时间和粒度计算时间窗口"
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            timestamp = input_data.get("task_time")
            granularity = input_data.get("granularity") or input_data.get("kind") or "daily"
            timezone = input_data.get("timezone", "Asia/Shanghai")

            reference = (
                datetime.fromtimestamp(float(timestamp))
                if timestamp
                else datetime.now()
            )

            window = self._calculate_window(reference, granularity, timezone)
            return {
                "success": True,
                "window": window,
                "granularity": window["granularity"],
                "timezone": timezone,
                "reference_time": reference.isoformat(),
            }
        except Exception as exc:
            self._logger.error("时间窗口计算失败: %s", exc)
            return {"success": False, "error": str(exc)}

    def _calculate_window(self, ref: datetime, kind: str, timezone: str) -> Dict[str, Any]:
        if kind == "weekly":
            start = ref - timedelta(days=ref.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
            label = f"{start.strftime('%Y-%m-%d')}~{(end - timedelta(days=1)).strftime('%Y-%m-%d')}"
        elif kind == "monthly":
            start = ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)
            label = start.strftime("%Y-%m")
        elif kind == "yearly":
            start = ref.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = start.replace(year=start.year + 1)
            label = start.strftime("%Y")
        else:
            start = ref.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            label = start.strftime("%Y-%m-%d")
            kind = "daily"

        tz_suffix = "+08:00" if timezone == "Asia/Shanghai" else "+00:00"
        return {
            "start": f"{start.isoformat()}{tz_suffix}",
            "end": f"{end.isoformat()}{tz_suffix}",
            "label": label,
            "granularity": kind,
            "timezone": timezone,
        }


__all__ = ["TimeWindowTool"]
