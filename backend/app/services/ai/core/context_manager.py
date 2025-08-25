"""
Agent Context Manager - 上下文工程核心模块

实现上下文感知的Agent执行框架，支持：
1. 上下文状态管理
2. 上下文传播和继承
3. 上下文感知的决策
4. 动态上下文更新
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, Type, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ContextScope(Enum):
    """上下文作用域"""
    SESSION = "session"      # 会话级别
    TASK = "task"           # 任务级别
    REQUEST = "request"     # 请求级别
    GLOBAL = "global"       # 全局级别


@dataclass
class ContextEntry:
    """上下文条目"""
    key: str
    value: Any
    scope: ContextScope
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_value(self, value: Any, metadata: Dict[str, Any] = None):
        """更新值和元数据"""
        self.value = value
        self.updated_at = datetime.now()
        if metadata:
            self.metadata.update(metadata)


@dataclass
class AgentContext:
    """Agent执行上下文"""
    session_id: str
    task_id: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # 上下文数据存储
    entries: Dict[str, ContextEntry] = field(default_factory=dict)
    
    # 能力和状态
    capabilities: Dict[str, Any] = field(default_factory=dict)
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # 配置
    config: Dict[str, Any] = field(default_factory=dict)
    
    def set_context(self, key: str, value: Any, scope: ContextScope, 
                   metadata: Dict[str, Any] = None):
        """设置上下文值"""
        if key in self.entries:
            self.entries[key].update_value(value, metadata)
        else:
            self.entries[key] = ContextEntry(
                key=key,
                value=value,
                scope=scope,
                metadata=metadata or {}
            )
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """获取上下文值"""
        entry = self.entries.get(key)
        return entry.value if entry else default
    
    def get_context_by_scope(self, scope: ContextScope) -> Dict[str, Any]:
        """按作用域获取上下文"""
        return {
            key: entry.value 
            for key, entry in self.entries.items() 
            if entry.scope == scope
        }
    
    def merge_context(self, other: 'AgentContext', preserve_local: bool = True):
        """合并其他上下文"""
        for key, entry in other.entries.items():
            if preserve_local and key in self.entries:
                continue
            self.entries[key] = entry
    
    def clear_scope(self, scope: ContextScope):
        """清理指定作用域的上下文"""
        to_remove = [
            key for key, entry in self.entries.items() 
            if entry.scope == scope
        ]
        for key in to_remove:
            del self.entries[key]
    
    def add_execution_record(self, agent_name: str, action: str, 
                           result: Dict[str, Any], duration: float = None):
        """添加执行记录"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'agent_name': agent_name,
            'action': action,
            'result': result,
            'duration': duration
        }
        self.execution_history.append(record)
        
        # 保持历史记录在合理范围内
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-50:]

    # ===== 任务时间/统计周期：便捷接口 =====
    def set_statistics_period(self, period: str, scope: ContextScope = ContextScope.TASK):
        """设置任务统计周期，例如: hourly/daily/weekly/monthly/quarterly/yearly/custom"""
        self.set_context('statistics_period', period, scope)

    def set_task_time(self, task_time: datetime, scope: ContextScope = ContextScope.TASK):
        """设置任务触发时间/任务时间"""
        # 存储为 ISO 字符串，避免时区/序列化问题
        self.set_context('task_time', task_time.isoformat() if isinstance(task_time, datetime) else task_time, scope)

    def set_time_window(self, start_time: datetime, end_time: datetime, scope: ContextScope = ContextScope.TASK):
        """设置查询时间窗口（开始/结束）"""
        start_val = start_time.isoformat() if isinstance(start_time, datetime) else start_time
        end_val = end_time.isoformat() if isinstance(end_time, datetime) else end_time
        self.set_context('time_window_start', start_val, scope)
        self.set_context('time_window_end', end_val, scope)

    def get_time_constraints(self) -> Dict[str, Any]:
        """获取与时间相关的所有约束字段"""
        return {
            'statistics_period': self.get_context('statistics_period'),
            'task_time': self.get_context('task_time'),
            'time_window_start': self.get_context('time_window_start'),
            'time_window_end': self.get_context('time_window_end')
        }

    def get_time_constraints_prompts(self) -> List[str]:
        """以提示词约束的形式返回时间相关信息，便于拼接到 Prompt 中"""
        constraints: List[str] = []
        period = self.get_context('statistics_period')
        if period:
            constraints.append(f"统计周期: {period}")
        tws = self.get_context('time_window_start')
        twe = self.get_context('time_window_end')
        if tws or twe:
            constraints.append(f"时间范围: {tws or '-'} 至 {twe or '-'}")
        task_time = self.get_context('task_time')
        if task_time:
            constraints.append(f"任务时间: {task_time}")
        return constraints


class ContextManager:
    """上下文管理器"""
    
    def __init__(self):
        self.contexts: Dict[str, AgentContext] = {}
        self.global_context: Dict[str, Any] = {}
        self._context_processors: List[callable] = []
    
    def create_context(self, session_id: str, task_id: str = None, 
                      user_id: str = None) -> AgentContext:
        """创建新的上下文"""
        context = AgentContext(
            session_id=session_id,
            task_id=task_id,
            user_id=user_id
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
    
    def get_context(self, session_id: str) -> Optional[AgentContext]:
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
        now = datetime.now()
        expired_sessions = []
        
        for session_id, context in self.contexts.items():
            # 找到最新的活动时间
            latest_activity = max(
                (entry.updated_at for entry in context.entries.values()),
                default=datetime.now()
            )
            
            hours_since_activity = (now - latest_activity).total_seconds() / 3600
            if hours_since_activity > max_age_hours:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.contexts[session_id]
            logger.info(f"Cleaned up expired context: {session_id}")

    # ===== 任务时间/统计周期：管理器级接口（供 task 调用） =====
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
        """在指定上下文中批量设置任务统计周期与时间窗口/任务时间

        示例：
            get_context_manager().set_task_time_constraints(
                session_id,
                statistics_period="monthly",
                task_time=datetime.utcnow(),
                time_window_start=start_dt,
                time_window_end=end_dt,
            )
        """
        context = self.get_context(session_id)
        if not context:
            raise ValueError(f"Context not found for session: {session_id}")

        if statistics_period is not None:
            context.set_statistics_period(statistics_period, scope)
        if task_time is not None:
            context.set_task_time(task_time, scope)
        if time_window_start is not None or time_window_end is not None:
            # 允许单侧设置：仅有 start 或仅有 end
            if time_window_start is not None and time_window_end is not None:
                context.set_time_window(time_window_start, time_window_end, scope)
            elif time_window_start is not None:
                context.set_context('time_window_start', time_window_start.isoformat() if isinstance(time_window_start, datetime) else time_window_start, scope)
            elif time_window_end is not None:
                context.set_context('time_window_end', time_window_end.isoformat() if isinstance(time_window_end, datetime) else time_window_end, scope)
        else:
            # 若仅提供了统计周期与任务时间，自动计算时间窗口
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
        """读取指定会话的时间约束字典"""
        context = self.get_context(session_id)
        if not context:
            raise ValueError(f"Context not found for session: {session_id}")
        return context.get_time_constraints()

    def build_time_constraints_for_prompt(self, session_id: str) -> List[str]:
        """为 Prompt 生成标准化时间约束提示列表"""
        context = self.get_context(session_id)
        if not context:
            raise ValueError(f"Context not found for session: {session_id}")
        return context.get_time_constraints_prompts()

    # ===== 计算时间窗口工具 =====
    def _compute_time_window(self, statistics_period: str, task_time: datetime) -> Tuple[datetime, datetime]:
        """根据统计周期与任务时间计算时间窗口 [start, end]

        周期支持：hourly/daily/weekly/monthly/quarterly/yearly
        规则：
          - hourly: 本小时 00 分至 59 分 59 秒
          - daily: 自 00:00:00 至 23:59:59
          - weekly: ISO 周（周一 00:00:00 至 周日 23:59:59）
          - monthly: 当月 1 日 00:00:00 至 当月末日 23:59:59
          - quarterly: 当季度首月 1 日 00:00:00 至 季末月末日 23:59:59
          - yearly: 当年 1 月 1 日 00:00:00 至 12 月 31 日 23:59:59
        """
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
            # ISO: Monday is 1, Sunday is 7
            weekday = tt.isoweekday()
            start = tt.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=weekday-1)
            end = start + timedelta(days=7) - timedelta(seconds=1)
            return start, end

        if period == 'monthly':
            start = tt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # next month
            if start.month == 12:
                next_month = start.replace(year=start.year+1, month=1)
            else:
                next_month = start.replace(month=start.month+1)
            end = next_month - timedelta(seconds=1)
            return start, end

        if period == 'quarterly':
            # Q1:1-3, Q2:4-6, Q3:7-9, Q4:10-12
            q_start_month = ((tt.month - 1) // 3) * 3 + 1
            start = tt.replace(month=q_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
            # next quarter start
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

        # default fallback: daily
        start = tt.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1) - timedelta(seconds=1)
        return start, end

    def compute_and_set_time_window(self, session_id: str, *, scope: ContextScope = ContextScope.TASK) -> Dict[str, Any]:
        """根据当前上下文中的 statistics_period 与 task_time 计算并设置时间窗口，返回设置后的约束字典"""
        context = self.get_context(session_id)
        if not context:
            raise ValueError(f"Context not found for session: {session_id}")
        period = context.get_context('statistics_period')
        tt = context.get_context('task_time')
        if not period or not tt:
            return context.get_time_constraints()
        if isinstance(tt, str):
            try:
                tt = datetime.fromisoformat(tt)
            except Exception:
                return context.get_time_constraints()
        start_dt, end_dt = self._compute_time_window(period, tt)
        context.set_time_window(start_dt, end_dt, scope)
        return context.get_time_constraints()


class ContextAwareAgent:
    """上下文感知的Agent基类"""
    
    def __init__(self, name: str, context_manager: ContextManager):
        self.name = name
        self.context_manager = context_manager
        self._capabilities: Dict[str, Any] = {}
        self._context_requirements: List[str] = []
    
    def register_capability(self, capability_name: str, description: str, 
                          metadata: Dict[str, Any] = None):
        """注册能力"""
        self._capabilities[capability_name] = {
            'description': description,
            'metadata': metadata or {}
        }
    
    def require_context(self, *context_keys: str):
        """声明所需的上下文键"""
        self._context_requirements.extend(context_keys)
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取能力列表"""
        return self._capabilities.copy()
    
    async def execute_with_context(self, session_id: str, action: str, 
                                 parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """在上下文中执行操作"""
        context = self.context_manager.get_context(session_id)
        if not context:
            raise ValueError(f"Context not found for session: {session_id}")
        
        # 检查上下文要求
        missing_context = [
            key for key in self._context_requirements 
            if context.get_context(key) is None
        ]
        if missing_context:
            logger.warning(f"Missing required context: {missing_context}")
        
        # 记录执行开始
        start_time = datetime.now()
        
        try:
            # 执行具体操作
            result = await self._execute_action(context, action, parameters or {})
            
            # 记录执行结果
            duration = (datetime.now() - start_time).total_seconds()
            context.add_execution_record(
                agent_name=self.name,
                action=action,
                result=result,
                duration=duration
            )
            
            return result
            
        except Exception as e:
            # 记录执行错误
            duration = (datetime.now() - start_time).total_seconds()
            error_result = {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
            context.add_execution_record(
                agent_name=self.name,
                action=action,
                result=error_result,
                duration=duration
            )
            raise
    
    async def _execute_action(self, context: AgentContext, action: str, 
                            parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行具体操作 - 子类需要实现"""
        raise NotImplementedError("Subclasses must implement _execute_action")
    
    def update_context(self, context: AgentContext, key: str, value: Any, 
                      scope: ContextScope = ContextScope.TASK):
        """更新上下文"""
        context.set_context(key, value, scope, {'updated_by': self.name})


# 全局上下文管理器实例
_global_context_manager = None

def get_context_manager() -> ContextManager:
    """获取全局上下文管理器"""
    global _global_context_manager
    if _global_context_manager is None:
        _global_context_manager = ContextManager()
    return _global_context_manager