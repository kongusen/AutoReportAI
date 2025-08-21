"""
基础设施层入口

提供缓存、监控、日志、配置等通用能力的统一接口：
- cache: 缓存服务（合并了cache_services）
- config: 配置管理
- monitoring: 监控指标
- storage: 文件存储
- notification: 通知服务
"""

# 缓存服务（合并后）
from .cache.cache_interfaces import CacheInterface
from .cache.memory_cache import MemoryCache
from .cache.pipeline_cache_manager import (
    PipelineCacheManager, CacheLevel
)

# 配置服务
from .config.settings import ServiceLayerSettings

# 监控服务  
from .monitoring.metrics_collector import MetricsCollector

# 存储服务
from .storage.file_storage_service import FileStorageService

# 通知服务
from .notification.notification_service import NotificationService
from .notification.email_service import EmailService

__all__ = [
    # 缓存
    "CacheInterface",
    "MemoryCache", 
    "PipelineCacheManager",
    "CacheLevel",
    
    # 配置
    "ServiceLayerSettings",
    
    # 监控
    "MetricsCollector",
    
    # 存储
    "FileStorageService",
    
    # 通知
    "NotificationService",
    "EmailService",
]


