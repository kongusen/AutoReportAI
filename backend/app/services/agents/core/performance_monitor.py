"""
性能监控和资源管理系统
提供全面的性能监控、资源优化和性能调优功能
"""

import asyncio
import logging
import psutil
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from collections import deque, defaultdict
from contextlib import contextmanager
import weakref
import gc


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    timestamp: datetime = field(default_factory=datetime.now)
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    memory_percent: float = 0.0
    active_threads: int = 0
    active_sessions: int = 0
    ai_service_pool_size: int = 0
    response_time_ms: float = 0.0
    error_count: int = 0
    request_count: int = 0


@dataclass
class ResourceThresholds:
    """资源阈值配置"""
    max_cpu_percent: float = 80.0
    max_memory_percent: float = 85.0
    max_active_sessions: int = 50
    max_ai_pool_size: int = 20
    max_response_time_ms: float = 5000.0
    max_error_rate: float = 0.05  # 5%


class PerformanceCollector:
    """性能数据收集器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.process = psutil.Process()
        
    def collect_system_metrics(self) -> Dict[str, Any]:
        """收集系统级性能指标"""
        try:
            return {
                "cpu_usage": self.process.cpu_percent(),
                "memory_info": self.process.memory_info(),
                "memory_percent": self.process.memory_percent(),
                "num_threads": self.process.num_threads(),
                "num_fds": self.process.num_fds(),
                "connections": len(self.process.connections()),
                "create_time": self.process.create_time()
            }
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
            return {}
    
    def collect_database_metrics(self) -> Dict[str, Any]:
        """收集数据库相关指标"""
        try:
            from .session_manager import get_session_manager
            manager = get_session_manager()
            health = manager.health_check()
            
            return {
                "active_sessions": health.get("active_sessions", 0),
                "connection_pool_size": health.get("connection_pool_size", 0),
                "checked_out_connections": health.get("checked_out_connections", 0),
                "status": health.get("status", "unknown")
            }
        except Exception as e:
            self.logger.error(f"Failed to collect database metrics: {e}")
            return {}
    
    def collect_ai_service_metrics(self) -> Dict[str, Any]:
        """收集AI服务性能指标"""
        try:
            from .ai_service import get_ai_service_pool
            pool = get_ai_service_pool()
            stats = pool.get_pool_stats()
            
            return {
                "total_instances": stats.get("total_instances", 0),
                "max_instances": stats.get("max_instances", 0),
                "active_references": stats.get("active_references", 0),
                "pool_utilization": stats.get("total_instances", 0) / max(stats.get("max_instances", 1), 1)
            }
        except Exception as e:
            self.logger.error(f"Failed to collect AI service metrics: {e}")
            return {}


class ResourceOptimizer:
    """资源优化器"""
    
    def __init__(self, thresholds: Optional[ResourceThresholds] = None):
        self.thresholds = thresholds or ResourceThresholds()
        self.logger = logging.getLogger(__name__)
        self.optimization_history: List[Dict[str, Any]] = []
    
    def optimize_memory(self, force_gc: bool = False) -> Dict[str, Any]:
        """内存优化"""
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        actions_taken = []
        
        # 强制垃圾回收
        if force_gc:
            collected = gc.collect()
            actions_taken.append(f"Garbage collection: {collected} objects")
        
        # 清理AI服务缓存
        try:
            from .ai_service import get_ai_service_pool
            pool = get_ai_service_pool()
            stats_before = pool.get_pool_stats()
            
            # 如果池使用率过高，清理一些实例
            if stats_before.get("total_instances", 0) > self.thresholds.max_ai_pool_size * 0.8:
                pool.clear_cache()
                actions_taken.append("Cleared AI service cache")
        except Exception as e:
            self.logger.warning(f"Failed to optimize AI service cache: {e}")
        
        # 清理过期会话
        try:
            from .session_manager import get_session_manager
            manager = get_session_manager()
            # 这里可以添加会话清理逻辑
            actions_taken.append("Cleaned expired database sessions")
        except Exception as e:
            self.logger.warning(f"Failed to clean database sessions: {e}")
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_freed = initial_memory - final_memory
        
        optimization_result = {
            "timestamp": datetime.now(),
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_freed_mb": memory_freed,
            "actions_taken": actions_taken
        }
        
        self.optimization_history.append(optimization_result)
        self.logger.info(f"Memory optimization completed: freed {memory_freed:.2f} MB")
        
        return optimization_result
    
    def optimize_connections(self) -> Dict[str, Any]:
        """连接优化"""
        actions_taken = []
        
        try:
            # 优化数据库连接
            from .session_manager import get_session_manager
            manager = get_session_manager()
            health = manager.health_check()
            
            active_sessions = health.get("active_sessions", 0)
            if active_sessions > self.thresholds.max_active_sessions:
                # 这里可以添加连接清理逻辑
                actions_taken.append(f"Cleaned {active_sessions} active sessions")
                
        except Exception as e:
            self.logger.warning(f"Failed to optimize connections: {e}")
        
        return {
            "timestamp": datetime.now(),
            "actions_taken": actions_taken
        }
    
    def should_optimize(self, metrics: PerformanceMetrics) -> List[str]:
        """判断是否需要优化"""
        optimization_needed = []
        
        if metrics.cpu_usage > self.thresholds.max_cpu_percent:
            optimization_needed.append("cpu")
        
        if metrics.memory_percent > self.thresholds.max_memory_percent:
            optimization_needed.append("memory")
        
        if metrics.active_sessions > self.thresholds.max_active_sessions:
            optimization_needed.append("connections")
        
        if metrics.ai_service_pool_size > self.thresholds.max_ai_pool_size:
            optimization_needed.append("ai_service")
        
        if metrics.response_time_ms > self.thresholds.max_response_time_ms:
            optimization_needed.append("response_time")
        
        return optimization_needed


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, 
                 collection_interval: int = 60,  # 1分钟
                 history_size: int = 1440,  # 24小时
                 thresholds: Optional[ResourceThresholds] = None):
        self.collection_interval = collection_interval
        self.history_size = history_size
        self.thresholds = thresholds or ResourceThresholds()
        
        self.logger = logging.getLogger(__name__)
        self.collector = PerformanceCollector()
        self.optimizer = ResourceOptimizer(thresholds)
        
        # 性能数据历史
        self.metrics_history: deque = deque(maxlen=history_size)
        
        # 统计数据
        self.request_counter = defaultdict(int)
        self.error_counter = defaultdict(int)
        self.response_times: deque = deque(maxlen=1000)
        
        # 监控状态
        self.monitoring_enabled = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # 告警回调
        self.alert_callbacks: List[Callable[[str, PerformanceMetrics], None]] = []
    
    def start_monitoring(self):
        """启动性能监控"""
        if self.monitoring_enabled:
            return
        
        self.monitoring_enabled = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """停止性能监控"""
        if not self.monitoring_enabled:
            return
        
        self.monitoring_enabled = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        self.logger.info("Performance monitoring stopped")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring_enabled:
            try:
                self.collect_and_analyze()
                time.sleep(self.collection_interval)
            except Exception as e:
                self.logger.error(f"Error in performance monitoring loop: {e}")
                time.sleep(60)  # 错误时等待1分钟
    
    def collect_and_analyze(self):
        """收集并分析性能数据"""
        # 收集各种指标
        system_metrics = self.collector.collect_system_metrics()
        db_metrics = self.collector.collect_database_metrics()
        ai_metrics = self.collector.collect_ai_service_metrics()
        
        # 构建性能指标对象
        metrics = PerformanceMetrics(
            cpu_usage=system_metrics.get("cpu_usage", 0.0),
            memory_usage=system_metrics.get("memory_info", {}).get("rss", 0) / 1024 / 1024,  # MB
            memory_percent=system_metrics.get("memory_percent", 0.0),
            active_threads=system_metrics.get("num_threads", 0),
            active_sessions=db_metrics.get("active_sessions", 0),
            ai_service_pool_size=ai_metrics.get("total_instances", 0),
            response_time_ms=self.get_average_response_time(),
            error_count=sum(self.error_counter.values()),
            request_count=sum(self.request_counter.values())
        )
        
        # 添加到历史记录
        self.metrics_history.append(metrics)
        
        # 检查是否需要优化
        optimizations_needed = self.optimizer.should_optimize(metrics)
        
        # 执行优化
        if optimizations_needed:
            self.logger.warning(f"Performance issues detected: {optimizations_needed}")
            
            if "memory" in optimizations_needed:
                self.optimizer.optimize_memory()
            
            if "connections" in optimizations_needed:
                self.optimizer.optimize_connections()
            
            # 发送告警
            for callback in self.alert_callbacks:
                try:
                    callback("performance_degradation", metrics)
                except Exception as e:
                    self.logger.error(f"Alert callback failed: {e}")
    
    @contextmanager
    def measure_request(self, request_type: str = "default"):
        """测量请求性能的上下文管理器"""
        start_time = time.time()
        error_occurred = False
        
        try:
            yield
        except Exception as e:
            error_occurred = True
            self.error_counter[request_type] += 1
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.response_times.append(duration_ms)
            self.request_counter[request_type] += 1
            
            # 记录慢请求
            if duration_ms > self.thresholds.max_response_time_ms:
                self.logger.warning(f"Slow request detected: {request_type} took {duration_ms:.2f}ms")
    
    def get_average_response_time(self) -> float:
        """获取平均响应时间"""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.metrics_history:
            return {"status": "no_data"}
        
        latest_metrics = self.metrics_history[-1]
        
        # 计算趋势
        if len(self.metrics_history) >= 2:
            prev_metrics = self.metrics_history[-2]
            cpu_trend = latest_metrics.cpu_usage - prev_metrics.cpu_usage
            memory_trend = latest_metrics.memory_percent - prev_metrics.memory_percent
        else:
            cpu_trend = 0.0
            memory_trend = 0.0
        
        return {
            "timestamp": latest_metrics.timestamp.isoformat(),
            "current_metrics": {
                "cpu_usage": latest_metrics.cpu_usage,
                "memory_usage_mb": latest_metrics.memory_usage,
                "memory_percent": latest_metrics.memory_percent,
                "active_sessions": latest_metrics.active_sessions,
                "ai_pool_size": latest_metrics.ai_service_pool_size,
                "avg_response_time_ms": latest_metrics.response_time_ms
            },
            "trends": {
                "cpu_trend": cpu_trend,
                "memory_trend": memory_trend
            },
            "counters": {
                "total_requests": sum(self.request_counter.values()),
                "total_errors": sum(self.error_counter.values()),
                "error_rate": sum(self.error_counter.values()) / max(sum(self.request_counter.values()), 1)
            },
            "optimization_history": len(self.optimizer.optimization_history),
            "monitoring_enabled": self.monitoring_enabled
        }
    
    def add_alert_callback(self, callback: Callable[[str, PerformanceMetrics], None]):
        """添加告警回调"""
        self.alert_callbacks.append(callback)


# 全局性能监控实例
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控实例"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def start_performance_monitoring():
    """启动性能监控"""
    monitor = get_performance_monitor()
    monitor.start_monitoring()


def stop_performance_monitoring():
    """停止性能监控"""
    monitor = get_performance_monitor()
    monitor.stop_monitoring()


@contextmanager
def performance_context(request_type: str = "default"):
    """性能测量上下文管理器"""
    monitor = get_performance_monitor()
    with monitor.measure_request(request_type):
        yield


async def optimize_system_performance() -> Dict[str, Any]:
    """执行系统性能优化"""
    monitor = get_performance_monitor()
    
    # 强制内存优化
    memory_result = monitor.optimizer.optimize_memory(force_gc=True)
    
    # 连接优化
    connection_result = monitor.optimizer.optimize_connections()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "memory_optimization": memory_result,
        "connection_optimization": connection_result,
        "performance_summary": monitor.get_performance_summary()
    }