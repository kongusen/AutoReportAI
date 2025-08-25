"""
智能缓存管理器 - 优化占位符缓存策略

基于使用模式、数据特征和业务场景的智能缓存管理
"""

import logging
import asyncio
import hashlib
import json
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import redis
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """缓存层级"""
    MEMORY = "memory"           # 内存缓存（最快）
    REDIS = "redis"            # Redis缓存（中等速度）
    DATABASE = "database"      # 数据库缓存（持久化）


class CacheStrategy(Enum):
    """缓存策略"""
    HOT_DATA = "hot_data"             # 热数据 - 频繁访问
    WARM_DATA = "warm_data"           # 温数据 - 定期访问
    COLD_DATA = "cold_data"           # 冷数据 - 很少访问
    PREDICTIVE = "predictive"         # 预测性缓存
    CONTEXTUAL = "contextual"         # 上下文相关缓存


@dataclass
class CacheMetrics:
    """缓存指标"""
    hit_count: int = 0
    miss_count: int = 0
    last_hit: Optional[datetime] = None
    last_miss: Optional[datetime] = None
    avg_access_time: float = 0.0
    data_size: int = 0
    creation_time: datetime = field(default_factory=datetime.now)
    ttl_seconds: int = 3600
    
    @property
    def hit_rate(self) -> float:
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0
    
    def record_hit(self, access_time: float = 0.0):
        """记录缓存命中"""
        self.hit_count += 1
        self.last_hit = datetime.now()
        if access_time > 0:
            self.avg_access_time = (self.avg_access_time + access_time) / 2
    
    def record_miss(self):
        """记录缓存失效"""
        self.miss_count += 1
        self.last_miss = datetime.now()


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    cache_level: CacheLevel
    strategy: CacheStrategy
    metrics: CacheMetrics
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: Set[str] = field(default_factory=set)  # 依赖的其他缓存键
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        age = (datetime.now() - self.metrics.creation_time).total_seconds()
        return age > self.metrics.ttl_seconds
    
    @property
    def priority_score(self) -> float:
        """计算优先级分数"""
        # 基于命中率、访问频率和最后访问时间计算
        hit_rate_score = self.metrics.hit_rate * 40
        
        frequency_score = min(self.metrics.hit_count * 2, 30)
        
        if self.metrics.last_hit:
            hours_since_last_hit = (datetime.now() - self.metrics.last_hit).total_seconds() / 3600
            recency_score = max(0, 30 - hours_since_last_hit * 2)
        else:
            recency_score = 0
        
        return hit_rate_score + frequency_score + recency_score


class IntelligentCacheManager:
    """智能缓存管理器"""
    
    def __init__(self, 
                 redis_client: Optional[redis.Redis] = None,
                 db_session: Optional[Session] = None,
                 max_memory_entries: int = 1000,
                 max_memory_size_mb: int = 100):
        
        self.redis_client = redis_client
        self.db_session = db_session
        self.max_memory_entries = max_memory_entries
        self.max_memory_size_mb = max_memory_size_mb * 1024 * 1024  # 转换为字节
        
        # 三级缓存存储
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.cache_metrics: Dict[str, CacheMetrics] = {}
        
        # 使用模式分析
        self.access_patterns: Dict[str, List[datetime]] = defaultdict(list)
        self.context_associations: Dict[str, Set[str]] = defaultdict(set)
        
        # 预测性缓存
        self.prediction_rules: List[callable] = []
        
        logger.info("IntelligentCacheManager initialized")
    
    async def get(self, 
                 key: str, 
                 context: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """智能获取缓存数据"""
        start_time = datetime.now()
        
        try:
            # 1. 内存缓存查找
            memory_result = await self._get_from_memory(key)
            if memory_result is not None:
                self._record_access(key, context)
                access_time = (datetime.now() - start_time).total_seconds()
                self.memory_cache[key].metrics.record_hit(access_time)
                return memory_result
            
            # 2. Redis缓存查找
            if self.redis_client:
                redis_result = await self._get_from_redis(key)
                if redis_result is not None:
                    # 提升到内存缓存
                    await self._promote_to_memory(key, redis_result, context)
                    self._record_access(key, context)
                    return redis_result
            
            # 3. 数据库缓存查找
            if self.db_session:
                db_result = await self._get_from_database(key)
                if db_result is not None:
                    # 提升到上级缓存
                    await self._promote_to_redis(key, db_result, context)
                    self._record_access(key, context)
                    return db_result
            
            # 缓存未命中
            self._record_miss(key)
            return None
            
        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            return None
    
    async def set(self, 
                 key: str, 
                 value: Any, 
                 ttl_seconds: Optional[int] = None,
                 strategy: CacheStrategy = CacheStrategy.WARM_DATA,
                 context: Optional[Dict[str, Any]] = None,
                 dependencies: Optional[Set[str]] = None) -> bool:
        """智能设置缓存数据"""
        try:
            # 智能选择缓存层级
            cache_level = await self._determine_cache_level(key, value, strategy, context)
            
            # 创建缓存条目
            cache_entry = CacheEntry(
                key=key,
                value=value,
                cache_level=cache_level,
                strategy=strategy,
                metrics=CacheMetrics(
                    ttl_seconds=ttl_seconds or self._calculate_ttl(strategy, context),
                    data_size=len(json.dumps(value, default=str).encode('utf-8'))
                ),
                metadata=context or {},
                dependencies=dependencies or set()
            )
            
            # 存储到相应层级
            success = False
            if cache_level == CacheLevel.MEMORY:
                success = await self._set_to_memory(key, cache_entry)
            elif cache_level == CacheLevel.REDIS:
                success = await self._set_to_redis(key, cache_entry)
            elif cache_level == CacheLevel.DATABASE:
                success = await self._set_to_database(key, cache_entry)
            
            if success:
                self._update_context_associations(key, context)
                await self._trigger_predictive_caching(key, context)
            
            return success
            
        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            return False
    
    async def invalidate(self, 
                        key: str, 
                        cascade: bool = True) -> bool:
        """智能缓存失效"""
        try:
            # 从所有层级删除
            await self._delete_from_memory(key)
            if self.redis_client:
                await self._delete_from_redis(key)
            if self.db_session:
                await self._delete_from_database(key)
            
            # 级联失效相关缓存
            if cascade:
                await self._cascade_invalidate(key)
            
            # 清理访问模式记录
            if key in self.access_patterns:
                del self.access_patterns[key]
            
            return True
            
        except Exception as e:
            logger.error(f"Cache invalidation failed for key {key}: {e}")
            return False
    
    async def optimize_cache(self) -> Dict[str, Any]:
        """缓存优化"""
        try:
            optimization_stats = {
                'memory_optimized': 0,
                'redis_optimized': 0,
                'expired_cleaned': 0,
                'predictions_generated': 0
            }
            
            # 1. 内存缓存优化
            memory_stats = await self._optimize_memory_cache()
            optimization_stats.update(memory_stats)
            
            # 2. 清理过期缓存
            expired_stats = await self._cleanup_expired_cache()
            optimization_stats['expired_cleaned'] = expired_stats
            
            # 3. 生成预测性缓存
            prediction_stats = await self._generate_predictive_cache()
            optimization_stats['predictions_generated'] = prediction_stats
            
            # 4. 更新缓存策略
            await self._update_cache_strategies()
            
            logger.info(f"Cache optimization completed: {optimization_stats}")
            return optimization_stats
            
        except Exception as e:
            logger.error(f"Cache optimization failed: {e}")
            return {}
    
    def register_prediction_rule(self, rule: callable):
        """注册预测规则"""
        self.prediction_rules.append(rule)
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        memory_size = sum(entry.metrics.data_size for entry in self.memory_cache.values())
        
        total_hits = sum(metrics.hit_count for metrics in self.cache_metrics.values())
        total_misses = sum(metrics.miss_count for metrics in self.cache_metrics.values())
        overall_hit_rate = total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0
        
        return {
            'memory_entries': len(self.memory_cache),
            'memory_size_mb': memory_size / (1024 * 1024),
            'total_keys': len(self.cache_metrics),
            'overall_hit_rate': overall_hit_rate,
            'hot_data_keys': len([k for k, e in self.memory_cache.items() if e.strategy == CacheStrategy.HOT_DATA]),
            'predictive_keys': len([k for k, e in self.memory_cache.items() if e.strategy == CacheStrategy.PREDICTIVE]),
            'access_patterns': len(self.access_patterns)
        }
    
    # 私有方法
    
    async def _get_from_memory(self, key: str) -> Optional[Any]:
        """从内存缓存获取"""
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            if not entry.is_expired:
                return entry.value
            else:
                # 过期则删除
                del self.memory_cache[key]
        return None
    
    async def _get_from_redis(self, key: str) -> Optional[Any]:
        """从Redis缓存获取"""
        if not self.redis_client:
            return None
        
        try:
            cached_data = await self.redis_client.get(f"cache:{key}")
            if cached_data:
                return json.loads(cached_data.decode('utf-8'))
        except Exception as e:
            logger.warning(f"Redis get failed for {key}: {e}")
        
        return None
    
    async def _get_from_database(self, key: str) -> Optional[Any]:
        """从数据库缓存获取"""
        if not self.db_session:
            return None
        
        # 这里可以实现数据库缓存查询
        # 为简化示例，暂时返回None
        return None
    
    async def _set_to_memory(self, key: str, cache_entry: CacheEntry) -> bool:
        """存储到内存缓存"""
        # 检查内存限制
        await self._ensure_memory_capacity(cache_entry.metrics.data_size)
        
        self.memory_cache[key] = cache_entry
        if key not in self.cache_metrics:
            self.cache_metrics[key] = CacheMetrics()
        
        return True
    
    async def _set_to_redis(self, key: str, cache_entry: CacheEntry) -> bool:
        """存储到Redis缓存"""
        if not self.redis_client:
            return False
        
        try:
            serialized_value = json.dumps(cache_entry.value, default=str)
            await self.redis_client.setex(
                f"cache:{key}",
                cache_entry.metrics.ttl_seconds,
                serialized_value
            )
            return True
        except Exception as e:
            logger.error(f"Redis set failed for {key}: {e}")
            return False
    
    async def _set_to_database(self, key: str, cache_entry: CacheEntry) -> bool:
        """存储到数据库缓存"""
        # 数据库缓存实现
        return True
    
    async def _determine_cache_level(self, 
                                   key: str, 
                                   value: Any, 
                                   strategy: CacheStrategy,
                                   context: Optional[Dict[str, Any]]) -> CacheLevel:
        """智能确定缓存层级"""
        
        # 根据策略选择层级
        if strategy == CacheStrategy.HOT_DATA:
            return CacheLevel.MEMORY
        elif strategy == CacheStrategy.PREDICTIVE:
            return CacheLevel.MEMORY
        elif strategy == CacheStrategy.WARM_DATA:
            # 检查访问频率
            if key in self.access_patterns and len(self.access_patterns[key]) > 5:
                return CacheLevel.MEMORY
            else:
                return CacheLevel.REDIS if self.redis_client else CacheLevel.DATABASE
        else:  # COLD_DATA
            return CacheLevel.DATABASE if self.db_session else CacheLevel.REDIS
    
    def _calculate_ttl(self, 
                      strategy: CacheStrategy, 
                      context: Optional[Dict[str, Any]]) -> int:
        """计算TTL"""
        base_ttl = {
            CacheStrategy.HOT_DATA: 300,      # 5分钟
            CacheStrategy.WARM_DATA: 1800,    # 30分钟
            CacheStrategy.COLD_DATA: 3600,    # 1小时
            CacheStrategy.PREDICTIVE: 1800,   # 30分钟
            CacheStrategy.CONTEXTUAL: 900     # 15分钟
        }.get(strategy, 1800)
        
        # 根据上下文调整TTL
        if context:
            # 如果是模板相关，TTL可以更长
            if context.get('template_id'):
                base_ttl *= 2
            # 如果是任务执行相关，TTL相对较短
            elif context.get('task_id'):
                base_ttl = max(300, base_ttl // 2)
        
        return base_ttl
    
    async def _ensure_memory_capacity(self, required_size: int):
        """确保内存容量"""
        # 检查条目数量限制
        if len(self.memory_cache) >= self.max_memory_entries:
            await self._evict_memory_entries(max(1, self.max_memory_entries // 10))
        
        # 检查内存大小限制
        current_size = sum(entry.metrics.data_size for entry in self.memory_cache.values())
        if current_size + required_size > self.max_memory_size_mb:
            await self._evict_memory_entries_by_size(required_size)
    
    async def _evict_memory_entries(self, count: int):
        """按优先级驱逐内存条目"""
        if len(self.memory_cache) <= count:
            return
        
        # 按优先级排序（优先级低的先驱逐）
        entries_by_priority = sorted(
            self.memory_cache.items(),
            key=lambda x: x[1].priority_score
        )
        
        for i in range(count):
            key, entry = entries_by_priority[i]
            
            # 降级到Redis或数据库
            if entry.cache_level == CacheLevel.MEMORY:
                if self.redis_client:
                    await self._demote_to_redis(key, entry)
                
            del self.memory_cache[key]
    
    async def _evict_memory_entries_by_size(self, required_size: int):
        """按大小驱逐内存条目"""
        freed_size = 0
        entries_by_size = sorted(
            self.memory_cache.items(),
            key=lambda x: x[1].metrics.data_size,
            reverse=True
        )
        
        for key, entry in entries_by_size:
            if freed_size >= required_size:
                break
            
            freed_size += entry.metrics.data_size
            
            # 降级处理
            if self.redis_client:
                await self._demote_to_redis(key, entry)
            
            del self.memory_cache[key]
    
    def _record_access(self, key: str, context: Optional[Dict[str, Any]]):
        """记录访问"""
        now = datetime.now()
        
        # 记录访问时间
        if key not in self.access_patterns:
            self.access_patterns[key] = []
        self.access_patterns[key].append(now)
        
        # 保留最近50次访问记录
        self.access_patterns[key] = self.access_patterns[key][-50:]
        
        # 更新上下文关联
        if context:
            self._update_context_associations(key, context)
    
    def _record_miss(self, key: str):
        """记录缓存失效"""
        if key not in self.cache_metrics:
            self.cache_metrics[key] = CacheMetrics()
        self.cache_metrics[key].record_miss()
    
    def _update_context_associations(self, key: str, context: Optional[Dict[str, Any]]):
        """更新上下文关联"""
        if not context:
            return
        
        # 记录与template_id的关联
        if 'template_id' in context:
            self.context_associations[f"template:{context['template_id']}"].add(key)
        
        # 记录与data_source_id的关联
        if 'data_source_id' in context:
            self.context_associations[f"datasource:{context['data_source_id']}"].add(key)
        
        # 记录与user_id的关联
        if 'user_id' in context:
            self.context_associations[f"user:{context['user_id']}"].add(key)
    
    async def _cascade_invalidate(self, key: str):
        """级联失效相关缓存"""
        # 查找依赖此key的其他缓存
        dependent_keys = []
        for cache_key, entry in self.memory_cache.items():
            if key in entry.dependencies:
                dependent_keys.append(cache_key)
        
        # 递归失效
        for dep_key in dependent_keys:
            await self.invalidate(dep_key, cascade=False)
    
    async def _optimize_memory_cache(self) -> Dict[str, int]:
        """优化内存缓存"""
        stats = {'promoted': 0, 'demoted': 0}
        
        for key, entry in list(self.memory_cache.items()):
            # 根据访问模式调整策略
            if key in self.access_patterns:
                recent_accesses = [
                    t for t in self.access_patterns[key]
                    if (datetime.now() - t).total_seconds() < 3600  # 最近1小时
                ]
                
                if len(recent_accesses) >= 5 and entry.strategy != CacheStrategy.HOT_DATA:
                    # 提升为热数据
                    entry.strategy = CacheStrategy.HOT_DATA
                    entry.metrics.ttl_seconds = 300
                    stats['promoted'] += 1
                elif len(recent_accesses) == 0 and entry.strategy == CacheStrategy.HOT_DATA:
                    # 降级为温数据
                    entry.strategy = CacheStrategy.WARM_DATA
                    entry.metrics.ttl_seconds = 1800
                    stats['demoted'] += 1
        
        return stats
    
    async def _cleanup_expired_cache(self) -> int:
        """清理过期缓存"""
        expired_count = 0
        expired_keys = []
        
        for key, entry in self.memory_cache.items():
            if entry.is_expired:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.memory_cache[key]
            expired_count += 1
        
        return expired_count
    
    async def _generate_predictive_cache(self) -> int:
        """生成预测性缓存"""
        prediction_count = 0
        
        for rule in self.prediction_rules:
            try:
                predictions = rule(self.access_patterns, self.context_associations)
                for prediction in predictions:
                    # 这里可以预加载预测的数据
                    prediction_count += 1
            except Exception as e:
                logger.warning(f"Prediction rule failed: {e}")
        
        return prediction_count
    
    async def _update_cache_strategies(self):
        """更新缓存策略"""
        # 基于访问模式动态调整缓存策略
        for key, access_times in self.access_patterns.items():
            if len(access_times) < 2:
                continue
            
            # 计算访问频率
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                
                # 计算最近访问频率
                recent_accesses = [
                    t for t in access_times
                    if (datetime.now() - t).total_seconds() < 7200  # 最近2小时
                ]
                
                if len(recent_accesses) >= 3:
                    entry.strategy = CacheStrategy.HOT_DATA
                elif len(recent_accesses) >= 1:
                    entry.strategy = CacheStrategy.WARM_DATA
                else:
                    entry.strategy = CacheStrategy.COLD_DATA
    
    async def _promote_to_memory(self, key: str, value: Any, context: Optional[Dict[str, Any]]):
        """提升到内存缓存"""
        cache_entry = CacheEntry(
            key=key,
            value=value,
            cache_level=CacheLevel.MEMORY,
            strategy=CacheStrategy.WARM_DATA,
            metrics=CacheMetrics(data_size=len(json.dumps(value, default=str).encode('utf-8')))
        )
        await self._set_to_memory(key, cache_entry)
    
    async def _promote_to_redis(self, key: str, value: Any, context: Optional[Dict[str, Any]]):
        """提升到Redis缓存"""
        cache_entry = CacheEntry(
            key=key,
            value=value,
            cache_level=CacheLevel.REDIS,
            strategy=CacheStrategy.WARM_DATA,
            metrics=CacheMetrics(data_size=len(json.dumps(value, default=str).encode('utf-8')))
        )
        await self._set_to_redis(key, cache_entry)
    
    async def _demote_to_redis(self, key: str, entry: CacheEntry):
        """降级到Redis缓存"""
        entry.cache_level = CacheLevel.REDIS
        await self._set_to_redis(key, entry)
    
    async def _delete_from_memory(self, key: str):
        """从内存删除"""
        if key in self.memory_cache:
            del self.memory_cache[key]
    
    async def _delete_from_redis(self, key: str):
        """从Redis删除"""
        if self.redis_client:
            await self.redis_client.delete(f"cache:{key}")
    
    async def _delete_from_database(self, key: str):
        """从数据库删除"""
        # 数据库删除实现
        pass
    
    async def _trigger_predictive_caching(self, key: str, context: Optional[Dict[str, Any]]):
        """触发预测性缓存"""
        if not context:
            return
        
        # 基于上下文预测相关缓存需求
        predictions = []
        
        # 如果是模板相关的缓存，可能需要预加载其他占位符
        if 'template_id' in context:
            template_id = context['template_id']
            # 预测同一模板的其他占位符可能被访问
            predictions.append(f"template_placeholders:{template_id}")
        
        # 如果是数据源相关，可能需要预加载schema信息
        if 'data_source_id' in context:
            data_source_id = context['data_source_id']
            predictions.append(f"schema_cache:{data_source_id}")
        
        # 这里可以异步执行预测性缓存加载
        for prediction_key in predictions:
            asyncio.create_task(self._load_predictive_cache(prediction_key, context))
    
    async def _load_predictive_cache(self, key: str, context: Dict[str, Any]):
        """加载预测性缓存"""
        try:
            # 这里可以实现具体的预测性数据加载逻辑
            logger.debug(f"Loading predictive cache for: {key}")
        except Exception as e:
            logger.warning(f"Predictive cache loading failed for {key}: {e}")


# 便捷函数和预定义规则

def create_intelligent_cache_manager(redis_client: Optional[redis.Redis] = None,
                                   db_session: Optional[Session] = None) -> IntelligentCacheManager:
    """创建智能缓存管理器"""
    return IntelligentCacheManager(redis_client, db_session)


def template_access_prediction_rule(access_patterns: Dict[str, List[datetime]],
                                  context_associations: Dict[str, Set[str]]) -> List[str]:
    """模板访问预测规则"""
    predictions = []
    
    # 分析模板访问模式
    for context_key, cache_keys in context_associations.items():
        if context_key.startswith('template:') and len(cache_keys) > 1:
            template_id = context_key.split(':', 1)[1]
            
            # 如果模板的某些占位符被频繁访问，预测其他占位符也可能被访问
            recently_accessed = []
            for cache_key in cache_keys:
                if cache_key in access_patterns:
                    recent_accesses = [
                        t for t in access_patterns[cache_key]
                        if (datetime.now() - t).total_seconds() < 1800  # 最近30分钟
                    ]
                    if recent_accesses:
                        recently_accessed.append(cache_key)
            
            # 如果超过30%的占位符被最近访问，预测加载所有占位符
            if len(recently_accessed) >= max(1, len(cache_keys) * 0.3):
                for cache_key in cache_keys:
                    if cache_key not in recently_accessed:
                        predictions.append(cache_key)
    
    return predictions


def user_behavior_prediction_rule(access_patterns: Dict[str, List[datetime]],
                                context_associations: Dict[str, Set[str]]) -> List[str]:
    """用户行为预测规则"""
    predictions = []
    
    # 基于用户行为模式预测
    for context_key, cache_keys in context_associations.items():
        if context_key.startswith('user:'):
            user_id = context_key.split(':', 1)[1]
            
            # 分析用户的访问时间模式
            user_access_times = []
            for cache_key in cache_keys:
                if cache_key in access_patterns:
                    user_access_times.extend(access_patterns[cache_key])
            
            if len(user_access_times) > 10:
                # 分析访问时间的周期性
                current_hour = datetime.now().hour
                hourly_access_count = defaultdict(int)
                
                for access_time in user_access_times[-50:]:  # 最近50次访问
                    hourly_access_count[access_time.hour] += 1
                
                # 如果当前时间是用户的活跃时间，预测加载用户相关缓存
                if hourly_access_count[current_hour] >= 3:
                    predictions.extend(list(cache_keys))
    
    return predictions