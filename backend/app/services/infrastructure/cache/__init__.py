"""
Cache Services Module

提供缓存管理相关服务，包括：
- 统一缓存系统
- 模板缓存
- 占位符缓存
- AI分析结果缓存
"""

from .unified_cache_system import (
    UnifiedCacheManager, UnifiedCacheEntry, CacheType, CacheLevel,
    initialize_cache_manager, get_cache_manager
)
from .redis_cache_service import (
    cache_service,
    get_cache_service,
    cached,
    cache_key_for_user_dashboard,
    cache_key_for_report,
    cache_key_for_query,
    ApplicationCacheService
)

__all__ = [
    "UnifiedCacheManager",
    "UnifiedCacheEntry", 
    "CacheType",
    "CacheLevel",
    "initialize_cache_manager",
    "get_cache_manager",
    "cache_service",
    "get_cache_service",
    "cached",
    "cache_key_for_user_dashboard",
    "cache_key_for_report", 
    "cache_key_for_query",
    "ApplicationCacheService"
]