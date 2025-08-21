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
from typing import Dict, Any, List, Optional, Type, Union
from dataclasses import dataclass, field
from datetime import datetime
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