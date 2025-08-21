"""
智能缓存管理系统
提供多层次缓存策略和智能缓存优化
"""

import asyncio
import logging
import threading
import time
import pickle
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, TypeVar, Generic, Callable, List, Union
from collections import OrderedDict
import weakref


T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """缓存条目"""
    value: T
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl: Optional[timedelta] = None
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return datetime.now() - self.created_at > self.ttl
    
    def touch(self):
        """更新访问时间"""
        self.last_accessed = datetime.now()
        self.access_count += 1


class CacheStrategy(ABC):
    """缓存策略抽象类"""
    
    @abstractmethod
    def should_evict(self, entries: Dict[str, CacheEntry], max_size: int) -> List[str]:
        """决定应该驱逐哪些条目"""
        pass


class LRUStrategy(CacheStrategy):
    """最近最少使用策略"""
    
    def should_evict(self, entries: Dict[str, CacheEntry], max_size: int) -> List[str]:
        if len(entries) <= max_size:
            return []
        
        # 按最后访问时间排序
        sorted_keys = sorted(
            entries.keys(),
            key=lambda k: entries[k].last_accessed
        )
        
        return sorted_keys[:len(entries) - max_size]


class LFUStrategy(CacheStrategy):
    """最少频率使用策略"""
    
    def should_evict(self, entries: Dict[str, CacheEntry], max_size: int) -> List[str]:
        if len(entries) <= max_size:
            return []
        
        # 按访问次数排序
        sorted_keys = sorted(
            entries.keys(),
            key=lambda k: (entries[k].access_count, entries[k].last_accessed)
        )
        
        return sorted_keys[:len(entries) - max_size]


class TTLStrategy(CacheStrategy):
    """基于TTL的策略"""
    
    def should_evict(self, entries: Dict[str, CacheEntry], max_size: int) -> List[str]:
        # 首先移除过期条目
        expired_keys = [k for k, entry in entries.items() if entry.is_expired()]
        
        if len(entries) - len(expired_keys) <= max_size:
            return expired_keys
        
        # 如果还需要更多空间，按创建时间排序
        remaining_entries = {k: v for k, v in entries.items() if k not in expired_keys}
        sorted_keys = sorted(
            remaining_entries.keys(),
            key=lambda k: remaining_entries[k].created_at
        )
        
        additional_evictions = sorted_keys[:len(remaining_entries) - max_size]
        return expired_keys + additional_evictions


class SmartCache(Generic[T]):
    """智能缓存实现"""
    
    def __init__(self,
                 max_size: int = 1000,
                 default_ttl: Optional[timedelta] = None,
                 strategy: Optional[CacheStrategy] = None,
                 enable_stats: bool = True):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.strategy = strategy or LRUStrategy()
        self.enable_stats = enable_stats
        
        self.logger = logging.getLogger(__name__)
        self._entries: Dict[str, CacheEntry[T]] = {}
        self._lock = threading.RLock()
        
        # 统计信息
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
    def get(self, key: str) -> Optional[T]:
        """获取缓存值"""
        with self._lock:
            if key not in self._entries:
                if self.enable_stats:
                    self.misses += 1
                return None
            
            entry = self._entries[key]
            
            # 检查是否过期
            if entry.is_expired():
                del self._entries[key]
                if self.enable_stats:
                    self.misses += 1
                return None
            
            # 更新访问信息
            entry.touch()
            
            if self.enable_stats:
                self.hits += 1
            
            return entry.value
    
    def set(self, key: str, value: T, ttl: Optional[timedelta] = None):
        """设置缓存值"""
        with self._lock:
            # 使用指定的TTL或默认TTL
            effective_ttl = ttl or self.default_ttl
            
            # 创建缓存条目
            entry = CacheEntry(value=value, ttl=effective_ttl)
            self._entries[key] = entry
            
            # 检查是否需要驱逐
            self._evict_if_needed()
    
    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        with self._lock:
            if key in self._entries:
                del self._entries[key]
                return True
            return False
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._entries.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0
    
    def _evict_if_needed(self):
        """根据策略驱逐条目"""
        if len(self._entries) <= self.max_size:
            return
        
        keys_to_evict = self.strategy.should_evict(self._entries, self.max_size)
        
        for key in keys_to_evict:
            if key in self._entries:
                del self._entries[key]
                if self.enable_stats:
                    self.evictions += 1
        
        self.logger.debug(f"Evicted {len(keys_to_evict)} cache entries")
    
    def cleanup_expired(self) -> int:
        """清理过期条目"""
        with self._lock:
            expired_keys = [k for k, entry in self._entries.items() if entry.is_expired()]
            
            for key in expired_keys:
                del self._entries[key]
            
            if expired_keys:
                self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
            
            return {
                "size": len(self._entries),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "hit_rate": hit_rate,
                "utilization": len(self._entries) / self.max_size
            }


class QueryCache:
    """数据库查询缓存"""
    
    def __init__(self, max_size: int = 500, default_ttl: timedelta = timedelta(hours=1)):
        self.cache = SmartCache[Any](
            max_size=max_size,
            default_ttl=default_ttl,
            strategy=TTLStrategy()
        )
        self.logger = logging.getLogger(__name__)
    
    def _generate_key(self, query: str, params: Optional[Dict[str, Any]] = None) -> str:
        """生成缓存键"""
        key_data = {
            "query": query,
            "params": params or {}
        }
        key_str = pickle.dumps(key_data, protocol=pickle.HIGHEST_PROTOCOL)
        return hashlib.md5(key_str).hexdigest()
    
    def get_query_result(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """获取查询结果"""
        key = self._generate_key(query, params)
        result = self.cache.get(key)
        
        if result is not None:
            self.logger.debug(f"Query cache hit: {query[:50]}...")
        
        return result
    
    def cache_query_result(self, query: str, result: Any, params: Optional[Dict[str, Any]] = None, ttl: Optional[timedelta] = None):
        """缓存查询结果"""
        key = self._generate_key(query, params)
        self.cache.set(key, result, ttl)
        self.logger.debug(f"Cached query result: {query[:50]}...")
    
    def invalidate_pattern(self, pattern: str):
        """按模式失效缓存"""
        # 这里可以实现更复杂的模式匹配失效逻辑
        self.logger.info(f"Invalidating cache pattern: {pattern}")


class AIResponseCache:
    """AI响应缓存"""
    
    def __init__(self, max_size: int = 200, default_ttl: timedelta = timedelta(hours=6)):
        self.cache = SmartCache[str](
            max_size=max_size,
            default_ttl=default_ttl,
            strategy=LFUStrategy()
        )
        self.logger = logging.getLogger(__name__)
    
    def _generate_key(self, prompt: str, context: str = "", task_type: str = "", **kwargs) -> str:
        """生成AI请求的缓存键"""
        key_data = {
            "prompt": prompt,
            "context": context,
            "task_type": task_type,
            "kwargs": sorted(kwargs.items())
        }
        key_str = pickle.dumps(key_data, protocol=pickle.HIGHEST_PROTOCOL)
        return hashlib.md5(key_str).hexdigest()
    
    def get_response(self, prompt: str, context: str = "", task_type: str = "", **kwargs) -> Optional[str]:
        """获取AI响应"""
        key = self._generate_key(prompt, context, task_type, **kwargs)
        response = self.cache.get(key)
        
        if response is not None:
            self.logger.debug(f"AI response cache hit: {prompt[:30]}...")
        
        return response
    
    def cache_response(self, response: str, prompt: str, context: str = "", task_type: str = "", ttl: Optional[timedelta] = None, **kwargs):
        """缓存AI响应"""
        key = self._generate_key(prompt, context, task_type, **kwargs)
        self.cache.set(key, response, ttl)
        self.logger.debug(f"Cached AI response: {prompt[:30]}...")


class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 各种缓存实例
        self.query_cache = QueryCache()
        self.ai_response_cache = AIResponseCache()
        
        # 自定义缓存注册表
        self._custom_caches: Dict[str, SmartCache] = {}
        
        # 清理任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval = 300  # 5分钟
    
    def register_cache(self, name: str, cache: SmartCache):
        """注册自定义缓存"""
        self._custom_caches[name] = cache
        self.logger.info(f"Registered custom cache: {name}")
    
    def get_cache(self, name: str) -> Optional[SmartCache]:
        """获取自定义缓存"""
        return self._custom_caches.get(name)
    
    def start_cleanup_task(self):
        """启动清理任务"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self.logger.info("Cache cleanup task started")
    
    async def stop_cleanup_task(self):
        """停止清理任务"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self.logger.info("Cache cleanup task stopped")
    
    async def _cleanup_loop(self):
        """清理循环"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                self.cleanup_all_caches()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cache cleanup loop: {e}")
    
    def cleanup_all_caches(self):
        """清理所有缓存的过期条目"""
        total_cleaned = 0
        
        # 清理查询缓存
        cleaned = self.query_cache.cache.cleanup_expired()
        total_cleaned += cleaned
        
        # 清理AI响应缓存
        cleaned = self.ai_response_cache.cache.cleanup_expired()
        total_cleaned += cleaned
        
        # 清理自定义缓存
        for name, cache in self._custom_caches.items():
            cleaned = cache.cleanup_expired()
            total_cleaned += cleaned
        
        if total_cleaned > 0:
            self.logger.info(f"Cleaned up {total_cleaned} expired cache entries")
    
    def clear_all_caches(self):
        """清空所有缓存"""
        self.query_cache.cache.clear()
        self.ai_response_cache.cache.clear()
        
        for cache in self._custom_caches.values():
            cache.clear()
        
        self.logger.info("All caches cleared")
    
    def get_global_stats(self) -> Dict[str, Any]:
        """获取全局缓存统计"""
        stats = {
            "query_cache": self.query_cache.cache.get_stats(),
            "ai_response_cache": self.ai_response_cache.cache.get_stats(),
            "custom_caches": {
                name: cache.get_stats()
                for name, cache in self._custom_caches.items()
            }
        }
        
        # 计算总体统计
        total_size = sum(s["size"] for s in stats.values() if isinstance(s, dict) and "size" in s)
        total_hits = sum(s["hits"] for s in stats.values() if isinstance(s, dict) and "hits" in s)
        total_misses = sum(s["misses"] for s in stats.values() if isinstance(s, dict) and "misses" in s)
        
        stats["global"] = {
            "total_size": total_size,
            "total_hits": total_hits,
            "total_misses": total_misses,
            "global_hit_rate": total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0.0
        }
        
        return stats


# 全局缓存管理器
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cache_query_result(query: str, result: Any, params: Optional[Dict[str, Any]] = None, ttl: Optional[timedelta] = None):
    """缓存查询结果的便捷函数"""
    manager = get_cache_manager()
    manager.query_cache.cache_query_result(query, result, params, ttl)


def get_cached_query_result(query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    """获取缓存查询结果的便捷函数"""
    manager = get_cache_manager()
    return manager.query_cache.get_query_result(query, params)


def cache_ai_response(response: str, prompt: str, context: str = "", task_type: str = "", ttl: Optional[timedelta] = None, **kwargs):
    """缓存AI响应的便捷函数"""
    manager = get_cache_manager()
    manager.ai_response_cache.cache_response(response, prompt, context, task_type, ttl, **kwargs)


def get_cached_ai_response(prompt: str, context: str = "", task_type: str = "", **kwargs) -> Optional[str]:
    """获取缓存AI响应的便捷函数"""
    manager = get_cache_manager()
    return manager.ai_response_cache.get_response(prompt, context, task_type, **kwargs)