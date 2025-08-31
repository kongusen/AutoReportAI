"""
占位符结果缓存

缓存占位符的分析结果和SQL生成结果
"""

import logging
import hashlib
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    data: Dict[str, Any]
    timestamp: datetime
    ttl_seconds: int
    access_count: int = 0
    last_access: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl_seconds <= 0:
            return False  # 永不过期
        return datetime.now() > (self.timestamp + timedelta(seconds=self.ttl_seconds))
    
    def update_access(self):
        """更新访问信息"""
        self.access_count += 1
        self.last_access = datetime.now()

class ResultCache:
    """占位符结果缓存"""
    
    def __init__(self, 
                 max_entries: int = 1000,
                 default_ttl: int = 3600,  # 1小时默认TTL
                 cleanup_interval: int = 300):  # 5分钟清理间隔
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        
        # 存储缓存条目
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        
        # 统计信息
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'cleanups': 0
        }
        
        # 启动定期清理任务
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _generate_cache_key(self, 
                           placeholder_content: str,
                           context_data: Dict[str, Any],
                           additional_params: Dict[str, Any] = None) -> str:
        """生成缓存键"""
        # 创建用于哈希的数据
        hash_data = {
            'placeholder_content': placeholder_content,
            'context_data': context_data,
            'additional_params': additional_params or {}
        }
        
        # 将数据序列化并计算哈希
        json_str = json.dumps(hash_data, sort_keys=True, ensure_ascii=False)
        hash_obj = hashlib.md5(json_str.encode('utf-8'))
        return f"result_{hash_obj.hexdigest()}"
    
    async def get(self, 
                  placeholder_content: str,
                  context_data: Dict[str, Any],
                  additional_params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """获取缓存结果"""
        key = self._generate_cache_key(placeholder_content, context_data, additional_params)
        
        async with self._lock:
            entry = self._cache.get(key)
            if not entry:
                self.stats['misses'] += 1
                return None
            
            if entry.is_expired():
                del self._cache[key]
                self.stats['misses'] += 1
                return None
            
            entry.update_access()
            self.stats['hits'] += 1
            return entry.data.copy()
    
    async def set(self, 
                  placeholder_content: str,
                  context_data: Dict[str, Any],
                  result_data: Dict[str, Any],
                  ttl_seconds: Optional[int] = None,
                  additional_params: Dict[str, Any] = None):
        """设置缓存结果"""
        key = self._generate_cache_key(placeholder_content, context_data, additional_params)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        
        async with self._lock:
            # 如果缓存已满，进行LRU驱逐
            if len(self._cache) >= self.max_entries:
                await self._evict_lru()
            
            entry = CacheEntry(
                key=key,
                data=result_data.copy(),
                timestamp=datetime.now(),
                ttl_seconds=ttl
            )
            
            self._cache[key] = entry
    
    async def invalidate(self, 
                        placeholder_content: str,
                        context_data: Dict[str, Any],
                        additional_params: Dict[str, Any] = None):
        """使特定缓存失效"""
        key = self._generate_cache_key(placeholder_content, context_data, additional_params)
        
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    async def invalidate_by_pattern(self, pattern: str):
        """根据模式使缓存失效"""
        async with self._lock:
            keys_to_remove = [
                key for key in self._cache.keys() 
                if pattern in key
            ]
            
            for key in keys_to_remove:
                del self._cache[key]
    
    async def clear(self):
        """清空所有缓存"""
        async with self._lock:
            self._cache.clear()
    
    async def _evict_lru(self):
        """驱逐最少使用的缓存条目"""
        if not self._cache:
            return
        
        # 找到最少访问的条目
        lru_key = min(
            self._cache.keys(),
            key=lambda k: (
                self._cache[k].access_count,
                self._cache[k].last_access or self._cache[k].timestamp
            )
        )
        
        del self._cache[lru_key]
        self.stats['evictions'] += 1
    
    def _start_cleanup_task(self):
        """启动清理任务"""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(self.cleanup_interval)
                    await self._cleanup_expired()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"缓存清理任务出错: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    async def _cleanup_expired(self):
        """清理过期的缓存条目"""
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                self.stats['cleanups'] += 1
                logger.debug(f"清理了 {len(expired_keys)} 个过期缓存条目")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'cache_size': len(self._cache),
            'max_entries': self.max_entries,
            'hit_rate': hit_rate,
            'stats': self.stats.copy(),
            'memory_info': {
                'entries_count': len(self._cache),
                'avg_access_count': sum(e.access_count for e in self._cache.values()) / len(self._cache) if self._cache else 0
            }
        }
    
    def get_cache_info(self) -> List[Dict[str, Any]]:
        """获取缓存详细信息"""
        return [
            {
                'key': entry.key,
                'timestamp': entry.timestamp.isoformat(),
                'ttl_seconds': entry.ttl_seconds,
                'access_count': entry.access_count,
                'last_access': entry.last_access.isoformat() if entry.last_access else None,
                'is_expired': entry.is_expired(),
                'data_size': len(str(entry.data))
            }
            for entry in self._cache.values()
        ]
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        stats = self.get_stats()
        
        # 检查缓存健康状态
        health_status = "healthy"
        issues = []
        
        # 检查命中率
        if stats['hit_rate'] < 0.1:  # 命中率低于10%
            issues.append("缓存命中率过低")
            health_status = "warning"
        
        # 检查缓存大小
        if stats['cache_size'] >= self.max_entries * 0.9:  # 使用率超过90%
            issues.append("缓存容量即将用完")
            health_status = "warning"
        
        return {
            'status': health_status,
            'cache_size': stats['cache_size'],
            'hit_rate': stats['hit_rate'],
            'issues': issues,
            'stats': stats
        }
    
    def shutdown(self):
        """关闭缓存"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        logger.info("结果缓存已关闭")