"""
AI服务连接池
管理多个AI服务实例的连接池
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """服务状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceInstance:
    """服务实例"""
    service_id: str
    service_type: str
    endpoint: str
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_health_check: Optional[datetime] = None
    response_time: float = 0.0
    error_count: int = 0
    success_count: int = 0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        total = self.error_count + self.success_count
        if total == 0:
            return 0.0
        return self.success_count / total
    
    @property
    def is_healthy(self) -> bool:
        """是否健康"""
        return self.status == ServiceStatus.HEALTHY
    
    def update_health(self, is_healthy: bool, response_time: float = 0.0):
        """更新健康状态"""
        self.last_health_check = datetime.utcnow()
        self.response_time = response_time
        
        if is_healthy:
            self.success_count += 1
            if self.error_count > 0:
                self.error_count = max(0, self.error_count - 1)  # 逐渐恢复
            
            if self.success_rate >= 0.9:
                self.status = ServiceStatus.HEALTHY
            elif self.success_rate >= 0.7:
                self.status = ServiceStatus.DEGRADED
            else:
                self.status = ServiceStatus.UNHEALTHY
        else:
            self.error_count += 1
            if self.success_rate < 0.5:
                self.status = ServiceStatus.UNHEALTHY
            else:
                self.status = ServiceStatus.DEGRADED
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "service_id": self.service_id,
            "service_type": self.service_type,
            "endpoint": self.endpoint,
            "status": self.status.value,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "response_time": self.response_time,
            "error_count": self.error_count,
            "success_count": self.success_count,
            "success_rate": self.success_rate,
            "created_at": self.created_at.isoformat(),
            "is_healthy": self.is_healthy
        }


class AIServicePool:
    """AI服务连接池"""
    
    def __init__(self, max_instances: int = 10):
        self.max_instances = max_instances
        self.services: Dict[str, ServiceInstance] = {}
        self.active_references: Set[str] = set()
        self._lock = asyncio.Lock()
        self.health_check_interval = 300  # 5分钟
        self.health_check_task: Optional[asyncio.Task] = None
        self.created_at = datetime.utcnow()
        
        # 启动健康检查任务
        self._start_health_check()
    
    def _start_health_check(self):
        """启动健康检查任务"""
        try:
            self.health_check_task = asyncio.create_task(self._periodic_health_check())
        except RuntimeError:
            # 没有事件循环时跳过
            pass
    
    async def _periodic_health_check(self):
        """定期健康检查"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self.health_check_all()
            except Exception as e:
                logger.error(f"定期健康检查失败: {e}")
    
    async def register_service(self, service_id: str, service_type: str, endpoint: str) -> bool:
        """注册服务实例"""
        async with self._lock:
            if len(self.services) >= self.max_instances:
                logger.warning(f"服务池已满，无法注册新服务: {service_id}")
                return False
            
            if service_id in self.services:
                logger.warning(f"服务已存在: {service_id}")
                return False
            
            instance = ServiceInstance(
                service_id=service_id,
                service_type=service_type,
                endpoint=endpoint
            )
            
            self.services[service_id] = instance
            logger.info(f"服务注册成功: {service_id} ({service_type})")
            
            # 立即进行健康检查
            await self._check_service_health(instance)
            
            return True
    
    async def unregister_service(self, service_id: str) -> bool:
        """注销服务实例"""
        async with self._lock:
            if service_id not in self.services:
                logger.warning(f"服务不存在: {service_id}")
                return False
            
            # 移除活跃引用
            self.active_references.discard(service_id)
            del self.services[service_id]
            
            logger.info(f"服务注销成功: {service_id}")
            return True
    
    def get_service(self, service_id: Optional[str] = None) -> Optional[ServiceInstance]:
        """获取服务实例"""
        if service_id:
            instance = self.services.get(service_id)
            if instance:
                self.active_references.add(service_id)
                return instance
            return None
        
        # 自动选择最佳服务实例
        healthy_services = [
            service for service in self.services.values()
            if service.is_healthy
        ]
        
        if not healthy_services:
            # 没有健康服务，选择状态最好的
            if self.services:
                best_service = min(
                    self.services.values(),
                    key=lambda s: (s.status.value, s.response_time, s.error_count)
                )
                self.active_references.add(best_service.service_id)
                return best_service
            return None
        
        # 选择响应时间最快的健康服务
        best_service = min(healthy_services, key=lambda s: s.response_time)
        self.active_references.add(best_service.service_id)
        return best_service
    
    def get_all_services(self) -> List[Dict[str, Any]]:
        """获取所有服务实例信息"""
        return [service.to_dict() for service in self.services.values()]
    
    def get_healthy_services(self) -> List[Dict[str, Any]]:
        """获取健康的服务实例"""
        return [
            service.to_dict() for service in self.services.values()
            if service.is_healthy
        ]
    
    async def health_check_all(self) -> Dict[str, Any]:
        """对所有服务进行健康检查"""
        results = {}
        
        for service in self.services.values():
            result = await self._check_service_health(service)
            results[service.service_id] = result
        
        return results
    
    async def _check_service_health(self, service: ServiceInstance) -> Dict[str, Any]:
        """检查单个服务健康状态"""
        start_time = time.time()
        
        try:
            # 这里应该实现实际的健康检查逻辑
            # 例如发送HTTP请求到健康检查端点
            # 现在使用模拟实现
            await asyncio.sleep(0.1)  # 模拟网络延迟
            
            response_time = time.time() - start_time
            service.update_health(True, response_time)
            
            return {
                "service_id": service.service_id,
                "healthy": True,
                "response_time": response_time,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            service.update_health(False, response_time)
            
            logger.error(f"服务健康检查失败 {service.service_id}: {e}")
            
            return {
                "service_id": service.service_id,
                "healthy": False,
                "error": str(e),
                "response_time": response_time,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        healthy_count = len([s for s in self.services.values() if s.is_healthy])
        degraded_count = len([s for s in self.services.values() if s.status == ServiceStatus.DEGRADED])
        unhealthy_count = len([s for s in self.services.values() if s.status == ServiceStatus.UNHEALTHY])
        
        total_success = sum(s.success_count for s in self.services.values())
        total_errors = sum(s.error_count for s in self.services.values())
        
        avg_response_time = 0.0
        if self.services:
            avg_response_time = sum(s.response_time for s in self.services.values()) / len(self.services)
        
        return {
            "total_instances": len(self.services),
            "max_instances": self.max_instances,
            "healthy_instances": healthy_count,
            "degraded_instances": degraded_count,
            "unhealthy_instances": unhealthy_count,
            "active_references": len(self.active_references),
            "pool_usage": len(self.services) / self.max_instances,
            "overall_stats": {
                "total_success": total_success,
                "total_errors": total_errors,
                "success_rate": total_success / max(total_success + total_errors, 1),
                "average_response_time": avg_response_time
            },
            "created_at": self.created_at.isoformat(),
            "uptime_seconds": (datetime.utcnow() - self.created_at).total_seconds()
        }
    
    async def shutdown(self):
        """关闭连接池"""
        if self.health_check_task:
            self.health_check_task.cancel()
        
        async with self._lock:
            self.services.clear()
            self.active_references.clear()
        
        logger.info("AI服务连接池已关闭")


# 全局服务池实例
_global_service_pool: Optional[AIServicePool] = None


def get_ai_service_pool() -> AIServicePool:
    """获取全局AI服务连接池"""
    global _global_service_pool
    
    if _global_service_pool is None:
        _global_service_pool = AIServicePool()
    
    return _global_service_pool


def reset_ai_service_pool():
    """重置全局服务池"""
    global _global_service_pool
    if _global_service_pool:
        asyncio.create_task(_global_service_pool.shutdown())
    _global_service_pool = None
    return {"message": "AI服务连接池已重置"}