"""
时间上下文管理器

处理动态时间范围的生成，支持不同的报告周期和调度表达式
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, date
from croniter import croniter
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

class TimeContextManager:
    """时间上下文管理器"""
    
    def __init__(self):
        pass
    
    def generate_time_context(
        self,
        report_period: str,
        execution_time: Optional[datetime] = None,
        schedule: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成时间上下文信息
        
        Args:
            report_period: 报告周期 (daily, weekly, monthly, yearly)
            execution_time: 执行时间，默认为当前时间
            schedule: Cron调度表达式，用于推断预期的执行频率
            
        Returns:
            Dict: 包含时间上下文的字典
        """
        if execution_time is None:
            execution_time = datetime.now()
        
        try:
            # 根据报告周期计算时间范围
            period_start, period_end = self._calculate_period_range(report_period, execution_time)
            
            # 生成SQL时间表达式
            sql_expressions = self._generate_sql_expressions(report_period, execution_time)
            
            # 生成人类可读的描述
            description = self._generate_period_description(report_period, period_start, period_end)
            
            time_context = {
                # 基础时间信息
                "execution_time": execution_time.isoformat(),
                "report_period": report_period,
                
                # 计算出的时间范围
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "period_start_date": period_start.strftime("%Y-%m-%d"),
                "period_end_date": period_end.strftime("%Y-%m-%d"),
                
                # SQL动态表达式
                "sql_expressions": sql_expressions,
                
                # 描述信息
                "description": description,
                "period_label": self._get_period_label(report_period, period_start),
                
                # 元数据
                "generated_at": datetime.now().isoformat(),
                "schedule": schedule,
                "days_in_period": (period_end - period_start).days + 1
            }
            
            logger.info(f"Generated time context for {report_period} period: {period_start} to {period_end}")
            return time_context
            
        except Exception as e:
            logger.error(f"Failed to generate time context: {e}")
            # 返回基础的时间上下文作为回退
            return self._get_fallback_context(execution_time, report_period)
    
    def _calculate_period_range(self, report_period: str, execution_time: datetime) -> Tuple[datetime, datetime]:
        """
        计算报告周期的时间范围
        
        Args:
            report_period: 报告周期
            execution_time: 执行时间
            
        Returns:
            Tuple[datetime, datetime]: (开始时间, 结束时间)
        """
        # 获取执行日期
        exec_date = execution_time.date()
        
        if report_period == "daily":
            # 日报：获取前一天的数据
            target_date = exec_date - timedelta(days=1)
            period_start = datetime.combine(target_date, datetime.min.time())
            period_end = datetime.combine(target_date, datetime.max.time())
            
        elif report_period == "weekly":
            # 周报：获取上周的数据（周一到周日）
            days_since_monday = exec_date.weekday()
            last_monday = exec_date - timedelta(days=days_since_monday + 7)
            last_sunday = last_monday + timedelta(days=6)
            period_start = datetime.combine(last_monday, datetime.min.time())
            period_end = datetime.combine(last_sunday, datetime.max.time())
            
        elif report_period == "monthly":
            # 月报：获取上个月的数据
            if exec_date.month == 1:
                last_month = exec_date.replace(year=exec_date.year - 1, month=12, day=1)
            else:
                last_month = exec_date.replace(month=exec_date.month - 1, day=1)
            
            # 计算上个月的最后一天
            next_month = last_month + relativedelta(months=1)
            last_day_of_month = next_month - timedelta(days=1)
            
            period_start = datetime.combine(last_month, datetime.min.time())
            period_end = datetime.combine(last_day_of_month, datetime.max.time())
            
        elif report_period == "yearly":
            # 年报：获取去年的数据
            last_year = exec_date.year - 1
            period_start = datetime(last_year, 1, 1, 0, 0, 0)
            period_end = datetime(last_year, 12, 31, 23, 59, 59)
            
        else:
            # 默认使用月报逻辑
            logger.warning(f"Unknown report period: {report_period}, using monthly as default")
            return self._calculate_period_range("monthly", execution_time)
        
        return period_start, period_end
    
    def _generate_sql_expressions(self, report_period: str, execution_time: datetime) -> Dict[str, str]:
        """
        生成SQL时间表达式
        
        Args:
            report_period: 报告周期
            execution_time: 执行时间
            
        Returns:
            Dict[str, str]: SQL表达式字典
        """
        expressions = {}
        
        if report_period == "daily":
            expressions.update({
                "current_date": "CURDATE()",
                "yesterday": "CURDATE() - INTERVAL 1 DAY",
                "period_start": "DATE(CURDATE() - INTERVAL 1 DAY)",
                "period_end": "DATE(CURDATE() - INTERVAL 1 DAY)",
                "period_start_datetime": "TIMESTAMP(CURDATE() - INTERVAL 1 DAY, '00:00:00')",
                "period_end_datetime": "TIMESTAMP(CURDATE() - INTERVAL 1 DAY, '23:59:59')"
            })
            
        elif report_period == "weekly":
            expressions.update({
                "current_date": "CURDATE()",
                "week_start": "DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) + 7 DAY)",
                "week_end": "DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) + 1 DAY)",
                "period_start": "DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) + 7 DAY)",
                "period_end": "DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) + 1 DAY)",
                "period_start_datetime": "TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) + 7 DAY), '00:00:00')",
                "period_end_datetime": "TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) + 1 DAY), '23:59:59')"
            })
            
        elif report_period == "monthly":
            expressions.update({
                "current_date": "CURDATE()",
                "last_month_start": "DATE_SUB(DATE_SUB(CURDATE(), INTERVAL DAY(CURDATE()) - 1 DAY), INTERVAL 1 MONTH)",
                "last_month_end": "DATE_SUB(DATE_SUB(CURDATE(), INTERVAL DAY(CURDATE()) DAY), INTERVAL 0 DAY)",
                "period_start": "DATE_SUB(DATE_SUB(CURDATE(), INTERVAL DAY(CURDATE()) - 1 DAY), INTERVAL 1 MONTH)",
                "period_end": "DATE_SUB(DATE_SUB(CURDATE(), INTERVAL DAY(CURDATE()) DAY), INTERVAL 0 DAY)",
                "period_start_datetime": "TIMESTAMP(DATE_SUB(DATE_SUB(CURDATE(), INTERVAL DAY(CURDATE()) - 1 DAY), INTERVAL 1 MONTH), '00:00:00')",
                "period_end_datetime": "TIMESTAMP(DATE_SUB(DATE_SUB(CURDATE(), INTERVAL DAY(CURDATE()) DAY), INTERVAL 0 DAY), '23:59:59')"
            })
            
        elif report_period == "yearly":
            expressions.update({
                "current_date": "CURDATE()",
                "last_year_start": "DATE_SUB(MAKEDATE(YEAR(CURDATE()), 1), INTERVAL 1 YEAR)",
                "last_year_end": "DATE_SUB(MAKEDATE(YEAR(CURDATE()), 1), INTERVAL 1 DAY)",
                "period_start": "DATE_SUB(MAKEDATE(YEAR(CURDATE()), 1), INTERVAL 1 YEAR)",
                "period_end": "DATE_SUB(MAKEDATE(YEAR(CURDATE()), 1), INTERVAL 1 DAY)",
                "period_start_datetime": "TIMESTAMP(DATE_SUB(MAKEDATE(YEAR(CURDATE()), 1), INTERVAL 1 YEAR), '00:00:00')",
                "period_end_datetime": "TIMESTAMP(DATE_SUB(MAKEDATE(YEAR(CURDATE()), 1), INTERVAL 1 DAY), '23:59:59')"
            })
        
        # 通用表达式
        expressions.update({
            "now": "NOW()",
            "current_timestamp": "CURRENT_TIMESTAMP()",
            "unix_timestamp": "UNIX_TIMESTAMP()",
        })
        
        return expressions
    
    def _generate_period_description(self, report_period: str, period_start: datetime, period_end: datetime) -> str:
        """生成周期描述"""
        start_str = period_start.strftime("%Y年%m月%d日")
        end_str = period_end.strftime("%Y年%m月%d日")
        
        if report_period == "daily":
            return f"日报 - {start_str}"
        elif report_period == "weekly":
            return f"周报 - {start_str}至{end_str}"
        elif report_period == "monthly":
            return f"月报 - {period_start.strftime('%Y年%m月')}"
        elif report_period == "yearly":
            return f"年报 - {period_start.strftime('%Y年')}"
        else:
            return f"报告 - {start_str}至{end_str}"
    
    def _get_period_label(self, report_period: str, period_start: datetime) -> str:
        """获取周期标签"""
        if report_period == "daily":
            return period_start.strftime("%Y-%m-%d")
        elif report_period == "weekly":
            return f"第{period_start.isocalendar()[1]}周 ({period_start.strftime('%Y')})"
        elif report_period == "monthly":
            return period_start.strftime("%Y年%m月")
        elif report_period == "yearly":
            return period_start.strftime("%Y年")
        else:
            return period_start.strftime("%Y-%m-%d")
    
    def _get_fallback_context(self, execution_time: datetime, report_period: str) -> Dict[str, Any]:
        """获取回退时间上下文"""
        yesterday = execution_time - timedelta(days=1)
        
        return {
            "execution_time": execution_time.isoformat(),
            "report_period": report_period,
            "period_start": yesterday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
            "period_end": yesterday.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat(),
            "period_start_date": yesterday.strftime("%Y-%m-%d"),
            "period_end_date": yesterday.strftime("%Y-%m-%d"),
            "sql_expressions": {
                "current_date": "CURDATE()",
                "yesterday": "CURDATE() - INTERVAL 1 DAY",
                "period_start": "CURDATE() - INTERVAL 1 DAY",
                "period_end": "CURDATE() - INTERVAL 1 DAY"
            },
            "description": f"回退模式 - {yesterday.strftime('%Y年%m月%d日')}",
            "period_label": yesterday.strftime("%Y-%m-%d"),
            "generated_at": datetime.now().isoformat(),
            "fallback": True,
            "days_in_period": 1
        }
    
    def replace_sql_time_placeholders(self, sql: str, time_context: Dict[str, Any]) -> str:
        """
        替换SQL中的时间占位符
        
        Args:
            sql: 原始SQL
            time_context: 时间上下文
            
        Returns:
            str: 替换后的SQL
        """
        try:
            sql_expressions = time_context.get("sql_expressions", {})
            
            # 替换常见的硬编码日期模式
            import re
            
            # 替换 '2024-01-01' 格式的硬编码日期
            date_pattern = r"'(\d{4}-\d{2}-\d{2})'"
            sql = re.sub(date_pattern, sql_expressions.get("period_start", "CURDATE()"), sql)
            
            # 替换 '2024-01-01 00:00:00' 格式的硬编码日期时间
            datetime_pattern = r"'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})'"
            sql = re.sub(datetime_pattern, sql_expressions.get("period_start_datetime", "NOW()"), sql)
            
            # 替换时间占位符变量
            for placeholder, expression in sql_expressions.items():
                sql = sql.replace(f"{{{placeholder}}}", expression)
                sql = sql.replace(f"${{{placeholder}}}", expression)
                sql = sql.replace(f"@{placeholder}", expression)
            
            logger.info(f"Replaced time placeholders in SQL")
            return sql
            
        except Exception as e:
            logger.error(f"Failed to replace SQL time placeholders: {e}")
            return sql

logger.info("✅ Time Context Manager loaded")