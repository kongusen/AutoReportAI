"""
AI Service Pool
管理AI服务实例池，提供负载均衡和健康检查功能
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
import threading

logger = logging.getLogger(__name__)


@dataclass
class ServiceInstance:
    """服务实例"""
    id: str
    name: str
    endpoint: str
    is_healthy: bool = True
    last_health_check: Optional[datetime] = None
    response_time: float = 0.0
    error_count: int = 0
    success_count: int = 0


class AIServicePool:
    """AI服务池"""
    
    def __init__(self):
        self.instances: Dict[str, ServiceInstance] = {}
        self.lock = threading.RLock()
        self._current_instance_index = 0
        
    def add_instance(self, instance_id: str, name: str, endpoint: str) -> bool:
        """添加服务实例"""
        with self.lock:
            if instance_id in self.instances:
                logger.warning(f"Service instance {instance_id} already exists")
                return False
                
            self.instances[instance_id] = ServiceInstance(
                id=instance_id,
                name=name,
                endpoint=endpoint,
                last_health_check=datetime.utcnow()
            )
            logger.info(f"Added service instance: {name} ({instance_id})")
            return True
    
    def remove_instance(self, instance_id: str) -> bool:
        """移除服务实例"""
        with self.lock:
            if instance_id in self.instances:
                instance = self.instances.pop(instance_id)
                logger.info(f"Removed service instance: {instance.name} ({instance_id})")
                return True
            return False
    
    def mark_healthy(self, instance_id: str, response_time: float = 0.0):
        """标记实例为健康"""
        with self.lock:
            if instance_id in self.instances:
                instance = self.instances[instance_id]
                instance.is_healthy = True
                instance.last_health_check = datetime.utcnow()
                instance.response_time = response_time
                instance.success_count += 1
    
    def mark_unhealthy(self, instance_id: str, error_message: str = ""):
        """标记实例为不健康"""
        with self.lock:
            if instance_id in self.instances:
                instance = self.instances[instance_id]
                instance.is_healthy = False
                instance.last_health_check = datetime.utcnow()
                instance.error_count += 1
                logger.warning(f"Marked instance {instance_id} as unhealthy: {error_message}")
    
    def get_healthy_instance(self) -> Optional[ServiceInstance]:
        """获取健康的服务实例（轮询负载均衡）"""
        with self.lock:
            healthy_instances = [inst for inst in self.instances.values() if inst.is_healthy]
            
            if not healthy_instances:
                return None
            
            # 简单的轮询算法
            instance = healthy_instances[self._current_instance_index % len(healthy_instances)]
            self._current_instance_index += 1
            
            return instance
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """获取池统计信息"""
        with self.lock:
            total_instances = len(self.instances)
            healthy_instances = len([inst for inst in self.instances.values() if inst.is_healthy])
            
            if total_instances == 0:
                usage = 0.0
            else:
                usage = (total_instances - healthy_instances) / total_instances
            
            total_requests = sum(inst.success_count + inst.error_count for inst in self.instances.values())
            total_success = sum(inst.success_count for inst in self.instances.values())
            
            success_rate = (total_success / total_requests * 100) if total_requests > 0 else 100.0
            
            avg_response_time = 0.0
            if healthy_instances > 0:
                total_response_time = sum(
                    inst.response_time for inst in self.instances.values() 
                    if inst.is_healthy
                )
                avg_response_time = total_response_time / healthy_instances
            
            return {
                "total_instances": total_instances,
                "healthy_instances": healthy_instances,
                "unhealthy_instances": total_instances - healthy_instances,
                "pool_usage": usage,
                "success_rate": success_rate,
                "average_response_time": avg_response_time,
                "total_requests": total_requests,
                "instance_details": [
                    {
                        "id": inst.id,
                        "name": inst.name,
                        "is_healthy": inst.is_healthy,
                        "response_time": inst.response_time,
                        "success_count": inst.success_count,
                        "error_count": inst.error_count,
                        "last_health_check": inst.last_health_check.isoformat() if inst.last_health_check else None
                    }
                    for inst in self.instances.values()
                ]
            }
    
    def get_instance_by_id(self, instance_id: str) -> Optional[ServiceInstance]:
        """根据ID获取实例"""
        return self.instances.get(instance_id)
    
    def health_check_all(self) -> Dict[str, bool]:
        """检查所有实例健康状态"""
        with self.lock:
            return {
                inst.id: inst.is_healthy 
                for inst in self.instances.values()
            }
    
    def reset_stats(self):
        """重置统计信息"""
        with self.lock:
            for instance in self.instances.values():
                instance.success_count = 0
                instance.error_count = 0
                instance.response_time = 0.0
            logger.info("Service pool statistics reset")
    
    def clear_all_instances(self):
        """清除所有实例"""
        with self.lock:
            count = len(self.instances)
            self.instances.clear()
            self._current_instance_index = 0
            logger.info(f"Cleared {count} service instances from pool")


# 全局服务池实例
_global_service_pool: Optional[AIServicePool] = None
_pool_lock = threading.Lock()


def get_ai_service_pool() -> AIServicePool:
    """获取全局AI服务池实例"""
    global _global_service_pool
    
    with _pool_lock:
        if _global_service_pool is None:
            _global_service_pool = AIServicePool()
            # 默认添加一些示例实例（实际使用中应该从配置加载）
            _global_service_pool.add_instance("default", "Default AI Service", "http://localhost:8080")
        
        return _global_service_pool


def reset_ai_service_pool():
    """重置AI服务池"""
    global _global_service_pool
    
    with _pool_lock:
        if _global_service_pool is not None:
            _global_service_pool.clear_all_instances()
            _global_service_pool.reset_stats()
            logger.info("AI service pool has been reset")
        else:
            logger.info("AI service pool was not initialized, nothing to reset")


def initialize_service_pool_from_config(config: Dict[str, Any]):
    """从配置初始化服务池"""
    pool = get_ai_service_pool()
    
    # 清除现有实例
    pool.clear_all_instances()
    
    # 从配置添加实例
    instances = config.get("ai_service_instances", [])
    for instance_config in instances:
        pool.add_instance(
            instance_id=instance_config["id"],
            name=instance_config["name"],
            endpoint=instance_config["endpoint"]
        )
    
    logger.info(f"Initialized service pool with {len(instances)} instances from config")