"""
Redis缓存服务
提供统一的缓存接口，支持数据缓存、会话缓存和结果缓存
"""

import json
import logging
import pickle
from datetime import timedelta
from typing import Any, Dict, List, Optional, Union
from functools import wraps

try:
    import redis
    from redis import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = None

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """缓存服务基类"""
    
    def __init__(self):
        self.enabled = False
        self.client = None
        self._setup_cache()
    
    def _setup_cache(self):
        """设置缓存连接"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, cache disabled")
            return
        
        try:
            # 从环境变量或配置中获取Redis连接信息
            redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
            
            self.client = redis.from_url(redis_url, decode_responses=True)
            
            # 测试连接
            self.client.ping()
            self.enabled = True
            logger.info(f"Cache service enabled with Redis at {redis_url}")
            
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Cache disabled.")
            self.enabled = False
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self.enabled:
            return None
            
        try:
            value = self.client.get(key)
            if value is None:
                return None
                
            # 尝试反序列化
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # 如果JSON反序列化失败，尝试pickle
                try:
                    return pickle.loads(value.encode('latin1'))
                except:
                    # 如果都失败，返回原始字符串
                    return value
                    
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        if not self.enabled:
            return False
            
        try:
            # 序列化值
            if isinstance(value, (dict, list, tuple)):
                serialized_value = json.dumps(value, ensure_ascii=False, default=str)
            elif isinstance(value, (str, int, float, bool)):
                serialized_value = json.dumps(value)
            else:
                # 复杂对象使用pickle
                serialized_value = pickle.dumps(value).decode('latin1')
            
            # 设置缓存
            if ttl:
                return self.client.setex(key, ttl, serialized_value)
            else:
                return self.client.set(key, serialized_value)
                
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        if not self.enabled:
            return False
            
        try:
            return self.client.delete(key) > 0
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.enabled:
            return False
            
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    def expire(self, key: str, ttl: int) -> bool:
        """设置键的过期时间"""
        if not self.enabled:
            return False
            
        try:
            return self.client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Cache expire error for key {key}: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """删除匹配模式的所有键"""
        if not self.enabled:
            return 0
            
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear pattern error for pattern {pattern}: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        if not self.enabled:
            return {"enabled": False}
            
        try:
            info = self.client.info()
            return {
                "enabled": True,
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(info)
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"enabled": True, "error": str(e)}
    
    def _calculate_hit_rate(self, info: Dict) -> float:
        """计算缓存命中率"""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        if total == 0:
            return 0.0
        return (hits / total) * 100


class ApplicationCacheService(CacheService):
    """应用级缓存服务"""
    
    def __init__(self):
        super().__init__()
        self.key_prefix = "app:"
        self.default_ttl = 3600  # 1小时
    
    def _make_key(self, key: str) -> str:
        """生成完整的缓存键"""
        return f"{self.key_prefix}{key}"
    
    def cache_user_data(self, user_id: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """缓存用户数据"""
        key = self._make_key(f"user:{user_id}")
        return self.set(key, data, ttl or self.default_ttl)
    
    def get_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户缓存数据"""
        key = self._make_key(f"user:{user_id}")
        return self.get(key)
    
    def cache_dashboard_data(self, user_id: str, data: Dict[str, Any], ttl: int = 300) -> bool:
        """缓存仪表板数据（5分钟TTL）"""
        key = self._make_key(f"dashboard:{user_id}")
        return self.set(key, data, ttl)
    
    def get_dashboard_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取仪表板缓存数据"""
        key = self._make_key(f"dashboard:{user_id}")
        return self.get(key)
    
    def cache_report_result(self, report_id: str, result: Dict[str, Any], ttl: int = 1800) -> bool:
        """缓存报告结果（30分钟TTL）"""
        key = self._make_key(f"report:{report_id}")
        return self.set(key, result, ttl)
    
    def get_report_result(self, report_id: str) -> Optional[Dict[str, Any]]:
        """获取报告结果缓存"""
        key = self._make_key(f"report:{report_id}")
        return self.get(key)
    
    def cache_data_source_schema(self, data_source_id: str, schema: Dict[str, Any], ttl: int = 7200) -> bool:
        """缓存数据源模式（2小时TTL）"""
        key = self._make_key(f"schema:{data_source_id}")
        return self.set(key, schema, ttl)
    
    def get_data_source_schema(self, data_source_id: str) -> Optional[Dict[str, Any]]:
        """获取数据源模式缓存"""
        key = self._make_key(f"schema:{data_source_id}")
        return self.get(key)
    
    def cache_query_result(self, query_hash: str, result: Any, ttl: int = 1800) -> bool:
        """缓存查询结果（30分钟TTL）"""
        key = self._make_key(f"query:{query_hash}")
        return self.set(key, result, ttl)
    
    def get_query_result(self, query_hash: str) -> Optional[Any]:
        """获取查询结果缓存"""
        key = self._make_key(f"query:{query_hash}")
        return self.get(key)
    
    def invalidate_user_cache(self, user_id: str) -> int:
        """清理用户相关的所有缓存"""
        pattern = self._make_key(f"*:{user_id}*")
        return self.clear_pattern(pattern)
    
    def invalidate_data_source_cache(self, data_source_id: str) -> int:
        """清理数据源相关的所有缓存"""
        patterns = [
            self._make_key(f"schema:{data_source_id}"),
            self._make_key(f"query:*:{data_source_id}:*")
        ]
        total_deleted = 0
        for pattern in patterns:
            total_deleted += self.clear_pattern(pattern)
        return total_deleted


def cached(ttl: int = 3600, key_prefix: str = "func"):
    """
    装饰器：为函数结果提供缓存
    
    Args:
        ttl: 缓存时间（秒）
        key_prefix: 缓存键前缀
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = cache_service
            if not cache.enabled:
                return func(*args, **kwargs)
            
            # 生成缓存键
            import hashlib
            key_data = f"{func.__module__}.{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            key_hash = hashlib.md5(key_data.encode()).hexdigest()
            cache_key = f"{key_prefix}:{key_hash}"
            
            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            logger.debug(f"Cache miss for {func.__name__}, result cached")
            return result
            
        return wrapper
    return decorator


def cache_key_for_user_dashboard(user_id: str) -> str:
    """生成用户仪表板缓存键"""
    return f"dashboard:{user_id}"


def cache_key_for_report(report_id: str) -> str:
    """生成报告缓存键"""
    return f"report:{report_id}"


def cache_key_for_query(query: str, data_source_id: str, user_id: str) -> str:
    """生成查询缓存键"""
    import hashlib
    query_hash = hashlib.md5(f"{query}:{data_source_id}:{user_id}".encode()).hexdigest()
    return f"query:{query_hash}"


# 全局缓存服务实例
cache_service = ApplicationCacheService()


def get_cache_service() -> ApplicationCacheService:
    """获取缓存服务实例"""
    return cache_service