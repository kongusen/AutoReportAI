"""
Period Placeholder Handler (Domain)

Computes period values based on business task cycle (cron + execution time):
- daily: yesterday
- weekly: last 7 days ending yesterday
- monthly: previous calendar month
Returns string suitable for direct replacement in reports.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime
from app.utils.time_context import TimeContextManager


class PeriodHandler:
    def __init__(self) -> None:
        self._tm = TimeContextManager()

    async def compute(self, placeholder_text: str, time_ctx: Dict[str, Any]) -> Dict[str, Any]:
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"🔧 PeriodHandler.compute 开始，time_ctx类型: {type(time_ctx)}, 内容: {time_ctx}")

        # 优先使用cron表达式与执行时间推断周期
        cron = None
        exec_time: Optional[datetime] = None

        # 防御性地获取schedule
        schedule = time_ctx.get("schedule") if isinstance(time_ctx, dict) else {}
        logger.info(f"🔧 schedule类型: {type(schedule)}, 内容: {schedule}")

        try:
            if isinstance(schedule, dict):
                cron = schedule.get("cron_expression") or time_ctx.get("cron_expression")
            else:
                cron = time_ctx.get("cron_expression")
        except Exception as e:
            logger.error(f"🔧 获取cron表达式失败: {e}")
            cron = time_ctx.get("cron_expression") if isinstance(time_ctx, dict) else None
        try:
            et = time_ctx.get("execution_time") if isinstance(time_ctx, dict) else None
            logger.info(f"🔧 execution_time类型: {type(et)}, 内容: {et}")
            if isinstance(et, str):
                exec_time = datetime.fromisoformat(et)
            elif isinstance(et, datetime):
                exec_time = et
            else:
                exec_time = None
        except Exception as e:
            logger.error(f"🔧 解析execution_time失败: {e}")
            exec_time = None

        if cron:
            logger.info(f"🔧 调用TimeContextManager.build_task_time_context，cron: {cron}, exec_time: {exec_time}")
            ctx = self._tm.build_task_time_context(cron, exec_time)
            logger.info(f"🔧 build_task_time_context返回，ctx类型: {type(ctx)}, 内容: {ctx}")

            if isinstance(ctx, dict):
                start = ctx.get("data_start_time")
                end = ctx.get("data_end_time")
                value = start if start == end else f"{start}～{end}"
                return {"value": value, "meta": {"start_date": start, "end_date": end, "period": ctx.get("period")}}
            else:
                logger.error(f"🔧 build_task_time_context返回非字典类型: {type(ctx)}")
                # 继续到回退逻辑

        # 回退：使用传入的start/end（如果有）
        logger.info(f"🔧 使用回退逻辑，time_ctx类型: {type(time_ctx)}")

        if isinstance(time_ctx, dict):
            start = time_ctx.get("start_date") or time_ctx.get("data_start_date") or time_ctx.get("period_start_date")
            end = time_ctx.get("end_date") or time_ctx.get("data_end_date") or time_ctx.get("period_end_date")
        else:
            logger.error(f"🔧 time_ctx不是字典类型: {type(time_ctx)}")
            start = None
            end = None

        if not start and not end:
            # 最终回退：使用当前日期作为默认值
            from datetime import datetime, timedelta
            yesterday = datetime.now() - timedelta(days=1)
            start = end = yesterday.strftime('%Y-%m-%d')
            logger.info(f"🔧 使用默认昨日日期: {start}")

        value = start if start and (start == end) else (f"{start}～{end}" if (start and end) else "")
        return {"value": value, "meta": {"start_date": start, "end_date": end}}
