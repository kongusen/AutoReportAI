"""
IAOP上下文管理器 - 整合AI模块的上下文管理功能
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

from .execution_context import EnhancedExecutionContext, ContextScope

logger = logging.getLogger(__name__)


class IAOPContextManager:
    """IAOP架构的上下文管理器"""
    
    def __init__(self):
        self.contexts: Dict[str, EnhancedExecutionContext] = {}
        self.global_context: Dict[str, Any] = {}
        self._context_processors: List[callable] = []
    
    def create_context(self, session_id: str, user_id: str, request: Dict[str, Any],
                      task_id: str = None) -> EnhancedExecutionContext:
        """创建新的执行上下文"""
        context = EnhancedExecutionContext(
            session_id=session_id,
            user_id=user_id,
            request=request,
            task_id=task_id
        )
        
        # 应用全局上下文
        for key, value in self.global_context.items():
            context.set_context(key, value, ContextScope.GLOBAL)
        
        # 应用上下文处理器
        for processor in self._context_processors:
            try:
                processor(context)
            except Exception as e:
                logger.warning(f"Context processor failed: {e}")
        
        self.contexts[session_id] = context
        return context
    
    def get_context(self, session_id: str) -> Optional[EnhancedExecutionContext]:
        """获取上下文"""
        return self.contexts.get(session_id)
    
    def update_global_context(self, key: str, value: Any):
        """更新全局上下文"""
        self.global_context[key] = value
        
        # 更新所有活跃上下文的全局值
        for context in self.contexts.values():
            context.set_context(key, value, ContextScope.GLOBAL)
    
    def register_context_processor(self, processor: callable):
        """注册上下文处理器"""
        self._context_processors.append(processor)
    
    def cleanup_expired_contexts(self, max_age_hours: int = 24):
        """清理过期上下文"""
        now = datetime.utcnow()
        expired_sessions = []
        
        for session_id, context in self.contexts.items():
            # 找到最新的活动时间
            latest_activity = max(
                (entry.updated_at for entry in context.context_entries.values()),
                default=context.created_at
            )
            
            hours_since_activity = (now - latest_activity).total_seconds() / 3600
            if hours_since_activity > max_age_hours:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.contexts[session_id]
            logger.info(f"Cleaned up expired context: {session_id}")
    
    # 时间约束管理接口
    def set_task_time_constraints(
        self,
        session_id: str,
        *,
        statistics_period: Optional[str] = None,
        task_time: Optional[datetime] = None,
        time_window_start: Optional[datetime] = None,
        time_window_end: Optional[datetime] = None,
        scope: ContextScope = ContextScope.TASK,
    ) -> None:
        """批量设置任务统计周期与时间窗口"""
        context = self.get_context(session_id)
        if not context:
            raise ValueError(f"Context not found for session: {session_id}")

        if statistics_period is not None:
            context.set_statistics_period(statistics_period, scope)
        if task_time is not None:
            context.set_task_time(task_time, scope)
        if time_window_start is not None or time_window_end is not None:
            if time_window_start is not None and time_window_end is not None:
                context.set_time_window(time_window_start, time_window_end, scope)
            elif time_window_start is not None:
                context.set_context('time_window_start', time_window_start.isoformat(), scope)
            elif time_window_end is not None:
                context.set_context('time_window_end', time_window_end.isoformat(), scope)
        else:
            # 自动计算时间窗口
            period = statistics_period or context.get_context('statistics_period')
            task_time_val = task_time or context.get_context('task_time')
            if isinstance(task_time_val, str):
                try:
                    task_time_val = datetime.fromisoformat(task_time_val)
                except Exception:
                    task_time_val = None
            if period and task_time_val:
                start_dt, end_dt = self._compute_time_window(period, task_time_val)
                context.set_time_window(start_dt, end_dt, scope)

    def get_task_time_constraints(self, session_id: str) -> Dict[str, Any]:
        """获取指定会话的时间约束字典"""
        context = self.get_context(session_id)
        if not context:
            raise ValueError(f"Context not found for session: {session_id}")
        return context.get_time_constraints_dict()

    def build_time_constraints_for_prompt(self, session_id: str) -> List[str]:
        """为Prompt生成标准化时间约束提示列表"""
        context = self.get_context(session_id)
        if not context:
            raise ValueError(f"Context not found for session: {session_id}")
        return context.get_time_constraints_prompts()

    def _compute_time_window(self, statistics_period: str, task_time: datetime) -> Tuple[datetime, datetime]:
        """根据统计周期与任务时间计算时间窗口"""
        period = (statistics_period or '').lower()
        tt = task_time

        if period == 'hourly':
            start = tt.replace(minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=1) - timedelta(seconds=1)
            return start, end

        if period == 'daily':
            start = tt.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1) - timedelta(seconds=1)
            return start, end

        if period == 'weekly':
            weekday = tt.isoweekday()
            start = tt.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=weekday-1)
            end = start + timedelta(days=7) - timedelta(seconds=1)
            return start, end

        if period == 'monthly':
            start = tt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start.month == 12:
                next_month = start.replace(year=start.year+1, month=1)
            else:
                next_month = start.replace(month=start.month+1)
            end = next_month - timedelta(seconds=1)
            return start, end

        if period == 'quarterly':
            q_start_month = ((tt.month - 1) // 3) * 3 + 1
            start = tt.replace(month=q_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
            if q_start_month == 10:
                next_q = start.replace(year=start.year+1, month=1)
            else:
                next_q = start.replace(month=q_start_month+3)
            end = next_q - timedelta(seconds=1)
            return start, end

        if period == 'yearly':
            start = tt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = start.replace(year=start.year+1) - timedelta(seconds=1)
            return start, end

        # default: daily
        start = tt.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1) - timedelta(seconds=1)
        return start, end

    def compute_and_set_time_window(self, session_id: str, *, scope: ContextScope = ContextScope.TASK) -> Dict[str, Any]:
        """根据当前上下文计算并设置时间窗口"""
        context = self.get_context(session_id)
        if not context:
            raise ValueError(f"Context not found for session: {session_id}")
        
        period = context.get_context('statistics_period')
        tt = context.get_context('task_time')
        if not period or not tt:
            return context.get_time_constraints_dict()
        
        if isinstance(tt, str):
            try:
                tt = datetime.fromisoformat(tt)
            except Exception:
                return context.get_time_constraints_dict()
        
        start_dt, end_dt = self._compute_time_window(period, tt)
        context.set_time_window(start_dt, end_dt, scope)
        return context.get_time_constraints_dict()


# 全局上下文管理器实例
_global_iaop_context_manager = None

def get_iaop_context_manager() -> IAOPContextManager:
    """获取全局IAOP上下文管理器"""
    global _global_iaop_context_manager
    if _global_iaop_context_manager is None:
        _global_iaop_context_manager = IAOPContextManager()
    return _global_iaop_context_manager