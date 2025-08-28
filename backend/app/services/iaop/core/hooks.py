"""
IAOP钩子系统 - 事件驱动的扩展机制

提供灵活的钩子系统，支持在关键节点注册和执行自定义逻辑
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable, Awaitable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class HookType(Enum):
    """钩子类型"""
    # 系统级钩子
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    
    # 服务级钩子
    SERVICE_INIT = "service_init"
    SERVICE_READY = "service_ready"
    SERVICE_ERROR = "service_error"
    
    # 请求级钩子
    REQUEST_START = "request_start"
    REQUEST_END = "request_end"
    REQUEST_ERROR = "request_error"
    
    # Agent级钩子
    AGENT_BEFORE_EXECUTE = "agent_before_execute"
    AGENT_AFTER_EXECUTE = "agent_after_execute"
    AGENT_ERROR = "agent_error"
    
    # 上下文级钩子
    CONTEXT_CREATE = "context_create"
    CONTEXT_UPDATE = "context_update"
    CONTEXT_DESTROY = "context_destroy"
    
    # 数据处理钩子
    DATA_QUERY_START = "data_query_start"
    DATA_QUERY_END = "data_query_end"
    DATA_ANALYSIS_START = "data_analysis_start"
    DATA_ANALYSIS_END = "data_analysis_end"
    
    # 结果处理钩子
    CHART_GENERATED = "chart_generated"
    NARRATIVE_GENERATED = "narrative_generated"
    REPORT_COMPLETED = "report_completed"


@dataclass
class HookContext:
    """钩子上下文"""
    hook_type: HookType
    timestamp: datetime
    source: str  # 触发源
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取数据"""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置数据"""
        self.data[key] = value
    
    def update(self, data: Dict[str, Any]) -> None:
        """更新数据"""
        self.data.update(data)


class Hook:
    """钩子定义"""
    
    def __init__(self, name: str, handler: Callable, priority: int = 50, 
                 enabled: bool = True, async_handler: bool = True):
        self.name = name
        self.handler = handler
        self.priority = priority
        self.enabled = enabled
        self.async_handler = async_handler
        self.execution_count = 0
        self.last_execution = None
        self.errors = []
    
    async def execute(self, context: HookContext) -> Any:
        """执行钩子"""
        if not self.enabled:
            return None
        
        start_time = datetime.utcnow()
        
        try:
            if self.async_handler:
                if asyncio.iscoroutinefunction(self.handler):
                    result = await self.handler(context)
                else:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, self.handler, context
                    )
            else:
                result = self.handler(context)
            
            self.execution_count += 1
            self.last_execution = start_time
            
            return result
            
        except Exception as e:
            error_info = {
                'error': str(e),
                'timestamp': start_time.isoformat(),
                'context_data': context.data
            }
            self.errors.append(error_info)
            
            logger.error(f"钩子执行失败: {self.name}, 错误: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """获取钩子统计"""
        return {
            'name': self.name,
            'enabled': self.enabled,
            'priority': self.priority,
            'execution_count': self.execution_count,
            'last_execution': self.last_execution.isoformat() if self.last_execution else None,
            'error_count': len(self.errors),
            'recent_errors': self.errors[-5:]  # 最近5个错误
        }


class HookManager:
    """钩子管理器"""
    
    def __init__(self):
        self.hooks: Dict[HookType, List[Hook]] = {
            hook_type: [] for hook_type in HookType
        }
        self.global_hooks: List[Hook] = []  # 全局钩子，响应所有事件
        self._setup_default_hooks()
    
    def _setup_default_hooks(self):
        """设置默认钩子"""
        
        # 系统启动钩子
        self.register_hook(
            HookType.SYSTEM_STARTUP,
            "system_logger",
            self._log_system_event,
            priority=10
        )
        
        # 请求日志钩子
        self.register_hook(
            HookType.REQUEST_START,
            "request_logger",
            self._log_request_start,
            priority=10
        )
        
        self.register_hook(
            HookType.REQUEST_END,
            "request_logger",
            self._log_request_end,
            priority=10
        )
        
        # Agent执行日志钩子
        self.register_hook(
            HookType.AGENT_BEFORE_EXECUTE,
            "agent_logger",
            self._log_agent_execution,
            priority=10
        )
        
        logger.info("默认钩子设置完成")
    
    def register_hook(self, hook_type: HookType, name: str, handler: Callable,
                     priority: int = 50, enabled: bool = True, async_handler: bool = True) -> None:
        """注册钩子"""
        hook = Hook(name, handler, priority, enabled, async_handler)
        self.hooks[hook_type].append(hook)
        
        # 按优先级排序
        self.hooks[hook_type].sort(key=lambda h: h.priority)
        
        logger.info(f"注册钩子: {name} -> {hook_type.value}")
    
    def register_global_hook(self, name: str, handler: Callable, 
                           priority: int = 50, enabled: bool = True, async_handler: bool = True) -> None:
        """注册全局钩子"""
        hook = Hook(name, handler, priority, enabled, async_handler)
        self.global_hooks.append(hook)
        
        # 按优先级排序
        self.global_hooks.sort(key=lambda h: h.priority)
        
        logger.info(f"注册全局钩子: {name}")
    
    def unregister_hook(self, hook_type: HookType, name: str) -> bool:
        """取消注册钩子"""
        initial_count = len(self.hooks[hook_type])
        self.hooks[hook_type] = [h for h in self.hooks[hook_type] if h.name != name]
        
        removed = initial_count > len(self.hooks[hook_type])
        if removed:
            logger.info(f"取消注册钩子: {name} <- {hook_type.value}")
        
        return removed
    
    async def trigger_hook(self, hook_type: HookType, source: str, 
                          data: Dict[str, Any] = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """触发钩子"""
        context = HookContext(
            hook_type=hook_type,
            timestamp=datetime.utcnow(),
            source=source,
            data=data or {},
            metadata=metadata or {}
        )
        
        results = {}
        
        # 执行特定类型的钩子
        for hook in self.hooks[hook_type]:
            if hook.enabled:
                try:
                    result = await hook.execute(context)
                    if result is not None:
                        results[hook.name] = result
                except Exception as e:
                    logger.error(f"钩子执行失败: {hook.name}, 错误: {e}")
                    results[hook.name] = {'error': str(e)}
        
        # 执行全局钩子
        for hook in self.global_hooks:
            if hook.enabled:
                try:
                    result = await hook.execute(context)
                    if result is not None:
                        results[f"global_{hook.name}"] = result
                except Exception as e:
                    logger.error(f"全局钩子执行失败: {hook.name}, 错误: {e}")
                    results[f"global_{hook.name}"] = {'error': str(e)}
        
        return results
    
    def get_hook_stats(self) -> Dict[str, Any]:
        """获取钩子统计"""
        stats = {}
        
        for hook_type, hook_list in self.hooks.items():
            stats[hook_type.value] = [hook.get_stats() for hook in hook_list]
        
        stats['global_hooks'] = [hook.get_stats() for hook in self.global_hooks]
        
        return stats
    
    def enable_hook(self, hook_type: HookType, name: str) -> bool:
        """启用钩子"""
        for hook in self.hooks[hook_type]:
            if hook.name == name:
                hook.enabled = True
                return True
        return False
    
    def disable_hook(self, hook_type: HookType, name: str) -> bool:
        """禁用钩子"""
        for hook in self.hooks[hook_type]:
            if hook.name == name:
                hook.enabled = False
                return True
        return False
    
    # 默认钩子处理函数
    async def _log_system_event(self, context: HookContext):
        """系统事件日志"""
        event_type = context.hook_type.value
        logger.info(f"系统事件: {event_type} from {context.source}")
        return {'logged': True}
    
    async def _log_request_start(self, context: HookContext):
        """请求开始日志"""
        request_id = context.get('request_id', 'unknown')
        placeholder_text = context.get('placeholder_text', '')
        
        logger.info(f"请求开始: {request_id}")
        if placeholder_text:
            logger.info(f"占位符: {placeholder_text}")
        
        return {'request_start_logged': True}
    
    async def _log_request_end(self, context: HookContext):
        """请求结束日志"""
        request_id = context.get('request_id', 'unknown')
        success = context.get('success', True)
        execution_time = context.get('execution_time', 0)
        
        status = "成功" if success else "失败"
        logger.info(f"请求结束: {request_id} - {status}, 耗时: {execution_time:.2f}s")
        
        return {'request_end_logged': True}
    
    async def _log_agent_execution(self, context: HookContext):
        """Agent执行日志"""
        agent_name = context.get('agent_name', 'unknown')
        action = context.get('action', 'execute')
        
        logger.info(f"Agent执行: {agent_name}.{action}")
        return {'agent_execution_logged': True}


# 预定义的钩子处理函数
async def performance_monitor_hook(context: HookContext):
    """性能监控钩子"""
    if context.hook_type == HookType.REQUEST_END:
        execution_time = context.get('execution_time', 0)
        if execution_time > 10:  # 超过10秒的请求
            logger.warning(f"慢请求检测: {context.get('request_id')} - {execution_time:.2f}s")
            
            return {
                'slow_request_detected': True,
                'execution_time': execution_time,
                'threshold': 10
            }


async def cache_invalidation_hook(context: HookContext):
    """缓存失效钩子"""
    if context.hook_type == HookType.DATA_QUERY_END:
        # 数据查询完成后，可能需要清理相关缓存
        data_source = context.get('data_source')
        if data_source:
            logger.debug(f"数据源查询完成，考虑缓存策略: {data_source}")
            return {'cache_strategy_applied': True}


async def metrics_collection_hook(context: HookContext):
    """指标收集钩子"""
    metrics = {
        'hook_type': context.hook_type.value,
        'timestamp': context.timestamp.isoformat(),
        'source': context.source
    }
    
    # 收集特定指标
    if context.hook_type == HookType.AGENT_AFTER_EXECUTE:
        metrics.update({
            'agent_name': context.get('agent_name'),
            'execution_time': context.get('execution_time'),
            'success': context.get('success', True)
        })
    elif context.hook_type == HookType.CHART_GENERATED:
        metrics.update({
            'chart_type': context.get('chart_type'),
            'data_points': context.get('data_points', 0)
        })
    
    # 这里可以发送到监控系统
    logger.debug(f"收集指标: {metrics}")
    return {'metrics_collected': metrics}


async def notification_hook(context: HookContext):
    """通知钩子"""
    if context.hook_type == HookType.REQUEST_ERROR:
        error = context.get('error')
        request_id = context.get('request_id')
        
        # 发送错误通知（这里只是记录日志）
        logger.error(f"错误通知: 请求 {request_id} 发生错误 - {error}")
        
        return {
            'notification_sent': True,
            'notification_type': 'error',
            'details': {'request_id': request_id, 'error': str(error)}
        }


# 全局钩子管理器实例
_global_hook_manager = None

def get_hook_manager() -> HookManager:
    """获取全局钩子管理器"""
    global _global_hook_manager
    if _global_hook_manager is None:
        _global_hook_manager = HookManager()
    return _global_hook_manager


def setup_common_hooks():
    """设置常用钩子"""
    hook_manager = get_hook_manager()
    
    # 性能监控钩子
    hook_manager.register_hook(
        HookType.REQUEST_END,
        "performance_monitor",
        performance_monitor_hook,
        priority=20
    )
    
    # 缓存策略钩子
    hook_manager.register_hook(
        HookType.DATA_QUERY_END,
        "cache_invalidation",
        cache_invalidation_hook,
        priority=30
    )
    
    # 全局指标收集钩子
    hook_manager.register_global_hook(
        "metrics_collector",
        metrics_collection_hook,
        priority=5
    )
    
    # 错误通知钩子
    hook_manager.register_hook(
        HookType.REQUEST_ERROR,
        "error_notification",
        notification_hook,
        priority=90
    )
    
    logger.info("常用钩子设置完成")


# 钩子装饰器
def hook_trigger(hook_type: HookType, source: str = None):
    """钩子触发装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            hook_manager = get_hook_manager()
            actual_source = source or func.__name__
            
            # 触发前置钩子
            await hook_manager.trigger_hook(hook_type, actual_source, {
                'function': func.__name__,
                'args': str(args)[:100],  # 限制长度
                'kwargs': {k: str(v)[:100] for k, v in kwargs.items()}
            })
            
            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                
                # 触发成功钩子
                if hook_type == HookType.REQUEST_START:
                    await hook_manager.trigger_hook(HookType.REQUEST_END, actual_source, {
                        'success': True,
                        'result': 'completed'
                    })
                
                return result
                
            except Exception as e:
                # 触发错误钩子
                await hook_manager.trigger_hook(HookType.REQUEST_ERROR, actual_source, {
                    'error': str(e),
                    'function': func.__name__
                })
                raise
        
        return wrapper
    return decorator