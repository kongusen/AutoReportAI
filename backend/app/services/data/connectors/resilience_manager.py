"""
连接韧性管理器
提供断路器、重试机制、连接池监控等功能，提升系统容错能力
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import threading
from collections import defaultdict, deque


class CircuitBreakerState(Enum):
    """断路器状态"""
    CLOSED = "closed"       # 正常状态
    OPEN = "open"           # 开路状态，快速失败
    HALF_OPEN = "half_open" # 半开状态，尝试恢复


@dataclass
class CircuitBreakerConfig:
    """断路器配置"""
    failure_threshold: int = 5          # 失败次数阈值
    recovery_timeout: int = 60          # 恢复尝试超时(秒)
    success_threshold: int = 3          # 半开状态成功次数阈值
    monitor_window: int = 300           # 监控窗口(秒)
    max_request_volume: int = 20        # 最小请求量阈值


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3               # 最大重试次数
    base_delay: float = 1.0             # 基础延迟(秒)
    max_delay: float = 60.0             # 最大延迟(秒)
    exponential_factor: float = 2.0     # 指数退避因子
    jitter: bool = True                 # 是否添加随机抖动


class ConnectionHealth(Enum):
    """连接健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ConnectionMetrics:
    """连接度量指标"""
    connection_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    average_response_time: float = 0.0
    current_health: ConnectionHealth = ConnectionHealth.UNKNOWN
    recent_failures: deque = field(default_factory=lambda: deque(maxlen=100))
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))


class CircuitBreaker:
    """断路器实现"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.lock = threading.Lock()
        self.logger = logging.getLogger(f"{__name__}.CircuitBreaker.{name}")
        
    def call(self, func: Callable, *args, **kwargs):
        """执行函数调用，带断路器保护"""
        if not self._should_allow_request():
            self.logger.warning(f"断路器 {self.name} 处于开路状态，拒绝请求")
            raise CircuitBreakerOpenError(f"Circuit breaker {self.name} is open")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise
    
    async def async_call(self, func: Callable, *args, **kwargs):
        """异步执行函数调用，带断路器保护"""
        if not self._should_allow_request():
            self.logger.warning(f"断路器 {self.name} 处于开路状态，拒绝请求")
            raise CircuitBreakerOpenError(f"Circuit breaker {self.name} is open")
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise
    
    def _should_allow_request(self) -> bool:
        """判断是否应该允许请求"""
        with self.lock:
            if self.state == CircuitBreakerState.CLOSED:
                return True
            
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.success_count = 0
                    self.logger.info(f"断路器 {self.name} 进入半开状态")
                    return True
                return False
            
            # HALF_OPEN state
            return True
    
    def _should_attempt_reset(self) -> bool:
        """判断是否应该尝试重置断路器"""
        if self.last_failure_time is None:
            return True
        
        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.config.recovery_timeout
    
    def _on_success(self):
        """处理成功请求"""
        with self.lock:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    self.logger.info(f"断路器 {self.name} 恢复到关闭状态")
            elif self.state == CircuitBreakerState.CLOSED:
                self.failure_count = 0
    
    def _on_failure(self, exception: Exception):
        """处理失败请求"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.OPEN
                self.logger.warning(f"断路器 {self.name} 在半开状态下失败，重新开路")
            elif (self.state == CircuitBreakerState.CLOSED and 
                  self.failure_count >= self.config.failure_threshold):
                self.state = CircuitBreakerState.OPEN
                self.logger.error(f"断路器 {self.name} 达到失败阈值，开路保护")
    
    def get_state(self) -> Dict[str, Any]:
        """获取断路器状态"""
        with self.lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "last_failure_time": self.last_failure_time,
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "recovery_timeout": self.config.recovery_timeout,
                    "success_threshold": self.config.success_threshold
                }
            }


class RetryManager:
    """重试管理器"""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.RetryManager")
    
    async def execute_with_retry(
        self, 
        func: Callable, 
        *args, 
        retryable_exceptions: tuple = (Exception,),
        **kwargs
    ):
        """执行函数，带重试机制"""
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
                    
            except retryable_exceptions as e:
                last_exception = e
                
                if attempt == self.config.max_attempts - 1:
                    self.logger.error(f"重试 {self.config.max_attempts} 次后仍失败: {e}")
                    break
                
                delay = self._calculate_delay(attempt)
                self.logger.warning(f"第 {attempt + 1} 次尝试失败，{delay:.2f}秒后重试: {e}")
                await asyncio.sleep(delay)
            
            except Exception as e:
                # 非重试异常，直接抛出
                self.logger.error(f"遇到不可重试异常: {e}")
                raise
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """计算重试延迟"""
        delay = self.config.base_delay * (self.config.exponential_factor ** attempt)
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # 添加50%-100%的随机因子
        
        return delay


class ConnectionMonitor:
    """连接监控器"""
    
    def __init__(self):
        self.metrics: Dict[str, ConnectionMetrics] = {}
        self.lock = threading.Lock()
        self.logger = logging.getLogger(f"{__name__}.ConnectionMonitor")
    
    def record_request(self, connection_name: str, success: bool, response_time: float, error: Optional[Exception] = None):
        """记录请求结果"""
        with self.lock:
            if connection_name not in self.metrics:
                self.metrics[connection_name] = ConnectionMetrics(connection_name=connection_name)
            
            metrics = self.metrics[connection_name]
            metrics.total_requests += 1
            
            if success:
                metrics.successful_requests += 1
                metrics.last_success_time = datetime.utcnow()
            else:
                metrics.failed_requests += 1
                metrics.last_failure_time = datetime.utcnow()
                if error:
                    metrics.recent_failures.append({
                        "time": datetime.utcnow(),
                        "error": str(error),
                        "type": type(error).__name__
                    })
            
            metrics.response_times.append(response_time)
            if metrics.response_times:
                metrics.average_response_time = sum(metrics.response_times) / len(metrics.response_times)
            
            # 更新健康状态
            metrics.current_health = self._calculate_health(metrics)
    
    def _calculate_health(self, metrics: ConnectionMetrics) -> ConnectionHealth:
        """计算连接健康状态"""
        if metrics.total_requests == 0:
            return ConnectionHealth.UNKNOWN
        
        success_rate = metrics.successful_requests / metrics.total_requests
        
        # 检查最近的健康状况
        recent_window = 60  # 最近60秒
        recent_time = datetime.utcnow() - timedelta(seconds=recent_window)
        recent_failures = [f for f in metrics.recent_failures if f["time"] > recent_time]
        
        if success_rate >= 0.95 and len(recent_failures) == 0:
            return ConnectionHealth.HEALTHY
        elif success_rate >= 0.8 and len(recent_failures) <= 2:
            return ConnectionHealth.DEGRADED
        else:
            return ConnectionHealth.UNHEALTHY
    
    def get_metrics(self, connection_name: Optional[str] = None) -> Dict[str, Any]:
        """获取连接度量指标"""
        with self.lock:
            if connection_name:
                if connection_name in self.metrics:
                    metrics = self.metrics[connection_name]
                    return {
                        "connection_name": metrics.connection_name,
                        "total_requests": metrics.total_requests,
                        "successful_requests": metrics.successful_requests,
                        "failed_requests": metrics.failed_requests,
                        "success_rate": metrics.successful_requests / metrics.total_requests if metrics.total_requests > 0 else 0,
                        "average_response_time": metrics.average_response_time,
                        "current_health": metrics.current_health.value,
                        "last_success_time": metrics.last_success_time.isoformat() if metrics.last_success_time else None,
                        "last_failure_time": metrics.last_failure_time.isoformat() if metrics.last_failure_time else None,
                        "recent_failures_count": len(metrics.recent_failures)
                    }
                else:
                    return {"error": f"Connection {connection_name} not found"}
            else:
                return {
                    name: self.get_metrics(name)
                    for name in self.metrics.keys()
                }


class ResilienceManager:
    """韧性管理器 - 统一管理断路器、重试、监控"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_manager = RetryManager(RetryConfig())
        self.connection_monitor = ConnectionMonitor()
        self.logger = logging.getLogger(f"{__name__}.ResilienceManager")
    
    def get_circuit_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """获取或创建断路器"""
        if name not in self.circuit_breakers:
            if config is None:
                config = CircuitBreakerConfig()
            self.circuit_breakers[name] = CircuitBreaker(name, config)
        return self.circuit_breakers[name]
    
    @asynccontextmanager
    async def resilient_operation(
        self, 
        operation_name: str,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None
    ):
        """韧性操作上下文管理器"""
        circuit_breaker = self.get_circuit_breaker(operation_name, circuit_breaker_config)
        retry_manager = RetryManager(retry_config) if retry_config else self.retry_manager
        
        start_time = time.time()
        success = False
        error = None
        
        try:
            # 使用断路器保护的重试操作
            async def protected_operation():
                return circuit_breaker
            
            yield await retry_manager.execute_with_retry(protected_operation)
            success = True
            
        except Exception as e:
            error = e
            success = False
            raise
        
        finally:
            response_time = time.time() - start_time
            self.connection_monitor.record_request(operation_name, success, response_time, error)
    
    def get_health_report(self) -> Dict[str, Any]:
        """获取整体健康报告"""
        circuit_breaker_status = {
            name: cb.get_state() 
            for name, cb in self.circuit_breakers.items()
        }
        
        connection_metrics = self.connection_monitor.get_metrics()
        
        # 计算整体健康状态
        overall_health = "healthy"
        unhealthy_connections = []
        
        for name, metrics in connection_metrics.items():
            if isinstance(metrics, dict) and "current_health" in metrics:
                if metrics["current_health"] == "unhealthy":
                    overall_health = "unhealthy"
                    unhealthy_connections.append(name)
                elif metrics["current_health"] == "degraded" and overall_health == "healthy":
                    overall_health = "degraded"
        
        return {
            "overall_health": overall_health,
            "timestamp": datetime.utcnow().isoformat(),
            "circuit_breakers": circuit_breaker_status,
            "connection_metrics": connection_metrics,
            "unhealthy_connections": unhealthy_connections,
            "total_circuit_breakers": len(self.circuit_breakers),
            "open_circuit_breakers": sum(1 for cb in self.circuit_breakers.values() 
                                       if cb.state == CircuitBreakerState.OPEN)
        }


class CircuitBreakerOpenError(Exception):
    """断路器开路异常"""
    pass


# 全局韧性管理器实例
_resilience_manager: Optional[ResilienceManager] = None


def get_resilience_manager() -> ResilienceManager:
    """获取全局韧性管理器"""
    global _resilience_manager
    if _resilience_manager is None:
        _resilience_manager = ResilienceManager()
    return _resilience_manager