"""
时间上下文管理器
为AI任务提供时间相关的上下文信息
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple
from croniter import croniter
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TaskTimeContext:
    """任务时间上下文"""
    current_time: datetime
    execution_time: datetime
    previous_execution: Optional[datetime]
    next_execution: Optional[datetime]
    cron_expression: Optional[str]
    task_period: str
    data_start_time: datetime
    data_end_time: datetime
    timezone_info: str
    period_description: str


class TimeContextManager:
    """时间上下文管理器"""
    
    def __init__(self, timezone_str: str = "Asia/Shanghai"):
        self.timezone = timezone.utc if timezone_str == "UTC" else timezone(timedelta(hours=8))  # 简化处理
        
    def build_task_time_context(
        self, 
        cron_expression: Optional[str] = None,
        execution_time: Optional[datetime] = None,
        task_type: str = "scheduled"
    ) -> TaskTimeContext:
        """构建任务时间上下文"""
        
        current_time = datetime.now(self.timezone)
        exec_time = execution_time or current_time
        
        # 解析cron表达式
        if cron_expression:
            try:
                cron = croniter(cron_expression, exec_time)
                previous_execution = cron.get_prev(datetime)
                next_execution = cron.get_next(datetime)
                
                # 推测任务周期
                period_info = self._analyze_cron_period(cron_expression)
                
            except Exception as e:
                logger.warning(f"解析cron表达式失败: {cron_expression}, 错误: {e}")
                previous_execution = exec_time - timedelta(days=1)
                next_execution = exec_time + timedelta(days=1)
                period_info = {"period": "daily", "description": "每日任务（推测）"}
        else:
            # 无cron表达式时的默认处理
            previous_execution = exec_time - timedelta(days=1)
            next_execution = exec_time + timedelta(days=1)
            period_info = {"period": "manual", "description": "手动触发任务"}
        
        # 根据任务周期推测数据时间范围
        data_range = self._calculate_data_range(exec_time, period_info["period"])
        
        return TaskTimeContext(
            current_time=current_time,
            execution_time=exec_time,
            previous_execution=previous_execution,
            next_execution=next_execution,
            cron_expression=cron_expression,
            task_period=period_info["period"],
            data_start_time=data_range[0],
            data_end_time=data_range[1],
            timezone_info=str(self.timezone),
            period_description=period_info["description"]
        )
    
    def _analyze_cron_period(self, cron_expr: str) -> Dict[str, str]:
        """分析cron表达式的周期性"""
        
        # 分解cron表达式: 分 时 日 月 周
        parts = cron_expr.strip().split()
        
        if len(parts) < 5:
            return {"period": "unknown", "description": "未知周期"}
        
        minute, hour, day, month, weekday = parts[:5]
        
        # 分析周期模式
        if minute != "*" and hour != "*" and day != "*" and month != "*":
            if weekday != "*":
                return {"period": "weekly", "description": f"每周{weekday}日 {hour}:{minute}"}
            else:
                return {"period": "monthly", "description": f"每月{day}日 {hour}:{minute}"}
        
        elif minute != "*" and hour != "*" and day == "*" and month == "*":
            if weekday != "*":
                return {"period": "weekly", "description": f"每周{weekday}日 {hour}:{minute}"}
            else:
                return {"period": "daily", "description": f"每日 {hour}:{minute}"}
        
        elif minute != "*" and hour == "*":
            return {"period": "hourly", "description": f"每小时第{minute}分钟"}
        
        elif minute == "*" and hour == "*" and day == "*":
            return {"period": "continuous", "description": "连续执行"}
        
        # 特殊模式识别
        if "0 0 * * 0" in cron_expr:  # 每周日午夜
            return {"period": "weekly", "description": "每周日午夜执行"}
        
        if "0 0 1 * *" in cron_expr:  # 每月1日午夜
            return {"period": "monthly", "description": "每月1日午夜执行"}
        
        if "0 0 1 1 *" in cron_expr:  # 每年1月1日
            return {"period": "yearly", "description": "每年1月1日执行"}
        
        # 默认分析
        return {"period": "custom", "description": f"自定义周期: {cron_expr}"}
    
    def _calculate_data_range(self, execution_time: datetime, period: str) -> Tuple[datetime, datetime]:
        """根据任务周期计算数据时间范围"""
        
        end_time = execution_time
        
        if period == "hourly":
            start_time = end_time - timedelta(hours=1)
        elif period == "daily":
            start_time = end_time - timedelta(days=1)
        elif period == "weekly":
            start_time = end_time - timedelta(weeks=1)
        elif period == "monthly":
            # 获取上个月同一天
            if end_time.month == 1:
                start_time = end_time.replace(year=end_time.year - 1, month=12)
            else:
                try:
                    start_time = end_time.replace(month=end_time.month - 1)
                except ValueError:
                    # 处理月末日期问题（如1月31日 -> 2月28日）
                    start_time = end_time - timedelta(days=30)
        elif period == "yearly":
            start_time = end_time.replace(year=end_time.year - 1)
        else:
            # 默认情况：过去24小时
            start_time = end_time - timedelta(days=1)
        
        return start_time, end_time
    
    def format_time_context_for_prompt(self, time_context: TaskTimeContext) -> str:
        """将时间上下文格式化为AI提示词"""
        
        return f"""
【任务时间上下文】
- 当前时间: {time_context.current_time.strftime('%Y-%m-%d %H:%M:%S')}
- 任务执行时间: {time_context.execution_time.strftime('%Y-%m-%d %H:%M:%S')}
- 任务周期: {time_context.period_description}
- 数据时间范围: {time_context.data_start_time.strftime('%Y-%m-%d %H:%M:%S')} 至 {time_context.data_end_time.strftime('%Y-%m-%d %H:%M:%S')}
- 上次执行: {time_context.previous_execution.strftime('%Y-%m-%d %H:%M:%S') if time_context.previous_execution else '无'}
- 下次执行: {time_context.next_execution.strftime('%Y-%m-%d %H:%M:%S') if time_context.next_execution else '无'}
- 时区: {time_context.timezone_info}
"""
    
    def get_data_range_sql_conditions(self, time_context: TaskTimeContext, date_column: str = "created_at") -> str:
        """生成数据时间范围的SQL条件"""
        
        start_str = time_context.data_start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_str = time_context.data_end_time.strftime('%Y-%m-%d %H:%M:%S')
        
        return f"{date_column} >= '{start_str}' AND {date_column} < '{end_str}'"
    
    def suggest_time_placeholders(self, time_context: TaskTimeContext) -> Dict[str, str]:
        """根据时间上下文建议时间占位符"""
        
        suggestions = {
            "{{报告日期}}": time_context.execution_time.strftime('%Y年%m月%d日'),
            "{{数据开始时间}}": time_context.data_start_time.strftime('%Y-%m-%d'),
            "{{数据结束时间}}": time_context.data_end_time.strftime('%Y-%m-%d'),
            "{{报告周期}}": time_context.period_description,
            "{{当前年份}}": str(time_context.execution_time.year),
            "{{当前月份}}": str(time_context.execution_time.month),
            "{{当前季度}}": f"Q{(time_context.execution_time.month - 1) // 3 + 1}",
        }
        
        # 根据周期添加特定建议
        if time_context.task_period == "weekly":
            suggestions["{{本周开始}}"] = (time_context.execution_time - timedelta(days=time_context.execution_time.weekday())).strftime('%Y-%m-%d')
            suggestions["{{上周同期}}"] = (time_context.execution_time - timedelta(weeks=1)).strftime('%Y-%m-%d')
        
        elif time_context.task_period == "monthly":
            suggestions["{{本月开始}}"] = time_context.execution_time.replace(day=1).strftime('%Y-%m-%d')
            suggestions["{{上月同期}}"] = time_context.previous_execution.strftime('%Y-%m-%d') if time_context.previous_execution else ""
        
        return suggestions


# 全局实例
time_context_manager = TimeContextManager()


def get_time_context_manager() -> TimeContextManager:
    """获取时间上下文管理器实例"""
    return time_context_manager


# 便捷函数
def create_task_time_context(
    cron_expression: Optional[str] = None,
    execution_time: Optional[datetime] = None,
    task_type: str = "scheduled"
) -> TaskTimeContext:
    """创建任务时间上下文的便捷函数"""
    return time_context_manager.build_task_time_context(cron_expression, execution_time, task_type)


def format_time_context_for_ai(time_context: TaskTimeContext) -> str:
    """为AI格式化时间上下文的便捷函数"""
    return time_context_manager.format_time_context_for_prompt(time_context)