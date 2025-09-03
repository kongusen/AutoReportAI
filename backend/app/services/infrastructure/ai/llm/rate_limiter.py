"""
LLM访问速度限制器
基于系统设计规范的完整实现
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class LimiterStatus(str, Enum):
    """限制器状态"""
    HEALTHY = "healthy"
    WARNING = "warning"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class RequestMetrics:
    """请求指标"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    blocked_requests: int = 0
    total_tokens: int = 0
    average_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def block_rate(self) -> float:
        """阻塞率"""
        if self.total_requests == 0:
            return 0.0
        return self.blocked_requests / self.total_requests


@dataclass
class LimiterConfig:
    """限制器配置"""
    max_concurrent_requests: int = 3
    min_interval_seconds: float = 1.0
    request_timeout_seconds: float = 120.0
    enable_rate_limiting: bool = True
    enable_concurrency_limiting: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_concurrent_requests": self.max_concurrent_requests,
            "min_interval_seconds": self.min_interval_seconds,
            "request_timeout_seconds": self.request_timeout_seconds,
            "enable_rate_limiting": self.enable_rate_limiting,
            "enable_concurrency_limiting": self.enable_concurrency_limiting
        }


class LLMRateLimiter:
    """LLM访问速度限制器"""
    
    def __init__(self, config: Optional[LimiterConfig] = None):
        self.config = config or LimiterConfig()
        self.metrics = RequestMetrics()
        self.active_requests = set()
        self.last_request_time = 0.0
        self.request_semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        self.start_time = datetime.utcnow()
        self._lock = asyncio.Lock()
        
        logger.info(f"LLM速度限制器已初始化: {self.config.to_dict()}")
    
    async def acquire(self) -> bool:
        """获取访问许可"""
        if not self.config.enable_rate_limiting and not self.config.enable_concurrency_limiting:
            return True
        
        try:
            # 并发限制
            if self.config.enable_concurrency_limiting:
                # 非阻塞方式检查并发限制
                if self.request_semaphore.locked():
                    async with self._lock:
                        self.metrics.blocked_requests += 1
                    logger.warning("请求被阻塞：并发限制已达上限")
                    return False
                
                await self.request_semaphore.acquire()
            
            # 速率限制
            if self.config.enable_rate_limiting:
                current_time = time.time()
                time_since_last = current_time - self.last_request_time
                
                if time_since_last < self.config.min_interval_seconds:
                    # 需要等待
                    wait_time = self.config.min_interval_seconds - time_since_last
                    logger.debug(f"速率限制：等待 {wait_time:.2f} 秒")
                    await asyncio.sleep(wait_time)
                
                self.last_request_time = time.time()
            
            # 记录活跃请求
            request_id = f"req_{int(time.time() * 1000000)}"
            self.active_requests.add(request_id)
            
            async with self._lock:
                self.metrics.total_requests += 1
                self.metrics.last_request_time = datetime.utcnow()
            
            return True
            
        except Exception as e:
            logger.error(f"获取访问许可时发生错误: {e}")
            if self.config.enable_concurrency_limiting:
                self.request_semaphore.release()
            return False
    
    def release(self, success: bool = True, tokens_used: int = 0, response_time: float = 0.0):
        """释放访问许可"""
        try:
            # 释放信号量
            if self.config.enable_concurrency_limiting:
                self.request_semaphore.release()
            
            # 更新指标
            asyncio.create_task(self._update_metrics(success, tokens_used, response_time))
            
        except Exception as e:
            logger.error(f"释放访问许可时发生错误: {e}")
    
    async def _update_metrics(self, success: bool, tokens_used: int, response_time: float):
        """更新指标"""
        async with self._lock:
            if success:
                self.metrics.successful_requests += 1
            else:
                self.metrics.failed_requests += 1
            
            self.metrics.total_tokens += tokens_used
            
            # 更新平均响应时间
            if response_time > 0:
                total_response_time = (
                    self.metrics.average_response_time * (self.metrics.successful_requests - 1) + response_time
                )
                self.metrics.average_response_time = total_response_time / self.metrics.successful_requests
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        uptime = datetime.utcnow() - self.start_time
        
        return {
            "rate_limiter_config": self.config.to_dict(),
            "current_status": {
                "active_requests": len(self.active_requests),
                "available_slots": self.request_semaphore._value if self.config.enable_concurrency_limiting else -1,
                "last_request_time": self.metrics.last_request_time.isoformat() if self.metrics.last_request_time else None,
                "uptime_seconds": uptime.total_seconds()
            },
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "blocked_requests": self.metrics.blocked_requests,
                "success_rate": self.metrics.success_rate,
                "block_rate": self.metrics.block_rate,
                "total_tokens": self.metrics.total_tokens,
                "average_response_time": self.metrics.average_response_time,
                "requests_per_minute": self._calculate_rpm()
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        status = LimiterStatus.HEALTHY
        issues = []
        
        # 检查阻塞率
        if self.metrics.block_rate > 0.3:  # 阻塞率超过30%
            status = LimiterStatus.WARNING
            issues.append(f"高阻塞率: {self.metrics.block_rate:.2%}")
        
        # 检查失败率
        if self.metrics.success_rate < 0.8 and self.metrics.total_requests > 10:
            status = LimiterStatus.WARNING
            issues.append(f"低成功率: {self.metrics.success_rate:.2%}")
        
        # 检查当前并发
        if self.config.enable_concurrency_limiting and len(self.active_requests) >= self.config.max_concurrent_requests:
            status = LimiterStatus.BUSY
            issues.append("并发请求已达上限")
        
        return {
            "status": status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "issues": issues,
            "metrics_summary": {
                "total_requests": self.metrics.total_requests,
                "success_rate": self.metrics.success_rate,
                "block_rate": self.metrics.block_rate,
                "active_requests": len(self.active_requests)
            }
        }
    
    def reset_statistics(self):
        """重置统计信息"""
        logger.info("重置LLM速度限制器统计信息")
        self.metrics = RequestMetrics()
        self.active_requests.clear()
        self.start_time = datetime.utcnow()
    
    def _calculate_rpm(self) -> float:
        """计算每分钟请求数"""
        if not self.metrics.last_request_time:
            return 0.0
        
        uptime = datetime.utcnow() - self.start_time
        uptime_minutes = uptime.total_seconds() / 60
        
        if uptime_minutes < 0.1:  # 少于6秒，返回0
            return 0.0
        
        return self.metrics.total_requests / uptime_minutes


# 全局限制器实例
_global_rate_limiter: Optional[LLMRateLimiter] = None


def get_llm_rate_limiter(
    max_concurrent_requests: int = 3,
    min_interval_seconds: float = 1.0,
    request_timeout_seconds: float = 120.0
) -> LLMRateLimiter:
    """获取全局LLM速度限制器"""
    global _global_rate_limiter
    
    if _global_rate_limiter is None:
        config = LimiterConfig(
            max_concurrent_requests=max_concurrent_requests,
            min_interval_seconds=min_interval_seconds,
            request_timeout_seconds=request_timeout_seconds
        )
        _global_rate_limiter = LLMRateLimiter(config)
    
    return _global_rate_limiter


def reset_llm_rate_limiter():
    """重置全局限制器"""
    global _global_rate_limiter
    _global_rate_limiter = None
    return {"message": "LLM速度限制器已重置"}


# 装饰器用法
def rate_limited(func):
    """装饰器：为函数添加速率限制"""
    async def wrapper(*args, **kwargs):
        limiter = get_llm_rate_limiter()
        
        if not await limiter.acquire():
            raise Exception("请求被速率限制器阻塞")
        
        start_time = time.time()
        success = False
        tokens_used = 0
        
        try:
            result = await func(*args, **kwargs)
            success = True
            
            # 尝试从结果中提取token信息
            if isinstance(result, dict) and 'usage' in result:
                tokens_used = result['usage'].get('total_tokens', 0)
            
            return result
            
        finally:
            response_time = time.time() - start_time
            limiter.release(success=success, tokens_used=tokens_used, response_time=response_time)
    
    return wrapper