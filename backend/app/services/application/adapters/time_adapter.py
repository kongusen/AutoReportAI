"""
时间上下文适配器

将现有的时间推断服务适配到 Stage-Aware Agent 系统
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TimeContextAdapter:
    """
    时间上下文适配器

    职责：
    1. 解析 Cron 表达式
    2. 推断数据时间范围
    3. 构建时间上下文供 Agent 使用
    """

    def __init__(self):
        """初始化适配器"""
        self.time_inference = None
        self.time_manager = None

        logger.debug("🔧 [TimeContextAdapter] 创建适配器")

    def _ensure_services_initialized(self):
        """确保服务已初始化"""
        if not self.time_inference:
            from app.services.data.template.time_inference_service import (
                TimeInferenceService
            )
            self.time_inference = TimeInferenceService()

        if not self.time_manager:
            from app.utils.time_context import TimeContextManager
            self.time_manager = TimeContextManager()

    def build_time_context(
        self,
        cron_expression: Optional[str] = None,
        execution_time: Optional[datetime] = None,
        timezone_offset: int = 8
    ) -> Dict[str, Any]:
        """
        构建时间上下文

        Args:
            cron_expression: Cron 表达式
            execution_time: 执行时间
            timezone_offset: 时区偏移（小时）

        Returns:
            时间上下文字典
        """
        self._ensure_services_initialized()

        if not cron_expression:
            logger.debug("⏰ [TimeContextAdapter] 无 Cron 表达式，使用当前时间")
            return {
                "has_time_context": False,
                "execution_time": execution_time or datetime.now(),
                "timezone_offset": timezone_offset
            }

        try:
            logger.info(f"⏰ [TimeContextAdapter] 解析 Cron: {cron_expression}")

            # 使用现有的时间管理器构建时间上下文
            time_context = self.time_manager.build_task_time_context(
                cron_expression=cron_expression,
                execution_time=execution_time
            )

            # 添加额外信息
            context = {
                "has_time_context": True,
                "period": time_context.get("period", "unknown"),
                "start_date": time_context.get("start_date"),
                "end_date": time_context.get("end_date"),
                "cron_expression": cron_expression,
                "execution_time": execution_time or datetime.now(),
                "timezone_offset": timezone_offset,
                "formatted_range": self._format_time_range(time_context)
            }

            logger.info(
                f"✅ [TimeContextAdapter] 时间上下文构建完成 - "
                f"周期: {context['period']}, 范围: {context['formatted_range']}"
            )

            return context

        except Exception as e:
            logger.error(f"❌ [TimeContextAdapter] 构建时间上下文失败: {e}")
            # 返回基础上下文
            return {
                "has_time_context": False,
                "execution_time": execution_time or datetime.now(),
                "timezone_offset": timezone_offset,
                "error": str(e)
            }

    def _format_time_range(self, time_context: Dict[str, Any]) -> str:
        """
        格式化时间范围为可读字符串

        Args:
            time_context: 时间上下文

        Returns:
            格式化的时间范围字符串
        """
        start_date = time_context.get("start_date")
        end_date = time_context.get("end_date")

        if not start_date or not end_date:
            return "未指定"

        try:
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

            # 格式化
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            return f"{start_str} 至 {end_str}"

        except Exception as e:
            logger.warning(f"⚠️ [TimeContextAdapter] 格式化时间范围失败: {e}")
            return f"{start_date} 至 {end_date}"

    def infer_report_period(self, cron_expression: Optional[str] = None) -> str:
        """
        推断报告周期

        Args:
            cron_expression: Cron 表达式

        Returns:
            报告周期（daily/weekly/monthly/yearly）
        """
        if not cron_expression:
            return "daily"

        try:
            # 解析 Cron 表达式的5个字段: m h dom mon dow
            parts = cron_expression.strip().split()
            if len(parts) < 5:
                return "daily"

            minute, hour, day_of_month, month, day_of_week = parts[:5]

            # 如果指定了星期几（非 *），判定为每周
            if day_of_week and day_of_week != '*':
                return "weekly"

            # 如果指定了月份（非 *），通常为每年
            if month and month != '*':
                return "yearly"

            # 如果指定了某一天（非 *），通常为每月
            if day_of_month and day_of_month != '*':
                return "monthly"

            # 其余默认按每日
            return "daily"

        except Exception as e:
            logger.warning(f"⚠️ [TimeContextAdapter] 推断报告周期失败: {e}")
            return "daily"

    def get_period_description(self, period: str) -> str:
        """
        获取周期的中文描述

        Args:
            period: 周期类型

        Returns:
            中文描述
        """
        descriptions = {
            "daily": "每日",
            "weekly": "每周",
            "monthly": "每月",
            "yearly": "每年",
        }
        return descriptions.get(period, "未知周期")

    def build_sql_time_filter(
        self,
        time_context: Dict[str, Any],
        date_column: str = "created_at"
    ) -> Optional[str]:
        """
        构建 SQL 时间过滤条件

        Args:
            time_context: 时间上下文
            date_column: 日期列名

        Returns:
            SQL WHERE 子句，如果无时间上下文返回 None
        """
        if not time_context.get("has_time_context"):
            return None

        start_date = time_context.get("start_date")
        end_date = time_context.get("end_date")

        if not start_date or not end_date:
            return None

        try:
            # 构建 SQL 过滤条件
            sql_filter = (
                f"{date_column} >= '{start_date}' "
                f"AND {date_column} <= '{end_date}'"
            )

            logger.debug(f"📊 [TimeContextAdapter] SQL时间过滤: {sql_filter}")
            return sql_filter

        except Exception as e:
            logger.warning(f"⚠️ [TimeContextAdapter] 构建SQL过滤条件失败: {e}")
            return None


__all__ = ["TimeContextAdapter"]
