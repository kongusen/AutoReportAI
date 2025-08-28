from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class ContextScope(Enum):
    """上下文作用域"""
    SESSION = "session"
    TASK = "task"
    REQUEST = "request"
    GLOBAL = "global"


@dataclass
class ContextEntry:
    """上下文条目"""
    key: str
    value: Any
    scope: ContextScope
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_value(self, value: Any, metadata: Dict[str, Any] = None):
        """更新值和元数据"""
        self.value = value
        self.updated_at = datetime.utcnow()
        if metadata:
            self.metadata.update(metadata)


@dataclass
class EnhancedExecutionContext:
    """增强的执行上下文 - 整合AI模块的上下文管理功能"""
    session_id: str
    user_id: str
    request: Dict[str, Any]

    # 核心上下文数据存储
    context_entries: Dict[str, ContextEntry] = field(default_factory=dict)
    
    # 原有字段
    created_at: datetime = field(default_factory=datetime.utcnow)
    time_constraints: Dict[str, Any] = field(default_factory=dict)
    agent_results: Dict[str, Any] = field(default_factory=dict)
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    error_stack: List[Dict[str, Any]] = field(default_factory=list)
    
    # 新增字段
    task_id: Optional[str] = None
    capabilities: Dict[str, Any] = field(default_factory=dict)
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def set_context(self, key: str, value: Any, scope: ContextScope, 
                   metadata: Dict[str, Any] = None):
        """设置上下文值"""
        if key in self.context_entries:
            self.context_entries[key].update_value(value, metadata)
        else:
            self.context_entries[key] = ContextEntry(
                key=key,
                value=value,
                scope=scope,
                metadata=metadata or {}
            )
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """获取上下文值"""
        entry = self.context_entries.get(key)
        return entry.value if entry else default
    
    def get_context_by_scope(self, scope: ContextScope) -> Dict[str, Any]:
        """按作用域获取上下文"""
        return {
            key: entry.value 
            for key, entry in self.context_entries.items() 
            if entry.scope == scope
        }
    
    def merge_context(self, other: 'EnhancedExecutionContext', preserve_local: bool = True):
        """合并其他上下文"""
        for key, entry in other.context_entries.items():
            if preserve_local and key in self.context_entries:
                continue
            self.context_entries[key] = entry
    
    def clear_scope(self, scope: ContextScope):
        """清理指定作用域的上下文"""
        to_remove = [
            key for key, entry in self.context_entries.items() 
            if entry.scope == scope
        ]
        for key in to_remove:
            del self.context_entries[key]
    
    def add_execution_record(self, agent_name: str, action: str, 
                           result: Dict[str, Any], duration: float = None):
        """添加执行记录"""
        record = {
            'timestamp': datetime.utcnow().isoformat(),
            'agent_name': agent_name,
            'action': action,
            'result': result,
            'duration': duration
        }
        self.execution_history.append(record)
        
        # 保持历史记录在合理范围内
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-50:]
    
    # 时间约束便捷接口
    def set_statistics_period(self, period: str, scope: ContextScope = ContextScope.TASK):
        """设置任务统计周期"""
        self.set_context('statistics_period', period, scope)

    def set_task_time(self, task_time: datetime, scope: ContextScope = ContextScope.TASK):
        """设置任务触发时间"""
        self.set_context('task_time', task_time.isoformat(), scope)

    def set_time_window(self, start_time: datetime, end_time: datetime, scope: ContextScope = ContextScope.TASK):
        """设置查询时间窗口"""
        self.set_context('time_window_start', start_time.isoformat(), scope)
        self.set_context('time_window_end', end_time.isoformat(), scope)

    def get_time_constraints_dict(self) -> Dict[str, Any]:
        """获取与时间相关的所有约束字段"""
        return {
            'statistics_period': self.get_context('statistics_period'),
            'task_time': self.get_context('task_time'),
            'time_window_start': self.get_context('time_window_start'),
            'time_window_end': self.get_context('time_window_end')
        }

    def get_time_constraints_prompts(self) -> List[str]:
        """以提示词约束的形式返回时间相关信息"""
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


