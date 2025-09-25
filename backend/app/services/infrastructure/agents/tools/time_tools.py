"""
时间相关工具

提供时间窗口计算和时间上下文处理功能
"""

import logging
from typing import Dict, Any
from datetime import datetime, timedelta
import time

from .base import Tool


class TimeWindowTool(Tool):
    """时间窗口计算工具"""

    def __init__(self, container):
        super().__init__()
        self.name = "time.window"
        self.description = "计算或修正任务执行时间窗口"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """计算时间窗口"""
        try:
            # 获取时间参数
            task_time = input_data.get("task_time")
            granularity = input_data.get("granularity", "daily")
            timezone = input_data.get("timezone", "Asia/Shanghai")
            kind = input_data.get("kind", granularity)

            # 如果没有指定时间，使用当前时间
            if not task_time:
                ref_time = datetime.now()
            else:
                ref_time = datetime.fromtimestamp(float(task_time))

            # 计算时间窗口
            window = self._calculate_time_window(ref_time, kind, timezone)

            return {
                "success": True,
                "window": window,
                "granularity": kind,
                "timezone": timezone,
                "reference_time": ref_time.isoformat()
            }

        except Exception as e:
            self._logger.error(f"时间窗口计算失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def _calculate_time_window(self, ref_time: datetime, kind: str, timezone: str) -> Dict[str, Any]:
        """计算时间窗口"""
        if kind == "daily":
            # 当天的时间范围
            start = ref_time.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            label = start.strftime("%Y-%m-%d")

        elif kind == "weekly":
            # 本周的时间范围 (周一到周日)
            days_since_monday = ref_time.weekday()
            start = (ref_time - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
            label = f"{start.strftime('%Y-%m-%d')} to {(end-timedelta(days=1)).strftime('%Y-%m-%d')}"

        elif kind == "monthly":
            # 本月的时间范围
            start = ref_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)
            label = start.strftime("%Y-%m")

        elif kind == "yearly":
            # 本年的时间范围
            start = ref_time.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = start.replace(year=start.year + 1)
            label = start.strftime("%Y")

        else:
            # 默认当天
            start = ref_time.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            label = start.strftime("%Y-%m-%d")

        # 生成时区感知的时间字符串
        tz_suffix = "+08:00" if timezone == "Asia/Shanghai" else "+00:00"

        return {
            "start": f"{start.isoformat()}{tz_suffix}",
            "end": f"{end.isoformat()}{tz_suffix}",
            "label": label,
            "granularity": kind,
            "timezone": timezone
        }