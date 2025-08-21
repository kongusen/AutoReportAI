"""
LLM访问速度限制器

提供LLM API调用的速度限制和串行控制，避免并发请求导致的资源竞争
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime, timedelta
from dataclasses import dataclass
from threading import Lock
from collections import defaultdict
import weakref

logger = logging.getLogger(__name__)


@dataclass
class LLMRequestInfo:
    """LLM请求信息"""
    request_id: str
    task_type: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    
    @property
    def duration_ms(self) -> Optional[float]:
        """请求耗时（毫秒）"""
        if self.end_time is not None:
            return (self.end_time - self.start_time) * 1000
        return None


class LLMRateLimiter:
    """LLM API访问速度限制器"""
    
    def __init__(
        self, 
        max_concurrent_requests: int = 1,  # 最大并发请求数
        min_interval_seconds: float = 1.0,  # 最小请求间隔（秒）
        request_timeout_seconds: float = 120.0,  # 请求超时时间
        enable_detailed_logging: bool = True
    ):
        """
        初始化速度限制器
        
        Args:
            max_concurrent_requests: 最大并发LLM请求数（默认1，即串行）
            min_interval_seconds: 最小请求间隔，秒
            request_timeout_seconds: 单个请求超时时间
            enable_detailed_logging: 是否启用详细日志
        """
        self.max_concurrent_requests = max_concurrent_requests
        self.min_interval_seconds = min_interval_seconds
        self.request_timeout_seconds = request_timeout_seconds
        self.enable_detailed_logging = enable_detailed_logging
        
        # 并发控制
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.request_queue = asyncio.Queue()
        self.active_requests: Dict[str, LLMRequestInfo] = {}
        
        # 请求间隔控制
        self.last_request_time = 0.0
        self.interval_lock = asyncio.Lock()
        
        # 统计信息
        self.request_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'timeout_requests': 0,
            'avg_response_time_ms': 0.0,
            'max_response_time_ms': 0.0,
            'min_response_time_ms': float('inf')
        }
        
        # 任务类型统计
        self.task_type_stats = defaultdict(lambda: {
            'count': 0,
            'success_count': 0,
            'avg_time_ms': 0.0
        })
        
        logger.info(
            f"LLM速度限制器初始化: max_concurrent={max_concurrent_requests}, "
            f"min_interval={min_interval_seconds}s, timeout={request_timeout_seconds}s"
        )
    
    async def execute_with_rate_limit(
        self,
        request_id: str,
        task_type: str,
        llm_function: Callable[[], Awaitable[Any]],
        **kwargs
    ) -> Any:
        """
        在速度限制下执行LLM请求
        
        Args:
            request_id: 请求唯一标识
            task_type: 任务类型（用于统计）
            llm_function: 要执行的LLM函数
            **kwargs: 额外参数
            
        Returns:
            LLM函数的返回值
            
        Raises:
            TimeoutError: 请求超时
            Exception: LLM函数抛出的异常
        """
        request_info = LLMRequestInfo(
            request_id=request_id,
            task_type=task_type,
            start_time=time.time()
        )
        
        if self.enable_detailed_logging:
            logger.info(f"LLM请求开始: {request_id} ({task_type})")
        
        try:
            # 1. 等待并发控制信号量
            async with self.semaphore:
                # 2. 等待请求间隔
                await self._wait_for_interval()
                
                # 3. 记录活跃请求
                self.active_requests[request_id] = request_info
                
                # 4. 执行实际的LLM请求
                result = await asyncio.wait_for(
                    llm_function(),
                    timeout=self.request_timeout_seconds
                )
                
                # 5. 记录成功
                request_info.end_time = time.time()
                request_info.success = True
                
                self._update_statistics(request_info)
                
                if self.enable_detailed_logging:
                    logger.info(
                        f"LLM请求成功: {request_id} "
                        f"(耗时: {request_info.duration_ms:.1f}ms)"
                    )
                
                return result
                
        except asyncio.TimeoutError:
            request_info.end_time = time.time()
            request_info.error = "请求超时"
            self.request_stats['timeout_requests'] += 1
            
            logger.warning(f"LLM请求超时: {request_id} (超时时间: {self.request_timeout_seconds}s)")
            raise TimeoutError(f"LLM请求超时: {request_id}")
            
        except Exception as e:
            request_info.end_time = time.time()
            request_info.error = str(e)
            
            self._update_statistics(request_info)
            
            logger.error(f"LLM请求失败: {request_id}, 错误: {e}")
            raise
            
        finally:
            # 清理活跃请求记录
            self.active_requests.pop(request_id, None)
    
    async def _wait_for_interval(self):
        """等待请求间隔"""
        async with self.interval_lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            if time_since_last < self.min_interval_seconds:
                wait_time = self.min_interval_seconds - time_since_last
                if self.enable_detailed_logging:
                    logger.debug(f"等待请求间隔: {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
            
            self.last_request_time = time.time()
    
    def _update_statistics(self, request_info: LLMRequestInfo):
        """更新统计信息"""
        self.request_stats['total_requests'] += 1
        
        if request_info.success:
            self.request_stats['successful_requests'] += 1
        else:
            self.request_stats['failed_requests'] += 1
        
        # 更新响应时间统计
        if request_info.duration_ms is not None:
            duration = request_info.duration_ms
            
            # 更新全局统计
            total = self.request_stats['total_requests']
            current_avg = self.request_stats['avg_response_time_ms']
            self.request_stats['avg_response_time_ms'] = (
                (current_avg * (total - 1) + duration) / total
            )
            
            self.request_stats['max_response_time_ms'] = max(
                self.request_stats['max_response_time_ms'], duration
            )
            self.request_stats['min_response_time_ms'] = min(
                self.request_stats['min_response_time_ms'], duration
            )
            
            # 更新任务类型统计
            task_stats = self.task_type_stats[request_info.task_type]
            task_stats['count'] += 1
            if request_info.success:
                task_stats['success_count'] += 1
            
            # 更新任务类型平均时间
            count = task_stats['count']
            current_task_avg = task_stats['avg_time_ms']
            task_stats['avg_time_ms'] = (
                (current_task_avg * (count - 1) + duration) / count
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        # 修正无限大的最小响应时间
        min_time = self.request_stats['min_response_time_ms']
        if min_time == float('inf'):
            min_time = 0.0
        
        return {
            'rate_limiter_config': {
                'max_concurrent_requests': self.max_concurrent_requests,
                'min_interval_seconds': self.min_interval_seconds,
                'request_timeout_seconds': self.request_timeout_seconds
            },
            'current_status': {
                'active_requests_count': len(self.active_requests),
                'queue_size': self.request_queue.qsize(),
                'semaphore_available': self.semaphore._value
            },
            'overall_stats': {
                **self.request_stats,
                'min_response_time_ms': min_time,
                'success_rate': (
                    self.request_stats['successful_requests'] / 
                    max(self.request_stats['total_requests'], 1) * 100
                )
            },
            'task_type_stats': dict(self.task_type_stats),
            'active_requests': [
                {
                    'request_id': req.request_id,
                    'task_type': req.task_type,
                    'duration_so_far_ms': (time.time() - req.start_time) * 1000
                }
                for req in self.active_requests.values()
            ]
        }
    
    def reset_statistics(self):
        """重置统计信息"""
        self.request_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'timeout_requests': 0,
            'avg_response_time_ms': 0.0,
            'max_response_time_ms': 0.0,
            'min_response_time_ms': float('inf')
        }
        self.task_type_stats.clear()
        logger.info("LLM速度限制器统计信息已重置")
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        active_count = len(self.active_requests)
        available_slots = self.semaphore._value
        
        status = "healthy"
        issues = []
        
        # 检查是否有超时的请求
        current_time = time.time()
        for req in self.active_requests.values():
            if current_time - req.start_time > self.request_timeout_seconds:
                issues.append(f"请求 {req.request_id} 可能超时")
        
        # 检查并发数是否达到上限
        if available_slots == 0:
            issues.append("已达到最大并发请求数")
            status = "busy"
        
        if issues:
            status = "warning" if status != "busy" else "busy"
        
        return {
            'status': status,
            'active_requests': active_count,
            'available_slots': available_slots,
            'issues': issues,
            'uptime_seconds': time.time() - getattr(self, '_start_time', time.time())
        }


# 全局LLM速度限制器实例
_llm_rate_limiter: Optional[LLMRateLimiter] = None
_limiter_lock = Lock()


def get_llm_rate_limiter(
    max_concurrent_requests: int = 1,
    min_interval_seconds: float = 1.0,
    request_timeout_seconds: float = 120.0,
    enable_detailed_logging: bool = True
) -> LLMRateLimiter:
    """
    获取全局LLM速度限制器实例
    
    Args:
        max_concurrent_requests: 最大并发请求数
        min_interval_seconds: 最小请求间隔
        request_timeout_seconds: 请求超时时间
        enable_detailed_logging: 是否启用详细日志
        
    Returns:
        LLMRateLimiter实例
    """
    global _llm_rate_limiter
    
    with _limiter_lock:
        if _llm_rate_limiter is None:
            _llm_rate_limiter = LLMRateLimiter(
                max_concurrent_requests=max_concurrent_requests,
                min_interval_seconds=min_interval_seconds,
                request_timeout_seconds=request_timeout_seconds,
                enable_detailed_logging=enable_detailed_logging
            )
            _llm_rate_limiter._start_time = time.time()
        
        return _llm_rate_limiter


def reset_llm_rate_limiter():
    """重置全局LLM速度限制器"""
    global _llm_rate_limiter
    
    with _limiter_lock:
        _llm_rate_limiter = None