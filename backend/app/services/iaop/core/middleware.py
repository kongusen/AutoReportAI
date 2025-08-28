"""
IAOP中间件系统 - 提供可插拔的处理管道

支持的中间件类型：
- 请求/响应中间件
- Agent执行中间件  
- 上下文处理中间件
- 缓存中间件
- 监控中间件
- 错误处理中间件
"""

import logging
import time
import asyncio
from typing import Dict, List, Any, Optional, Callable, Awaitable, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class MiddlewareType(Enum):
    """中间件类型"""
    PRE_REQUEST = "pre_request"
    POST_REQUEST = "post_request"
    PRE_AGENT_EXECUTION = "pre_agent_execution"
    POST_AGENT_EXECUTION = "post_agent_execution"
    PRE_CONTEXT_CREATE = "pre_context_create"
    POST_CONTEXT_CREATE = "post_context_create"
    ERROR_HANDLER = "error_handler"
    CACHE_HANDLER = "cache_handler"
    METRICS_COLLECTOR = "metrics_collector"


@dataclass
class MiddlewareContext:
    """中间件上下文"""
    request_id: str
    middleware_type: MiddlewareType
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取数据"""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置数据"""
        self.data[key] = value
    
    def update(self, data: Dict[str, Any]) -> None:
        """批量更新数据"""
        self.data.update(data)


class BaseMiddleware(ABC):
    """中间件基类"""
    
    def __init__(self, name: str, priority: int = 50):
        self.name = name
        self.priority = priority
        self.enabled = True
        self.metrics = {
            'invocation_count': 0,
            'success_count': 0,
            'error_count': 0,
            'total_duration': 0.0
        }
    
    @abstractmethod
    async def process(self, context: MiddlewareContext) -> Optional[Dict[str, Any]]:
        """处理中间件逻辑"""
        pass
    
    async def execute(self, context: MiddlewareContext) -> Optional[Dict[str, Any]]:
        """执行中间件（带监控）"""
        if not self.enabled:
            return None
        
        start_time = time.time()
        self.metrics['invocation_count'] += 1
        
        try:
            result = await self.process(context)
            self.metrics['success_count'] += 1
            return result
        except Exception as e:
            self.metrics['error_count'] += 1
            logger.error(f"中间件执行失败: {self.name}, 错误: {e}")
            raise
        finally:
            duration = time.time() - start_time
            self.metrics['total_duration'] += duration
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取中间件指标"""
        return {
            'name': self.name,
            'enabled': self.enabled,
            'priority': self.priority,
            **self.metrics,
            'average_duration': (
                self.metrics['total_duration'] / self.metrics['invocation_count']
                if self.metrics['invocation_count'] > 0 else 0
            ),
            'success_rate': (
                self.metrics['success_count'] / self.metrics['invocation_count']
                if self.metrics['invocation_count'] > 0 else 0
            )
        }


class RequestLoggingMiddleware(BaseMiddleware):
    """请求日志中间件"""
    
    def __init__(self, priority: int = 10):
        super().__init__("request_logging", priority)
    
    async def process(self, context: MiddlewareContext) -> Optional[Dict[str, Any]]:
        request_data = context.get('request')
        if request_data:
            logger.info(f"处理请求: {context.request_id}, 类型: {context.middleware_type.value}")
            
            # 记录关键请求信息
            if isinstance(request_data, dict):
                placeholder_text = request_data.get('placeholder_text', '')
                if placeholder_text:
                    logger.info(f"占位符文本: {placeholder_text}")
        
        return None


class PerformanceMonitoringMiddleware(BaseMiddleware):
    """性能监控中间件"""
    
    def __init__(self, priority: int = 5):
        super().__init__("performance_monitoring", priority)
        self.request_times = {}
    
    async def process(self, context: MiddlewareContext) -> Optional[Dict[str, Any]]:
        request_id = context.request_id
        
        if context.middleware_type == MiddlewareType.PRE_REQUEST:
            self.request_times[request_id] = time.time()
        elif context.middleware_type == MiddlewareType.POST_REQUEST:
            start_time = self.request_times.pop(request_id, None)
            if start_time:
                duration = time.time() - start_time
                context.set('execution_time', duration)
                logger.info(f"请求执行时间: {request_id} - {duration:.2f}s")
        
        return None


class CacheMiddleware(BaseMiddleware):
    """缓存中间件"""
    
    def __init__(self, priority: int = 20, ttl: int = 3600):
        super().__init__("cache", priority)
        self.cache = {}  # 简单内存缓存
        self.ttl = ttl
        self.cache_hits = 0
        self.cache_misses = 0
    
    async def process(self, context: MiddlewareContext) -> Optional[Dict[str, Any]]:
        if context.middleware_type == MiddlewareType.PRE_REQUEST:
            # 尝试从缓存获取
            cache_key = self._generate_cache_key(context)
            cached_result = self._get_from_cache(cache_key)
            
            if cached_result:
                self.cache_hits += 1
                context.set('cached_result', cached_result)
                context.set('cache_hit', True)
                logger.debug(f"缓存命中: {cache_key}")
                return {'cached_result': cached_result}
            else:
                self.cache_misses += 1
                context.set('cache_key', cache_key)
                context.set('cache_hit', False)
        
        elif context.middleware_type == MiddlewareType.POST_REQUEST:
            # 存储到缓存
            cache_key = context.get('cache_key')
            result = context.get('result')
            
            if cache_key and result and not context.get('cache_hit'):
                self._store_to_cache(cache_key, result)
                logger.debug(f"结果已缓存: {cache_key}")
        
        return None
    
    def _generate_cache_key(self, context: MiddlewareContext) -> str:
        """生成缓存键"""
        request_data = context.get('request', {})
        
        # 基于请求内容生成缓存键
        key_parts = [
            request_data.get('placeholder_text', ''),
            str(request_data.get('data_source_context', {})),
            str(request_data.get('template_context', {}))
        ]
        
        import hashlib
        return hashlib.md5('|'.join(key_parts).encode()).hexdigest()
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取"""
        if key in self.cache:
            entry_time, value = self.cache[key]
            if time.time() - entry_time < self.ttl:
                return value
            else:
                # 过期，删除
                del self.cache[key]
        return None
    
    def _store_to_cache(self, key: str, value: Any) -> None:
        """存储到缓存"""
        self.cache[key] = (time.time(), value)
        
        # 简单的缓存清理
        if len(self.cache) > 1000:
            # 删除最旧的条目
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][0])
            del self.cache[oldest_key]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self.cache_hits + self.cache_misses
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate': self.cache_hits / total_requests if total_requests > 0 else 0,
            'cached_items': len(self.cache),
            'ttl': self.ttl
        }


class ErrorHandlingMiddleware(BaseMiddleware):
    """错误处理中间件"""
    
    def __init__(self, priority: int = 100):
        super().__init__("error_handling", priority)
        self.error_counts = {}
    
    async def process(self, context: MiddlewareContext) -> Optional[Dict[str, Any]]:
        if context.middleware_type == MiddlewareType.ERROR_HANDLER:
            error = context.get('error')
            error_type = type(error).__name__ if error else 'UnknownError'
            
            # 统计错误
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            
            # 记录错误
            logger.error(f"处理错误: {error_type} - {str(error)}")
            
            # 构造错误响应
            return {
                'error_response': {
                    'success': False,
                    'error': str(error),
                    'error_type': error_type,
                    'request_id': context.request_id,
                    'timestamp': context.timestamp.isoformat()
                }
            }
        
        return None
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        return {
            'error_counts': self.error_counts,
            'total_errors': sum(self.error_counts.values())
        }


class ContextEnrichmentMiddleware(BaseMiddleware):
    """上下文增强中间件"""
    
    def __init__(self, priority: int = 15):
        super().__init__("context_enrichment", priority)
    
    async def process(self, context: MiddlewareContext) -> Optional[Dict[str, Any]]:
        if context.middleware_type == MiddlewareType.PRE_CONTEXT_CREATE:
            # 增强上下文信息
            request_data = context.get('request', {})
            
            enrichment = {
                'request_timestamp': context.timestamp.isoformat(),
                'request_id': context.request_id,
                'client_info': {
                    'user_agent': 'IAOP-System',
                    'version': '1.0.0'
                }
            }
            
            context.update(enrichment)
            return {'context_enrichment': enrichment}
        
        return None


class MetricsCollectorMiddleware(BaseMiddleware):
    """指标收集中间件"""
    
    def __init__(self, priority: int = 5):
        super().__init__("metrics_collector", priority)
        self.metrics_data = {
            'request_count': 0,
            'success_count': 0,
            'error_count': 0,
            'agent_execution_count': {},
            'execution_times': [],
            'placeholder_types': {}
        }
    
    async def process(self, context: MiddlewareContext) -> Optional[Dict[str, Any]]:
        if context.middleware_type == MiddlewareType.PRE_REQUEST:
            self.metrics_data['request_count'] += 1
            
            # 统计占位符类型
            request_data = context.get('request', {})
            if 'task_type' in request_data:
                task_type = request_data['task_type']
                self.metrics_data['placeholder_types'][task_type] = \
                    self.metrics_data['placeholder_types'].get(task_type, 0) + 1
        
        elif context.middleware_type == MiddlewareType.POST_REQUEST:
            success = context.get('success', True)
            if success:
                self.metrics_data['success_count'] += 1
            else:
                self.metrics_data['error_count'] += 1
            
            # 记录执行时间
            execution_time = context.get('execution_time')
            if execution_time:
                self.metrics_data['execution_times'].append(execution_time)
                # 保持最近1000条记录
                if len(self.metrics_data['execution_times']) > 1000:
                    self.metrics_data['execution_times'] = self.metrics_data['execution_times'][-1000:]
        
        elif context.middleware_type == MiddlewareType.POST_AGENT_EXECUTION:
            agent_name = context.get('agent_name')
            if agent_name:
                self.metrics_data['agent_execution_count'][agent_name] = \
                    self.metrics_data['agent_execution_count'].get(agent_name, 0) + 1
        
        return None
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统指标"""
        execution_times = self.metrics_data['execution_times']
        
        return {
            'request_count': self.metrics_data['request_count'],
            'success_count': self.metrics_data['success_count'],
            'error_count': self.metrics_data['error_count'],
            'success_rate': (
                self.metrics_data['success_count'] / self.metrics_data['request_count']
                if self.metrics_data['request_count'] > 0 else 0
            ),
            'agent_execution_count': self.metrics_data['agent_execution_count'],
            'placeholder_types': self.metrics_data['placeholder_types'],
            'execution_time_stats': {
                'count': len(execution_times),
                'average': sum(execution_times) / len(execution_times) if execution_times else 0,
                'min': min(execution_times) if execution_times else 0,
                'max': max(execution_times) if execution_times else 0
            }
        }


class MiddlewareManager:
    """中间件管理器"""
    
    def __init__(self):
        self.middlewares: Dict[MiddlewareType, List[BaseMiddleware]] = {
            mtype: [] for mtype in MiddlewareType
        }
        self._setup_default_middlewares()
    
    def _setup_default_middlewares(self):
        """设置默认中间件"""
        # 性能监控
        perf_middleware = PerformanceMonitoringMiddleware()
        self.register_middleware(MiddlewareType.PRE_REQUEST, perf_middleware)
        self.register_middleware(MiddlewareType.POST_REQUEST, perf_middleware)
        
        # 请求日志
        log_middleware = RequestLoggingMiddleware()
        self.register_middleware(MiddlewareType.PRE_REQUEST, log_middleware)
        
        # 缓存
        cache_middleware = CacheMiddleware()
        self.register_middleware(MiddlewareType.PRE_REQUEST, cache_middleware)
        self.register_middleware(MiddlewareType.POST_REQUEST, cache_middleware)
        
        # 上下文增强
        context_middleware = ContextEnrichmentMiddleware()
        self.register_middleware(MiddlewareType.PRE_CONTEXT_CREATE, context_middleware)
        
        # 指标收集
        metrics_middleware = MetricsCollectorMiddleware()
        self.register_middleware(MiddlewareType.PRE_REQUEST, metrics_middleware)
        self.register_middleware(MiddlewareType.POST_REQUEST, metrics_middleware)
        self.register_middleware(MiddlewareType.POST_AGENT_EXECUTION, metrics_middleware)
        
        # 错误处理
        error_middleware = ErrorHandlingMiddleware()
        self.register_middleware(MiddlewareType.ERROR_HANDLER, error_middleware)
        
        logger.info("默认中间件设置完成")
    
    def register_middleware(self, middleware_type: MiddlewareType, middleware: BaseMiddleware):
        """注册中间件"""
        self.middlewares[middleware_type].append(middleware)
        # 按优先级排序
        self.middlewares[middleware_type].sort(key=lambda m: m.priority)
        logger.info(f"注册中间件: {middleware.name} -> {middleware_type.value}")
    
    def remove_middleware(self, middleware_type: MiddlewareType, middleware_name: str):
        """移除中间件"""
        self.middlewares[middleware_type] = [
            m for m in self.middlewares[middleware_type] if m.name != middleware_name
        ]
        logger.info(f"移除中间件: {middleware_name} <- {middleware_type.value}")
    
    async def execute_middlewares(self, middleware_type: MiddlewareType, 
                                 context_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行指定类型的中间件"""
        import uuid
        
        context = MiddlewareContext(
            request_id=context_data.get('request_id', str(uuid.uuid4())),
            middleware_type=middleware_type,
            timestamp=datetime.utcnow(),
            data=context_data.copy(),
            metadata={}
        )
        
        results = {}
        
        for middleware in self.middlewares[middleware_type]:
            try:
                result = await middleware.execute(context)
                if result:
                    results[middleware.name] = result
            except Exception as e:
                logger.error(f"中间件执行失败: {middleware.name}, 错误: {e}")
                # 错误处理中间件特殊处理
                if middleware_type != MiddlewareType.ERROR_HANDLER:
                    await self.execute_middlewares(
                        MiddlewareType.ERROR_HANDLER, 
                        {'error': e, 'request_id': context.request_id}
                    )
        
        return results
    
    def get_middleware_status(self) -> Dict[str, Any]:
        """获取中间件状态"""
        status = {}
        
        for mtype, middleware_list in self.middlewares.items():
            status[mtype.value] = [m.get_metrics() for m in middleware_list]
        
        return status
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统指标"""
        metrics = {}
        
        for middleware_list in self.middlewares.values():
            for middleware in middleware_list:
                if hasattr(middleware, 'get_system_metrics'):
                    metrics.update(middleware.get_system_metrics())
                elif hasattr(middleware, 'get_cache_stats'):
                    metrics['cache_stats'] = middleware.get_cache_stats()
                elif hasattr(middleware, 'get_error_stats'):
                    metrics['error_stats'] = middleware.get_error_stats()
        
        return metrics


# 全局中间件管理器实例
_global_middleware_manager = None

def get_middleware_manager() -> MiddlewareManager:
    """获取全局中间件管理器"""
    global _global_middleware_manager
    if _global_middleware_manager is None:
        _global_middleware_manager = MiddlewareManager()
    return _global_middleware_manager