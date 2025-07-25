"""
优化的服务层包
提供统一的服务访问接口
"""

from .base_service import BaseService, ServiceException, ValidationError, NotFoundError, PermissionError
from .data_source_service import data_source_service
from .report_service import report_service

# 服务实例列表
__all__ = [
    # 基础类
    "BaseService",
    "ServiceException", 
    "ValidationError",
    "NotFoundError",
    "PermissionError",
    
    # 服务实例
    "data_source_service",
    "report_service",
    
    # 服务管理器
    "ServiceManager"
]


class ServiceManager:
    """服务管理器"""
    
    def __init__(self):
        self._services = {
            "data_source": data_source_service,
            "report": report_service,
        }
    
    def get_service(self, service_name: str):
        """根据名称获取服务"""
        return self._services.get(service_name.lower())
    
    def register_service(self, name: str, service):
        """注册新服务"""
        self._services[name.lower()] = service
    
    def list_services(self) -> list:
        """列出所有可用服务"""
        return list(self._services.keys())
    
    @property
    def data_source(self):
        """数据源服务"""
        return self._services["data_source"]
    
    @property
    def report(self):
        """报告服务"""
        return self._services["report"]


# 创建全局服务管理器实例
services = ServiceManager()