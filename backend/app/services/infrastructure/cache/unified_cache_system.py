"""
统一缓存系统

整合所有缓存相关的定义和操作，提供统一的缓存接口
"""

import logging
import asyncio
import json
import hashlib
from typing import Dict, Any, Optional, List, Union, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import redis
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """缓存层级"""
    MEMORY = "memory"           # 内存缓存（最快，容量小）
    REDIS = "redis"            # Redis缓存（中等速度，中等容量）
    DATABASE = "database"      # 数据库缓存（较慢，大容量，持久化）
    

class CacheStrategy(Enum):
    """缓存策略"""
    LRU = "lru"                    # 最近最少使用
    LFU = "lfu"                    # 最不频繁使用
    FIFO = "fifo"                  # 先进先出
    TTL = "ttl"                    # 基于时间的过期
    INTELLIGENT = "intelligent"     # 智能策略（根据访问模式）


class CacheType(Enum):
    """缓存数据类型"""
    PLACEHOLDER_RESULT = "placeholder_result"     # 占位符结果
    AGENT_ANALYSIS = "agent_analysis"            # Agent分析结果
    SQL_QUERY_RESULT = "sql_query_result"        # SQL查询结果
    TEMPLATE_DATA = "template_data"              # 模板数据
    REPORT_CONTENT = "report_content"            # 报告内容
    SYSTEM_CONFIG = "system_config"              # 系统配置


@dataclass
class CacheMetrics:
    """缓存指标"""
    hit_count: int = 0
    miss_count: int = 0
    creation_time: datetime = field(default_factory=datetime.now)
    last_hit_time: Optional[datetime] = None
    last_miss_time: Optional[datetime] = None
    access_frequency: float = 0.0  # 每小时访问次数
    size_bytes: int = 0
    
    @property
    def hit_rate(self) -> float:
        """缓存命中率"""
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0
    
    @property
    def age_hours(self) -> float:
        """缓存年龄（小时）"""
        return (datetime.now() - self.creation_time).total_seconds() / 3600
    
    def update_hit(self):
        """更新命中统计"""
        self.hit_count += 1
        self.last_hit_time = datetime.now()
        self._update_access_frequency()
    
    def update_miss(self):
        """更新未命中统计"""
        self.miss_count += 1
        self.last_miss_time = datetime.now()
    
    def _update_access_frequency(self):
        """更新访问频率"""
        if self.age_hours > 0:
            self.access_frequency = self.hit_count / self.age_hours


@dataclass
class UnifiedCacheEntry:
    """统一缓存条目"""
    # 基础信息
    key: str
    value: Any
    cache_type: CacheType
    cache_level: CacheLevel
    
    # 时间信息
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    ttl_seconds: int = 3600  # 默认1小时
    
    # 质量信息
    confidence: float = 1.0
    reliability: float = 1.0  # 数据可靠性
    
    # 依赖和关系
    dependencies: Set[str] = field(default_factory=set)  # 依赖的其他缓存键
    tags: Set[str] = field(default_factory=set)          # 标签用于批量操作
    
    # 元数据和统计
    metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: CacheMetrics = field(default_factory=CacheMetrics)
    
    def __post_init__(self):
        """初始化后处理"""
        if self.expires_at is None and self.ttl_seconds > 0:
            self.expires_at = self.created_at + timedelta(seconds=self.ttl_seconds)
        
        # 计算数据大小
        try:
            self.metrics.size_bytes = len(json.dumps(self.value, default=str).encode('utf-8'))
        except (TypeError, ValueError):
            self.metrics.size_bytes = len(str(self.value).encode('utf-8'))
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """检查是否有效（未过期且有效数据）"""
        return not self.is_expired and self.value is not None
    
    @property
    def remaining_ttl(self) -> int:
        """剩余TTL（秒）"""
        if self.expires_at is None:
            return -1  # 永不过期
        remaining = (self.expires_at - datetime.now()).total_seconds()
        return max(0, int(remaining))
    
    @property
    def priority_score(self) -> float:
        """计算优先级分数（用于清理策略）"""
        # 基于命中率、频率、最近访问时间、置信度计算
        hit_rate_score = self.metrics.hit_rate * 40
        frequency_score = min(self.metrics.access_frequency * 5, 30)
        
        if self.metrics.last_hit_time:
            hours_since_hit = (datetime.now() - self.metrics.last_hit_time).total_seconds() / 3600
            recency_score = max(0, 20 - hours_since_hit)
        else:
            recency_score = 0
        
        confidence_score = self.confidence * 10
        
        return hit_rate_score + frequency_score + recency_score + confidence_score
    
    def refresh_expiry(self, ttl_seconds: Optional[int] = None) -> None:
        """刷新过期时间"""
        if ttl_seconds is not None:
            self.ttl_seconds = ttl_seconds
        if self.ttl_seconds > 0:
            self.expires_at = datetime.now() + timedelta(seconds=self.ttl_seconds)
    
    def add_dependency(self, dependency_key: str) -> None:
        """添加依赖"""
        self.dependencies.add(dependency_key)
    
    def add_tag(self, tag: str) -> None:
        """添加标签"""
        self.tags.add(tag)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "key": self.key,
            "value": self.value,
            "cache_type": self.cache_type.value,
            "cache_level": self.cache_level.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "ttl_seconds": self.ttl_seconds,
            "confidence": self.confidence,
            "reliability": self.reliability,
            "dependencies": list(self.dependencies),
            "tags": list(self.tags),
            "metadata": self.metadata,
            "metrics": {
                "hit_count": self.metrics.hit_count,
                "miss_count": self.metrics.miss_count,
                "hit_rate": self.metrics.hit_rate,
                "access_frequency": self.metrics.access_frequency,
                "size_bytes": self.metrics.size_bytes
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedCacheEntry':
        """从字典创建实例"""
        metrics = CacheMetrics(
            hit_count=data["metrics"]["hit_count"],
            miss_count=data["metrics"]["miss_count"],
            creation_time=datetime.fromisoformat(data["created_at"]),
            size_bytes=data["metrics"]["size_bytes"]
        )
        
        return cls(
            key=data["key"],
            value=data["value"],
            cache_type=CacheType(data["cache_type"]),
            cache_level=CacheLevel(data["cache_level"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data["expires_at"] else None,
            ttl_seconds=data["ttl_seconds"],
            confidence=data["confidence"],
            reliability=data["reliability"],
            dependencies=set(data["dependencies"]),
            tags=set(data["tags"]),
            metadata=data["metadata"],
            metrics=metrics
        )


class CacheInterface(ABC):
    """缓存接口"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[UnifiedCacheEntry]:
        """获取缓存"""
        pass
    
    @abstractmethod
    async def set(self, entry: UnifiedCacheEntry) -> bool:
        """设置缓存"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """清空缓存"""
        pass


class MemoryCache(CacheInterface):
    """内存缓存实现"""
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, UnifiedCacheEntry] = {}
        self.max_size = max_size
        self.access_order: List[str] = []  # LRU顺序
    
    async def get(self, key: str) -> Optional[UnifiedCacheEntry]:
        """获取缓存"""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if entry.is_expired:
            await self.delete(key)
            entry.metrics.update_miss()
            return None
        
        # 更新访问顺序
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)
        
        entry.metrics.update_hit()
        return entry
    
    async def set(self, entry: UnifiedCacheEntry) -> bool:
        """设置缓存"""
        try:
            # 如果超过容量，清理旧条目
            if len(self.cache) >= self.max_size:
                await self._evict_lru()
            
            self.cache[entry.key] = entry
            if entry.key not in self.access_order:
                self.access_order.append(entry.key)
            
            return True
        except Exception as e:
            logger.error(f"内存缓存设置失败: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if key in self.cache:
            del self.cache[key]
        if key in self.access_order:
            self.access_order.remove(key)
        return True
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        return key in self.cache and not self.cache[key].is_expired
    
    async def clear(self) -> bool:
        """清空缓存"""
        self.cache.clear()
        self.access_order.clear()
        return True
    
    async def _evict_lru(self):
        """清理最少使用的缓存"""
        if self.access_order:
            oldest_key = self.access_order[0]
            await self.delete(oldest_key)


class RedisCache(CacheInterface):
    """Redis缓存实现"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.key_prefix = "autoreport:cache:"
    
    def _get_full_key(self, key: str) -> str:
        """获取完整的Redis键"""
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[UnifiedCacheEntry]:
        """获取缓存"""
        if not self.redis_client:
            return None
        
        try:
            full_key = self._get_full_key(key)
            data = self.redis_client.get(full_key)
            if not data:
                return None
            
            entry_dict = json.loads(data)
            entry = UnifiedCacheEntry.from_dict(entry_dict)
            
            if entry.is_expired:
                await self.delete(key)
                entry.metrics.update_miss()
                return None
            
            entry.metrics.update_hit()
            # 更新Redis中的统计信息
            await self._update_entry_metrics(entry)
            return entry
            
        except Exception as e:
            logger.error(f"Redis缓存获取失败: {e}")
            return None
    
    async def set(self, entry: UnifiedCacheEntry) -> bool:
        """设置缓存（带大小检查和压缩）"""
        if not self.redis_client:
            return False
        
        try:
            full_key = self._get_full_key(entry.key)
            
            # 优化缓存数据 - 移除不必要的大型数据
            optimized_entry = self._optimize_cache_entry(entry)
            data = json.dumps(optimized_entry.to_dict(), ensure_ascii=False)
            
            # 检查数据大小，如果超过限制则压缩
            max_cache_size = 512 * 1024  # 512KB限制
            if len(data.encode('utf-8')) > max_cache_size:
                logger.warning(f"缓存数据过大 ({len(data.encode('utf-8'))} bytes)，跳过Redis缓存: {entry.key}")
                return False
            
            if optimized_entry.ttl_seconds > 0:
                self.redis_client.setex(full_key, optimized_entry.ttl_seconds, data)
            else:
                self.redis_client.set(full_key, data)
            
            logger.debug(f"Redis缓存设置成功，大小: {len(data.encode('utf-8'))} bytes")
            return True
            
        except Exception as e:
            # Redis内存不足时的优雅处理
            if "OOM" in str(e) or "maxmemory" in str(e):
                logger.warning(f"Redis内存不足，跳过缓存: {entry.key}")
                return False
            else:
                logger.error(f"Redis缓存设置失败: {e}")
                return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.redis_client:
            return False
        
        try:
            full_key = self._get_full_key(key)
            self.redis_client.delete(full_key)
            return True
            
        except Exception as e:
            logger.error(f"Redis缓存删除失败: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        if not self.redis_client:
            return False
        
        try:
            full_key = self._get_full_key(key)
            return self.redis_client.exists(full_key) > 0
            
        except Exception as e:
            logger.error(f"Redis缓存检查失败: {e}")
            return False
    
    async def clear(self) -> bool:
        """清空缓存"""
        if not self.redis_client:
            return False
        
        try:
            pattern = f"{self.key_prefix}*"
            # 使用scan而不是keys来避免阻塞
            cursor = 0
            deleted_count = 0
            while True:
                cursor, keys = self.redis_client.scan(cursor, match=pattern, count=100)
                if keys:
                    self.redis_client.delete(*keys)
                    deleted_count += len(keys)
                if cursor == 0:
                    break
            
            logger.info(f"Redis缓存清空完成，删除了 {deleted_count} 个键")
            return True
            
        except Exception as e:
            logger.error(f"Redis缓存清空失败: {e}")
            return False
    
    async def cleanup_expired_keys(self) -> int:
        """清理过期的缓存键"""
        if not self.redis_client:
            return 0
        
        try:
            pattern = f"{self.key_prefix}*"
            cursor = 0
            cleaned_count = 0
            
            while True:
                cursor, keys = self.redis_client.scan(cursor, match=pattern, count=100)
                for key in keys:
                    ttl = self.redis_client.ttl(key)
                    if ttl == -2:  # 键已过期
                        self.redis_client.delete(key)
                        cleaned_count += 1
                
                if cursor == 0:
                    break
            
            logger.info(f"清理了 {cleaned_count} 个过期缓存键")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理过期缓存键失败: {e}")
            return 0
    
    async def _update_entry_metrics(self, entry: UnifiedCacheEntry):
        """更新条目指标"""
        try:
            full_key = self._get_full_key(entry.key)
            optimized_entry = self._optimize_cache_entry(entry)
            data = json.dumps(optimized_entry.to_dict(), ensure_ascii=False)
            # 保持原有TTL
            ttl = self.redis_client.ttl(full_key)
            if ttl > 0:
                self.redis_client.setex(full_key, ttl, data)
            else:
                self.redis_client.set(full_key, data)
        except Exception as e:
            logger.warning(f"更新Redis缓存指标失败: {e}")
    
    def _optimize_cache_entry(self, entry: UnifiedCacheEntry) -> UnifiedCacheEntry:
        """优化缓存条目，减少存储大小"""
        try:
            # 创建优化后的条目副本
            optimized = UnifiedCacheEntry(
                key=entry.key,
                value=self._compress_cache_value(entry.value),
                cache_type=entry.cache_type,
                cache_level=entry.cache_level,
                created_at=entry.created_at,
                expires_at=entry.expires_at,
                ttl_seconds=entry.ttl_seconds,
                confidence=entry.confidence,
                reliability=entry.reliability,
                dependencies=set(),  # 清空依赖关系以减少大小
                tags=entry.tags,
                metadata=self._compress_metadata(entry.metadata),
                metrics=CacheMetrics()  # 使用默认指标以减少大小
            )
            
            return optimized
            
        except Exception as e:
            logger.warning(f"缓存条目优化失败: {e}")
            return entry
    
    def _compress_cache_value(self, value: Any) -> Any:
        """压缩缓存值，移除不必要的数据"""
        try:
            if isinstance(value, dict):
                # 只保留必要的字段
                compressed = {}
                essential_fields = ['value', 'formatted_value', 'success', 'confidence']
                
                for field in essential_fields:
                    if field in value:
                        compressed[field] = value[field]
                
                # 如果raw_data太大，只保留摘要
                if 'raw_data' in value:
                    raw_data = value['raw_data']
                    if isinstance(raw_data, list) and len(raw_data) > 10:
                        # 大列表只保留前3个和后2个元素
                        compressed['raw_data'] = raw_data[:3] + ['... (省略 {} 条记录)'.format(len(raw_data) - 5)] + raw_data[-2:]
                    elif isinstance(raw_data, str) and len(raw_data) > 1000:
                        # 长字符串截断
                        compressed['raw_data'] = raw_data[:500] + '... (截断)'
                    else:
                        compressed['raw_data'] = raw_data
                
                return compressed
            
            elif isinstance(value, str) and len(value) > 2000:
                # 长字符串截断
                return value[:1000] + '... (截断)'
            
            return value
            
        except Exception as e:
            logger.warning(f"缓存值压缩失败: {e}")
            return value
    
    def _compress_metadata(self, metadata: dict) -> dict:
        """压缩元数据"""
        try:
            # 只保留重要的元数据字段
            essential_fields = [
                'placeholder_id', 'placeholder_name', 'placeholder_type',
                'execution_source', 'sql_query'
            ]
            
            compressed = {}
            for field in essential_fields:
                if field in metadata:
                    value = metadata[field]
                    # SQL查询截断以节省空间
                    if field == 'sql_query' and isinstance(value, str) and len(value) > 200:
                        compressed[field] = value[:200] + '... (截断)'
                    else:
                        compressed[field] = value
            
            return compressed
            
        except Exception as e:
            logger.warning(f"元数据压缩失败: {e}")
            return metadata


class DatabaseCache(CacheInterface):
    """数据库缓存实现"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def get(self, key: str) -> Optional[UnifiedCacheEntry]:
        """获取缓存"""
        # 这里需要实现数据库查询逻辑
        # 由于需要创建数据库模型，暂时返回None
        logger.debug(f"数据库缓存获取: {key}")
        return None
    
    async def set(self, entry: UnifiedCacheEntry) -> bool:
        """设置缓存"""
        # 这里需要实现数据库插入逻辑
        logger.debug(f"数据库缓存设置: {entry.key}")
        return True
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        logger.debug(f"数据库缓存删除: {key}")
        return True
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        return False
    
    async def clear(self) -> bool:
        """清空缓存"""
        return True


class UnifiedCacheManager:
    """统一缓存管理器"""
    
    def __init__(
        self, 
        enable_memory: bool = True,
        enable_redis: bool = True,
        enable_database: bool = True,
        redis_client: Optional[redis.Redis] = None,
        db_session: Optional[Session] = None
    ):
        self.caches: Dict[CacheLevel, CacheInterface] = {}
        
        if enable_memory:
            self.caches[CacheLevel.MEMORY] = MemoryCache()
        
        if enable_redis and redis_client:
            self.caches[CacheLevel.REDIS] = RedisCache(redis_client)
        
        if enable_database and db_session:
            self.caches[CacheLevel.DATABASE] = DatabaseCache(db_session)
        
        self.default_strategy = CacheStrategy.LRU
        self.stats = {
            "total_gets": 0,
            "total_sets": 0,
            "total_hits": 0,
            "total_misses": 0
        }
    
    async def get(self, key: str, preferred_level: Optional[CacheLevel] = None) -> Optional[UnifiedCacheEntry]:
        """获取缓存，支持级联查找"""
        self.stats["total_gets"] += 1
        
        # 确定查找顺序
        search_order = self._get_search_order(preferred_level)
        
        for level in search_order:
            if level not in self.caches:
                continue
            
            cache = self.caches[level]
            entry = await cache.get(key)
            
            if entry and entry.is_valid:
                self.stats["total_hits"] += 1
                
                # 如果在较慢的层级找到，提升到更快的层级
                await self._promote_entry(entry, level)
                
                return entry
        
        self.stats["total_misses"] += 1
        return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        cache_type: CacheType,
        cache_level: CacheLevel = CacheLevel.MEMORY,
        ttl_seconds: int = 3600,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """设置缓存"""
        self.stats["total_sets"] += 1
        
        entry = UnifiedCacheEntry(
            key=key,
            value=value,
            cache_type=cache_type,
            cache_level=cache_level,
            ttl_seconds=ttl_seconds,
            confidence=confidence,
            metadata=metadata or {},
            tags=tags or set()
        )
        
        # 设置到指定层级
        if cache_level in self.caches:
            success = await self.caches[cache_level].set(entry)
            
            # 如果设置成功，也考虑设置到更快的层级
            if success and cache_level != CacheLevel.MEMORY:
                await self._promote_entry(entry, cache_level)
            
            return success
        
        return False
    
    async def delete(self, key: str, all_levels: bool = True) -> bool:
        """删除缓存"""
        if all_levels:
            success = True
            for cache in self.caches.values():
                result = await cache.delete(key)
                success = success and result
            return success
        else:
            # 删除所有层级中的第一个找到的
            for cache in self.caches.values():
                if await cache.exists(key):
                    return await cache.delete(key)
            return True
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在（任一层级）"""
        for cache in self.caches.values():
            if await cache.exists(key):
                return True
        return False
    
    async def invalidate_by_tags(self, tags: Set[str]) -> int:
        """根据标签批量失效缓存"""
        # 这需要遍历所有缓存条目，在实际实现中可能需要优化
        invalidated_count = 0
        # 简化实现，实际需要更复杂的逻辑
        return invalidated_count
    
    async def invalidate_by_dependencies(self, dependency_key: str) -> int:
        """根据依赖关系失效缓存"""
        # 这需要查找所有依赖于指定key的缓存条目
        invalidated_count = 0
        # 简化实现，实际需要更复杂的逻辑
        return invalidated_count
    
    async def cleanup_expired(self) -> int:
        """清理过期缓存"""
        cleaned_count = 0
        
        try:
            # 清理各个层级的过期缓存
            for level, cache in self.caches.items():
                if hasattr(cache, 'cleanup_expired_keys'):
                    # Redis缓存的清理
                    count = await cache.cleanup_expired_keys()
                    cleaned_count += count
                    logger.info(f"清理了 {level.value} 缓存中的 {count} 个过期条目")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")
            return 0
    
    async def check_memory_usage(self) -> Dict[str, Any]:
        """检查缓存内存使用情况"""
        try:
            memory_info = {}
            
            # 检查Redis内存使用
            if CacheLevel.REDIS in self.caches:
                redis_cache = self.caches[CacheLevel.REDIS]
                if hasattr(redis_cache, 'redis_client') and redis_cache.redis_client:
                    try:
                        info = redis_cache.redis_client.info('memory')
                        memory_info['redis'] = {
                            'used_memory_human': info.get('used_memory_human'),
                            'used_memory_peak_human': info.get('used_memory_peak_human'),
                            'maxmemory_human': info.get('maxmemory_human'),
                            'used_memory_percent': round(info.get('used_memory', 0) / max(info.get('maxmemory', 1), 1) * 100, 2)
                        }
                    except Exception as e:
                        memory_info['redis'] = {'error': str(e)}
            
            # 内存缓存大小
            if CacheLevel.MEMORY in self.caches:
                memory_cache = self.caches[CacheLevel.MEMORY]
                if hasattr(memory_cache, 'cache'):
                    memory_info['memory'] = {
                        'entry_count': len(memory_cache.cache),
                        'max_size': getattr(memory_cache, 'max_size', 'unknown')
                    }
            
            return memory_info
            
        except Exception as e:
            logger.error(f"检查内存使用失败: {e}")
            return {'error': str(e)}
    
    async def auto_cleanup_if_needed(self) -> Dict[str, Any]:
        """当内存使用过高时自动清理"""
        try:
            memory_info = await self.check_memory_usage()
            cleanup_result = {'cleaned': False, 'reason': 'not_needed'}
            
            # 检查Redis内存使用率
            if 'redis' in memory_info and 'used_memory_percent' in memory_info['redis']:
                usage_percent = memory_info['redis']['used_memory_percent']
                
                if usage_percent > 80:  # 超过80%使用率时清理
                    logger.warning(f"Redis内存使用率过高: {usage_percent}%，开始自动清理")
                    
                    # 清理过期缓存
                    expired_count = await self.cleanup_expired()
                    
                    cleanup_result = {
                        'cleaned': True,
                        'reason': f'high_memory_usage_{usage_percent}%',
                        'expired_cleaned': expired_count
                    }
                    
                    logger.info(f"自动清理完成: 清理了 {expired_count} 个过期条目")
            
            return cleanup_result
            
        except Exception as e:
            logger.error(f"自动清理检查失败: {e}")
            return {'error': str(e)}
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        hit_rate = 0.0
        total_requests = self.stats["total_hits"] + self.stats["total_misses"]
        if total_requests > 0:
            hit_rate = self.stats["total_hits"] / total_requests
        
        return {
            "total_gets": self.stats["total_gets"],
            "total_sets": self.stats["total_sets"],
            "total_hits": self.stats["total_hits"],
            "total_misses": self.stats["total_misses"],
            "hit_rate": hit_rate,
            "enabled_levels": list(self.caches.keys()),
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_search_order(self, preferred_level: Optional[CacheLevel]) -> List[CacheLevel]:
        """获取缓存查找顺序"""
        if preferred_level and preferred_level in self.caches:
            # 从指定层级开始，然后是其他层级
            order = [preferred_level]
            for level in [CacheLevel.MEMORY, CacheLevel.REDIS, CacheLevel.DATABASE]:
                if level != preferred_level and level in self.caches:
                    order.append(level)
            return order
        else:
            # 默认顺序：内存 -> Redis -> 数据库
            return [level for level in [CacheLevel.MEMORY, CacheLevel.REDIS, CacheLevel.DATABASE] 
                   if level in self.caches]
    
    async def _promote_entry(self, entry: UnifiedCacheEntry, current_level: CacheLevel):
        """将缓存条目提升到更快的层级"""
        if current_level == CacheLevel.DATABASE and CacheLevel.REDIS in self.caches:
            # 从数据库提升到Redis
            entry.cache_level = CacheLevel.REDIS
            await self.caches[CacheLevel.REDIS].set(entry)
        
        if current_level in [CacheLevel.DATABASE, CacheLevel.REDIS] and CacheLevel.MEMORY in self.caches:
            # 提升到内存
            entry.cache_level = CacheLevel.MEMORY
            await self.caches[CacheLevel.MEMORY].set(entry)


# 全局缓存管理器实例
_global_cache_manager: Optional[UnifiedCacheManager] = None


def get_cache_manager() -> Optional[UnifiedCacheManager]:
    """获取全局缓存管理器"""
    return _global_cache_manager


def initialize_cache_manager(
    enable_memory: bool = True,
    enable_redis: bool = True,
    enable_database: bool = True,
    redis_client: Optional[redis.Redis] = None,
    db_session: Optional[Session] = None
) -> UnifiedCacheManager:
    """初始化全局缓存管理器"""
    global _global_cache_manager
    _global_cache_manager = UnifiedCacheManager(
        enable_memory=enable_memory,
        enable_redis=enable_redis,
        enable_database=enable_database,
        redis_client=redis_client,
        db_session=db_session
    )
    return _global_cache_manager


# 便捷函数
async def cache_get(key: str, cache_type: Optional[CacheType] = None) -> Optional[Any]:
    """便捷的缓存获取函数"""
    manager = get_cache_manager()
    if not manager:
        return None
    
    entry = await manager.get(key)
    return entry.value if entry else None


async def cache_set(
    key: str, 
    value: Any, 
    cache_type: CacheType = CacheType.PLACEHOLDER_RESULT,
    ttl_seconds: int = 3600,
    cache_level: CacheLevel = CacheLevel.MEMORY
) -> bool:
    """便捷的缓存设置函数"""
    manager = get_cache_manager()
    if not manager:
        return False
    
    return await manager.set(key, value, cache_type, cache_level, ttl_seconds)


async def cache_delete(key: str) -> bool:
    """便捷的缓存删除函数"""
    manager = get_cache_manager()
    if not manager:
        return False
    
    return await manager.delete(key)