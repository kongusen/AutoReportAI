"""
Agent健康监控系统
提供全面的健康检查、监控和自愈机制
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Set
from collections import defaultdict
import weakref

from .ai_service import get_ai_service_pool
from .session_manager import get_session_manager


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ComponentType(Enum):
    """组件类型枚举"""
    AGENT = "agent"
    AI_SERVICE = "ai_service"
    DATABASE = "database"
    CACHE = "cache"
    EXTERNAL_API = "external_api"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    component_id: str
    component_type: ComponentType
    status: HealthStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0
    error: Optional[Exception] = None


@dataclass
class HealthMetrics:
    """健康指标"""
    total_checks: int = 0
    successful_checks: int = 0
    failed_checks: int = 0
    average_response_time: float = 0.0
    last_check_time: Optional[datetime] = None
    uptime_percentage: float = 100.0


class HealthChecker:
    """健康检查器基类"""
    
    def __init__(self, check_id: str, component_type: ComponentType):
        self.check_id = check_id
        self.component_type = component_type
        self.logger = logging.getLogger(__name__)
    
    async def check(self) -> HealthCheckResult:
        """执行健康检查"""
        start_time = datetime.now()
        
        try:
            result = await self._perform_check()
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            return HealthCheckResult(
                component_id=self.check_id,
                component_type=self.component_type,
                status=result.get("status", HealthStatus.UNKNOWN),
                message=result.get("message", ""),
                details=result.get("details", {}),
                duration_ms=duration
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            return HealthCheckResult(
                component_id=self.check_id,
                component_type=self.component_type,
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {str(e)}",
                duration_ms=duration,
                error=e
            )
    
    async def _perform_check(self) -> Dict[str, Any]:
        """子类需要实现的具体检查逻辑"""
        raise NotImplementedError


class DatabaseHealthChecker(HealthChecker):
    """数据库健康检查器"""
    
    def __init__(self):
        super().__init__("database", ComponentType.DATABASE)
    
    async def _perform_check(self) -> Dict[str, Any]:
        """检查数据库连接和性能"""
        session_manager = get_session_manager()
        health_info = session_manager.health_check()
        
        if health_info.get("status") == "healthy":
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Database connection is healthy",
                "details": health_info
            }
        else:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Database issue: {health_info.get('error', 'Unknown')}",
                "details": health_info
            }


class AIServiceHealthChecker(HealthChecker):
    """AI服务健康检查器"""
    
    def __init__(self):
        super().__init__("ai_service", ComponentType.AI_SERVICE)
    
    async def _perform_check(self) -> Dict[str, Any]:
        """检查AI服务连接池状态"""
        pool = get_ai_service_pool()
        stats = pool.get_pool_stats()
        
        total_instances = stats.get("total_instances", 0)
        max_instances = stats.get("max_instances", 10)
        
        # 根据使用率判断健康状态
        usage_ratio = total_instances / max_instances if max_instances > 0 else 0
        
        if usage_ratio < 0.7:
            status = HealthStatus.HEALTHY
            message = "AI service pool is healthy"
        elif usage_ratio < 0.9:
            status = HealthStatus.DEGRADED
            message = "AI service pool is under moderate load"
        else:
            status = HealthStatus.UNHEALTHY
            message = "AI service pool is heavily loaded"
        
        return {
            "status": status,
            "message": message,
            "details": stats
        }


class AgentHealthChecker(HealthChecker):
    """Agent健康检查器"""
    
    def __init__(self, agent_ref: weakref.ref):
        self.agent_ref = agent_ref
        agent = agent_ref()
        agent_id = agent.agent_id if agent else "unknown"
        super().__init__(f"agent_{agent_id}", ComponentType.AGENT)
    
    async def _perform_check(self) -> Dict[str, Any]:
        """检查Agent健康状态"""
        agent = self.agent_ref()
        
        if agent is None:
            return {
                "status": HealthStatus.CRITICAL,
                "message": "Agent instance has been garbage collected",
                "details": {}
            }
        
        # 检查Agent是否有健康检查方法
        if hasattr(agent, 'health_check'):
            try:
                health_result = await agent.health_check()
                
                if health_result.get("healthy", False):
                    return {
                        "status": HealthStatus.HEALTHY,
                        "message": "Agent is healthy",
                        "details": health_result
                    }
                else:
                    return {
                        "status": HealthStatus.DEGRADED,
                        "message": "Agent reported degraded status",
                        "details": health_result
                    }
                    
            except Exception as e:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": f"Agent health check failed: {str(e)}",
                    "details": {"error": str(e)}
                }
        else:
            return {
                "status": HealthStatus.UNKNOWN,
                "message": "Agent does not support health checking",
                "details": {}
            }


class HealthMonitor:
    """健康监控管理器"""
    
    def __init__(self, check_interval: int = 300):  # 5分钟
        self.check_interval = check_interval
        self.logger = logging.getLogger(__name__)
        
        # 健康检查器注册表
        self.checkers: Dict[str, HealthChecker] = {}
        
        # 健康历史记录
        self.health_history: Dict[str, List[HealthCheckResult]] = defaultdict(list)
        
        # 健康指标
        self.metrics: Dict[str, HealthMetrics] = defaultdict(HealthMetrics)
        
        # 监控状态
        self.monitoring_enabled = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        # 告警回调
        self.alert_callbacks: List[Callable[[HealthCheckResult], None]] = []
        
        # 注册默认检查器
        self._register_default_checkers()
    
    def _register_default_checkers(self):
        """注册默认的健康检查器"""
        self.register_checker(DatabaseHealthChecker())
        self.register_checker(AIServiceHealthChecker())
    
    def register_checker(self, checker: HealthChecker):
        """注册健康检查器"""
        self.checkers[checker.check_id] = checker
        self.logger.info(f"Registered health checker: {checker.check_id}")
    
    def register_agent_checker(self, agent):
        """注册Agent健康检查器"""
        agent_ref = weakref.ref(agent)
        checker = AgentHealthChecker(agent_ref)
        self.register_checker(checker)
    
    def add_alert_callback(self, callback: Callable[[HealthCheckResult], None]):
        """添加告警回调"""
        self.alert_callbacks.append(callback)
    
    async def check_component(self, component_id: str) -> Optional[HealthCheckResult]:
        """检查特定组件的健康状态"""
        if component_id not in self.checkers:
            return None
        
        checker = self.checkers[component_id]
        result = await checker.check()
        
        # 更新历史记录
        self.health_history[component_id].append(result)
        
        # 限制历史记录长度
        if len(self.health_history[component_id]) > 100:
            self.health_history[component_id] = self.health_history[component_id][-100:]
        
        # 更新指标
        self._update_metrics(component_id, result)
        
        # 触发告警
        if result.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
            for callback in self.alert_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    self.logger.error(f"Alert callback failed: {e}")
        
        return result
    
    def _update_metrics(self, component_id: str, result: HealthCheckResult):
        """更新健康指标"""
        metrics = self.metrics[component_id]
        metrics.total_checks += 1
        metrics.last_check_time = result.timestamp
        
        if result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
            metrics.successful_checks += 1
        else:
            metrics.failed_checks += 1
        
        # 计算平均响应时间
        if metrics.total_checks == 1:
            metrics.average_response_time = result.duration_ms
        else:
            metrics.average_response_time = (
                (metrics.average_response_time * (metrics.total_checks - 1) + result.duration_ms) / 
                metrics.total_checks
            )
        
        # 计算在线率
        metrics.uptime_percentage = (
            (metrics.successful_checks / metrics.total_checks) * 100 
            if metrics.total_checks > 0 else 100.0
        )
    
    async def check_all_components(self) -> Dict[str, HealthCheckResult]:
        """检查所有组件的健康状态"""
        results = {}
        
        # 并发执行所有健康检查
        tasks = [
            self.check_component(component_id) 
            for component_id in self.checkers.keys()
        ]
        
        completed_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, component_id in enumerate(self.checkers.keys()):
            result = completed_results[i]
            if isinstance(result, Exception):
                results[component_id] = HealthCheckResult(
                    component_id=component_id,
                    component_type=self.checkers[component_id].component_type,
                    status=HealthStatus.CRITICAL,
                    message=f"Health check exception: {str(result)}",
                    error=result
                )
            else:
                results[component_id] = result
        
        return results
    
    async def start_monitoring(self):
        """启动持续监控"""
        if self.monitoring_enabled:
            return
        
        self.monitoring_enabled = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        self.logger.info("Health monitoring started")
    
    async def stop_monitoring(self):
        """停止持续监控"""
        if not self.monitoring_enabled:
            return
        
        self.monitoring_enabled = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Health monitoring stopped")
    
    async def _monitor_loop(self):
        """监控循环"""
        while self.monitoring_enabled:
            try:
                await self.check_all_components()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(60)  # 错误时等待1分钟再重试
    
    def get_system_health_summary(self) -> Dict[str, Any]:
        """获取系统健康状态摘要"""
        component_statuses = {}
        overall_status = HealthStatus.HEALTHY
        
        for component_id in self.checkers.keys():
            history = self.health_history.get(component_id, [])
            if history:
                latest_result = history[-1]
                component_statuses[component_id] = {
                    "status": latest_result.status.value,
                    "message": latest_result.message,
                    "last_check": latest_result.timestamp.isoformat(),
                    "duration_ms": latest_result.duration_ms
                }
                
                # 确定整体状态
                if latest_result.status == HealthStatus.CRITICAL:
                    overall_status = HealthStatus.CRITICAL
                elif latest_result.status == HealthStatus.UNHEALTHY and overall_status != HealthStatus.CRITICAL:
                    overall_status = HealthStatus.UNHEALTHY
                elif latest_result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
            else:
                component_statuses[component_id] = {
                    "status": HealthStatus.UNKNOWN.value,
                    "message": "No health checks performed",
                    "last_check": None,
                    "duration_ms": 0.0
                }
        
        return {
            "overall_status": overall_status.value,
            "monitoring_enabled": self.monitoring_enabled,
            "check_interval": self.check_interval,
            "total_components": len(self.checkers),
            "components": component_statuses,
            "metrics": {
                component_id: {
                    "total_checks": metrics.total_checks,
                    "successful_checks": metrics.successful_checks,
                    "failed_checks": metrics.failed_checks,
                    "uptime_percentage": round(metrics.uptime_percentage, 2),
                    "average_response_time": round(metrics.average_response_time, 2)
                }
                for component_id, metrics in self.metrics.items()
            }
        }


# 全局健康监控实例
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """获取全局健康监控实例"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor


async def perform_system_health_check() -> Dict[str, Any]:
    """执行系统健康检查"""
    monitor = get_health_monitor()
    await monitor.check_all_components()
    return monitor.get_system_health_summary()