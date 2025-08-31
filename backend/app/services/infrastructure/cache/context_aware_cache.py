"""
Context Aware Cache

上下文感知缓存系统，根据业务上下文和访问模式智能管理缓存
支持多维度上下文分析、预测性缓存、智能失效等功能
"""

import asyncio
import json
import logging
import pickle
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
import hashlib
import threading

from .unified_cache_system import CacheLevel, CacheStrategy, CacheType
from .memory_cache import MemoryCache
from ...llm_agents.monitoring.performance_monitor import get_performance_monitor, monitor_performance

logger = logging.getLogger(__name__)


class ContextType(Enum):
    """上下文类型"""
    USER_CONTEXT = "user"               # 用户上下文
    SESSION_CONTEXT = "session"         # 会话上下文
    TEMPLATE_CONTEXT = "template"       # 模板上下文
    DATA_SOURCE_CONTEXT = "data_source" # 数据源上下文
    TIME_CONTEXT = "time"               # 时间上下文
    BUSINESS_CONTEXT = "business"       # 业务上下文
    GEOGRAPHIC_CONTEXT = "geographic"   # 地理上下文


class AccessPattern(Enum):
    """访问模式"""
    SEQUENTIAL = "sequential"           # 顺序访问
    RANDOM = "random"                   # 随机访问
    BURST = "burst"                     # 突发访问
    PERIODIC = "periodic"               # 周期性访问
    TRENDING = "trending"               # 趋势性访问


class CacheAffinity(Enum):
    """缓存亲和性"""
    HIGH = "high"       # 高亲和性 - 长期缓存
    MEDIUM = "medium"   # 中等亲和性 - 中期缓存
    LOW = "low"         # 低亲和性 - 短期缓存
    NONE = "none"       # 无亲和性 - 不缓存


@dataclass
class ContextVector:
    """上下文向量"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    template_id: Optional[str] = None
    data_source_id: Optional[str] = None
    time_slot: Optional[str] = None      # 时间槽（如：morning, afternoon, evening）
    business_domain: Optional[str] = None
    geographic_region: Optional[str] = None
    device_type: Optional[str] = None
    language: Optional[str] = None
    
    def to_key(self) -> str:
        """转换为缓存键"""
        components = []
        for key, value in asdict(self).items():
            if value:
                components.append(f"{key}:{value}")
        return "|".join(components)
    
    def similarity(self, other: 'ContextVector') -> float:
        """计算与另一个上下文向量的相似度"""
        total_fields = 0
        matching_fields = 0
        
        for key in asdict(self).keys():
            self_value = getattr(self, key)
            other_value = getattr(other, key)
            
            if self_value is not None or other_value is not None:
                total_fields += 1
                if self_value == other_value:
                    matching_fields += 1
        
        return matching_fields / total_fields if total_fields > 0 else 0.0


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    context_vector: ContextVector
    cache_type: CacheType
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    access_pattern: AccessPattern = AccessPattern.RANDOM
    affinity: CacheAffinity = CacheAffinity.MEDIUM
    ttl_seconds: Optional[int] = None
    size_bytes: int = 0
    hit_rate: float = 0.0
    tags: Set[str] = field(default_factory=set)
    dependencies: Set[str] = field(default_factory=set)
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl_seconds is None:
            return False
        
        return (datetime.now() - self.created_at).total_seconds() > self.ttl_seconds
    
    def calculate_priority(self) -> float:
        """计算缓存优先级"""
        # 基于访问频率、最近访问时间、亲和性等计算优先级
        age_factor = max(0, 1 - (datetime.now() - self.last_accessed).total_seconds() / 3600)
        frequency_factor = min(1.0, self.access_count / 100)
        
        affinity_weights = {
            CacheAffinity.HIGH: 1.0,
            CacheAffinity.MEDIUM: 0.7,
            CacheAffinity.LOW: 0.3,
            CacheAffinity.NONE: 0.1
        }
        
        affinity_factor = affinity_weights.get(self.affinity, 0.5)
        hit_rate_factor = self.hit_rate
        
        return (age_factor * 0.3 + frequency_factor * 0.3 + 
                affinity_factor * 0.3 + hit_rate_factor * 0.1)


@dataclass
class ContextCluster:
    """上下文聚类"""
    cluster_id: str
    representative_context: ContextVector
    member_contexts: List[ContextVector] = field(default_factory=list)
    cache_entries: Set[str] = field(default_factory=set)
    access_patterns: Dict[AccessPattern, int] = field(default_factory=lambda: defaultdict(int))
    last_updated: datetime = field(default_factory=datetime.now)
    
    def add_context(self, context: ContextVector):
        """添加上下文到聚类"""
        self.member_contexts.append(context)
        self.last_updated = datetime.now()
    
    def get_dominant_pattern(self) -> AccessPattern:
        """获取主要访问模式"""
        if not self.access_patterns:
            return AccessPattern.RANDOM
        
        return max(self.access_patterns.items(), key=lambda x: x[1])[0]


class ContextAnalyzer:
    """上下文分析器"""
    
    def __init__(self):
        self.context_history: deque = deque(maxlen=10000)
        self.access_patterns: Dict[str, List[Tuple[datetime, AccessPattern]]] = defaultdict(list)
        self.context_clusters: Dict[str, ContextCluster] = {}
        self.similarity_threshold = 0.7
    
    def analyze_context(self, context: ContextVector, access_time: datetime = None) -> Dict[str, Any]:
        """分析上下文"""
        if access_time is None:
            access_time = datetime.now()
        
        # 记录上下文历史
        self.context_history.append((context, access_time))
        
        # 分析访问模式
        pattern = self._detect_access_pattern(context, access_time)
        
        # 计算缓存亲和性
        affinity = self._calculate_cache_affinity(context, pattern)
        
        # 预测相关上下文
        related_contexts = self._predict_related_contexts(context)
        
        # 聚类上下文
        cluster = self._cluster_context(context)
        
        return {
            "access_pattern": pattern,
            "cache_affinity": affinity,
            "related_contexts": related_contexts,
            "cluster_id": cluster.cluster_id if cluster else None,
            "similarity_score": self._calculate_context_similarity_score(context),
            "recommendation": self._generate_cache_recommendation(context, pattern, affinity)
        }
    
    def _detect_access_pattern(self, context: ContextVector, access_time: datetime) -> AccessPattern:
        """检测访问模式"""
        context_key = context.to_key()
        
        # 获取该上下文的历史访问时间
        recent_accesses = []
        for hist_context, hist_time in self.context_history:
            if hist_context.to_key() == context_key:
                recent_accesses.append(hist_time)
        
        if len(recent_accesses) < 2:
            return AccessPattern.RANDOM
        
        # 分析时间间隔
        intervals = []
        for i in range(1, len(recent_accesses)):
            interval = (recent_accesses[i] - recent_accesses[i-1]).total_seconds()
            intervals.append(interval)
        
        # 判断模式
        if len(intervals) >= 3:
            avg_interval = sum(intervals) / len(intervals)
            variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
            
            # 如果方差小，说明是周期性访问
            if variance < avg_interval * 0.1 and avg_interval > 60:  # 方差小且间隔大于1分钟
                return AccessPattern.PERIODIC
            
            # 如果访问很密集，说明是突发访问
            if avg_interval < 10:  # 平均间隔小于10秒
                return AccessPattern.BURST
        
        # 检查是否是顺序访问
        if self._is_sequential_access(context):
            return AccessPattern.SEQUENTIAL
        
        # 检查是否是趋势访问
        if self._is_trending_access(context_key):
            return AccessPattern.TRENDING
        
        return AccessPattern.RANDOM
    
    def _is_sequential_access(self, context: ContextVector) -> bool:
        """判断是否为顺序访问"""
        # 检查用户ID或会话ID是否连续
        if context.user_id and context.user_id.isdigit():
            user_num = int(context.user_id)
            # 检查最近是否有相邻用户ID的访问
            for hist_context, _ in list(self.context_history)[-10:]:
                if (hist_context.user_id and hist_context.user_id.isdigit() and 
                    abs(int(hist_context.user_id) - user_num) <= 2):
                    return True
        
        return False
    
    def _is_trending_access(self, context_key: str) -> bool:
        """判断是否为趋势访问"""
        # 统计最近一小时内该上下文的访问次数
        now = datetime.now()
        recent_count = 0
        
        for hist_context, hist_time in self.context_history:
            if hist_context.to_key() == context_key:
                if (now - hist_time).total_seconds() <= 3600:  # 1小时内
                    recent_count += 1
        
        # 如果最近访问频繁，认为是趋势访问
        return recent_count >= 5
    
    def _calculate_cache_affinity(self, context: ContextVector, pattern: AccessPattern) -> CacheAffinity:
        """计算缓存亲和性"""
        # 基于访问模式计算
        pattern_affinity = {
            AccessPattern.PERIODIC: CacheAffinity.HIGH,
            AccessPattern.TRENDING: CacheAffinity.HIGH,
            AccessPattern.BURST: CacheAffinity.MEDIUM,
            AccessPattern.SEQUENTIAL: CacheAffinity.MEDIUM,
            AccessPattern.RANDOM: CacheAffinity.LOW
        }
        
        base_affinity = pattern_affinity.get(pattern, CacheAffinity.LOW)
        
        # 基于上下文特征调整
        if context.template_id or context.data_source_id:
            # 模板或数据源相关的通常有较高亲和性
            if base_affinity == CacheAffinity.LOW:
                base_affinity = CacheAffinity.MEDIUM
            elif base_affinity == CacheAffinity.MEDIUM:
                base_affinity = CacheAffinity.HIGH
        
        return base_affinity
    
    def _predict_related_contexts(self, context: ContextVector) -> List[ContextVector]:
        """预测相关上下文"""
        related = []
        
        # 基于相似性查找相关上下文
        for hist_context, _ in self.context_history:
            similarity = context.similarity(hist_context)
            if similarity > self.similarity_threshold and similarity < 1.0:
                related.append(hist_context)
        
        # 去重并限制数量
        unique_related = []
        seen_keys = set()
        
        for rel_context in related:
            key = rel_context.to_key()
            if key not in seen_keys:
                unique_related.append(rel_context)
                seen_keys.add(key)
                
                if len(unique_related) >= 5:  # 最多返回5个相关上下文
                    break
        
        return unique_related
    
    def _cluster_context(self, context: ContextVector) -> Optional[ContextCluster]:
        """聚类上下文"""
        # 查找最相似的聚类
        best_cluster = None
        best_similarity = 0
        
        for cluster in self.context_clusters.values():
            similarity = context.similarity(cluster.representative_context)
            if similarity > best_similarity and similarity > self.similarity_threshold:
                best_similarity = similarity
                best_cluster = cluster
        
        if best_cluster:
            best_cluster.add_context(context)
            return best_cluster
        
        # 创建新聚类
        cluster_id = f"cluster_{len(self.context_clusters)}"
        new_cluster = ContextCluster(
            cluster_id=cluster_id,
            representative_context=context
        )
        new_cluster.add_context(context)
        self.context_clusters[cluster_id] = new_cluster
        
        return new_cluster
    
    def _calculate_context_similarity_score(self, context: ContextVector) -> float:
        """计算上下文相似性得分"""
        if not self.context_history:
            return 0.0
        
        similarities = []
        for hist_context, _ in list(self.context_history)[-50:]:  # 检查最近50个
            similarity = context.similarity(hist_context)
            similarities.append(similarity)
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _generate_cache_recommendation(
        self, 
        context: ContextVector, 
        pattern: AccessPattern, 
        affinity: CacheAffinity
    ) -> Dict[str, Any]:
        """生成缓存建议"""
        # TTL建议
        ttl_recommendations = {
            CacheAffinity.HIGH: 3600 * 24,     # 24小时
            CacheAffinity.MEDIUM: 3600 * 4,    # 4小时
            CacheAffinity.LOW: 3600,           # 1小时
            CacheAffinity.NONE: 300            # 5分钟
        }
        
        # 缓存层级建议
        level_recommendations = {
            AccessPattern.BURST: [CacheLevel.MEMORY, CacheLevel.REDIS],
            AccessPattern.PERIODIC: [CacheLevel.REDIS, CacheLevel.DATABASE],
            AccessPattern.TRENDING: [CacheLevel.MEMORY, CacheLevel.REDIS],
            AccessPattern.SEQUENTIAL: [CacheLevel.REDIS],
            AccessPattern.RANDOM: [CacheLevel.MEMORY]
        }
        
        # 预热建议
        should_prefetch = (
            pattern in [AccessPattern.PERIODIC, AccessPattern.TRENDING] and
            affinity in [CacheAffinity.HIGH, CacheAffinity.MEDIUM]
        )
        
        return {
            "ttl_seconds": ttl_recommendations.get(affinity, 3600),
            "recommended_levels": level_recommendations.get(pattern, [CacheLevel.MEMORY]),
            "should_prefetch": should_prefetch,
            "cache_strategy": CacheStrategy.INTELLIGENT,
            "priority_score": self._calculate_priority_score(pattern, affinity),
            "invalidation_strategy": self._recommend_invalidation_strategy(context, pattern)
        }
    
    def _calculate_priority_score(self, pattern: AccessPattern, affinity: CacheAffinity) -> float:
        """计算优先级得分"""
        pattern_scores = {
            AccessPattern.BURST: 0.9,
            AccessPattern.TRENDING: 0.8,
            AccessPattern.PERIODIC: 0.7,
            AccessPattern.SEQUENTIAL: 0.6,
            AccessPattern.RANDOM: 0.3
        }
        
        affinity_scores = {
            CacheAffinity.HIGH: 0.9,
            CacheAffinity.MEDIUM: 0.6,
            CacheAffinity.LOW: 0.3,
            CacheAffinity.NONE: 0.1
        }
        
        pattern_score = pattern_scores.get(pattern, 0.5)
        affinity_score = affinity_scores.get(affinity, 0.5)
        
        return (pattern_score + affinity_score) / 2
    
    def _recommend_invalidation_strategy(self, context: ContextVector, pattern: AccessPattern) -> str:
        """推荐失效策略"""
        if pattern == AccessPattern.PERIODIC:
            return "time_based"
        elif context.template_id or context.data_source_id:
            return "dependency_based"
        elif pattern == AccessPattern.BURST:
            return "lru_based"
        else:
            return "ttl_based"


class ContextAwareCache:
    """上下文感知缓存主类"""
    
    def __init__(self, max_memory_mb: int = 200):
        self.memory_cache = MemoryCache(max_size_mb=max_memory_mb)
        self.context_analyzer = ContextAnalyzer()
        self.performance_monitor = get_performance_monitor()
        
        # 缓存条目管理
        self.cache_entries: Dict[str, CacheEntry] = {}
        self.context_index: Dict[str, Set[str]] = defaultdict(set)  # 上下文 -> 缓存键集合
        self.tag_index: Dict[str, Set[str]] = defaultdict(set)      # 标签 -> 缓存键集合
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)  # 依赖关系图
        
        # 统计信息
        self.stats = {
            "hits": 0,
            "misses": 0,
            "context_predictions": 0,
            "prefetch_hits": 0,
            "invalidations": 0
        }
        
        # 预测性缓存
        self.prefetch_queue: deque = deque(maxlen=1000)
        self.prefetch_enabled = True
        
        # 异步任务
        self._background_tasks: List[asyncio.Task] = []
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """启动后台任务"""
        self._background_tasks = [
            asyncio.create_task(self._cleanup_expired_entries()),
            asyncio.create_task(self._prefetch_predicted_entries()),
            asyncio.create_task(self._optimize_cache_allocation())
        ]
    
    @monitor_performance("context_aware_cache", "get")
    async def get(
        self,
        key: str,
        context: ContextVector,
        cache_type: CacheType = CacheType.PLACEHOLDER_RESULT
    ) -> Optional[Any]:
        """
        获取缓存数据
        
        Args:
            key: 缓存键
            context: 上下文向量
            cache_type: 缓存类型
            
        Returns:
            缓存的数据或None
        """
        try:
            # 分析上下文
            context_analysis = self.context_analyzer.analyze_context(context)
            
            # 尝试直接获取
            if key in self.cache_entries:
                entry = self.cache_entries[key]
                
                # 检查是否过期
                if entry.is_expired():
                    await self._remove_entry(key)
                    self.stats["misses"] += 1
                    return None
                
                # 更新访问信息
                entry.last_accessed = datetime.now()
                entry.access_count += 1
                entry.access_pattern = context_analysis["access_pattern"]
                
                # 从内存缓存获取实际数据
                data = self.memory_cache.get(key)
                if data is not None:
                    self.stats["hits"] += 1
                    
                    # 触发预测性缓存
                    if self.prefetch_enabled:
                        await self._trigger_predictive_prefetch(context, context_analysis)
                    
                    return data
            
            # 尝试上下文相似性匹配
            similar_key = await self._find_similar_context_entry(context, cache_type)
            if similar_key:
                data = self.memory_cache.get(similar_key)
                if data is not None:
                    self.stats["context_predictions"] += 1
                    self.stats["hits"] += 1
                    return data
            
            self.stats["misses"] += 1
            return None
            
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            self.stats["misses"] += 1
            return None
    
    @monitor_performance("context_aware_cache", "set")
    async def set(
        self,
        key: str,
        value: Any,
        context: ContextVector,
        cache_type: CacheType = CacheType.PLACEHOLDER_RESULT,
        ttl_seconds: Optional[int] = None,
        tags: Optional[Set[str]] = None,
        dependencies: Optional[Set[str]] = None
    ) -> bool:
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            value: 要缓存的数据
            context: 上下文向量
            cache_type: 缓存类型
            ttl_seconds: 生存时间（秒）
            tags: 标签集合
            dependencies: 依赖关系
            
        Returns:
            操作是否成功
        """
        try:
            # 分析上下文并获取建议
            context_analysis = self.context_analyzer.analyze_context(context)
            recommendation = context_analysis["recommendation"]
            
            # 使用建议或用户指定的TTL
            effective_ttl = ttl_seconds or recommendation["ttl_seconds"]
            
            # 计算数据大小
            try:
                size_bytes = len(pickle.dumps(value))
            except:
                size_bytes = 0
            
            # 创建缓存条目
            entry = CacheEntry(
                key=key,
                value=value,
                context_vector=context,
                cache_type=cache_type,
                access_pattern=context_analysis["access_pattern"],
                affinity=context_analysis["cache_affinity"],
                ttl_seconds=effective_ttl,
                size_bytes=size_bytes,
                tags=tags or set(),
                dependencies=dependencies or set()
            )
            
            # 存储到内存缓存
            success = self.memory_cache.set(key, value, ttl_seconds=effective_ttl)
            if not success:
                # 内存不足，尝试清理低优先级条目
                await self._evict_low_priority_entries(size_bytes)
                success = self.memory_cache.set(key, value, ttl_seconds=effective_ttl)
            
            if success:
                # 更新索引
                self.cache_entries[key] = entry
                self.context_index[context.to_key()].add(key)
                
                for tag in entry.tags:
                    self.tag_index[tag].add(key)
                
                for dep in entry.dependencies:
                    self.dependency_graph[dep].add(key)
                
                logger.debug(f"缓存设置成功: {key}, 上下文: {context.to_key()}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
            return False
    
    async def _find_similar_context_entry(self, context: ContextVector, cache_type: CacheType) -> Optional[str]:
        """查找相似上下文的缓存条目"""
        best_key = None
        best_similarity = 0
        
        for key, entry in self.cache_entries.items():
            if entry.cache_type == cache_type and not entry.is_expired():
                similarity = context.similarity(entry.context_vector)
                if similarity > best_similarity and similarity > 0.8:  # 相似度阈值
                    best_similarity = similarity
                    best_key = key
        
        return best_key
    
    async def _trigger_predictive_prefetch(self, context: ContextVector, analysis: Dict[str, Any]):
        """触发预测性缓存"""
        if not analysis.get("should_prefetch", False):
            return
        
        # 获取相关上下文
        related_contexts = analysis.get("related_contexts", [])
        
        for related_context in related_contexts:
            # 将相关上下文加入预取队列
            self.prefetch_queue.append({
                "context": related_context,
                "trigger_time": datetime.now(),
                "priority": analysis["recommendation"]["priority_score"]
            })
    
    async def _evict_low_priority_entries(self, needed_size: int):
        """驱逐低优先级条目"""
        # 计算所有条目的优先级
        entry_priorities = []
        for key, entry in self.cache_entries.items():
            priority = entry.calculate_priority()
            entry_priorities.append((priority, key, entry.size_bytes))
        
        # 按优先级排序（低优先级在前）
        entry_priorities.sort(key=lambda x: x[0])
        
        freed_size = 0
        evicted_keys = []
        
        for priority, key, size in entry_priorities:
            if freed_size >= needed_size:
                break
            
            await self._remove_entry(key)
            evicted_keys.append(key)
            freed_size += size
        
        logger.info(f"驱逐了 {len(evicted_keys)} 个低优先级条目，释放 {freed_size} 字节")
    
    async def _remove_entry(self, key: str):
        """移除缓存条目"""
        if key in self.cache_entries:
            entry = self.cache_entries[key]
            
            # 从内存缓存移除
            self.memory_cache.delete(key)
            
            # 从索引中移除
            context_key = entry.context_vector.to_key()
            if context_key in self.context_index:
                self.context_index[context_key].discard(key)
                if not self.context_index[context_key]:
                    del self.context_index[context_key]
            
            for tag in entry.tags:
                self.tag_index[tag].discard(key)
                if not self.tag_index[tag]:
                    del self.tag_index[tag]
            
            for dep in entry.dependencies:
                self.dependency_graph[dep].discard(key)
                if not self.dependency_graph[dep]:
                    del self.dependency_graph[dep]
            
            del self.cache_entries[key]
    
    async def invalidate_by_tags(self, tags: Set[str]) -> int:
        """根据标签失效缓存"""
        invalidated_keys = set()
        
        for tag in tags:
            if tag in self.tag_index:
                invalidated_keys.update(self.tag_index[tag])
        
        for key in invalidated_keys:
            await self._remove_entry(key)
        
        count = len(invalidated_keys)
        self.stats["invalidations"] += count
        logger.info(f"根据标签失效了 {count} 个缓存条目")
        
        return count
    
    async def invalidate_by_dependencies(self, dependencies: Set[str]) -> int:
        """根据依赖关系失效缓存"""
        invalidated_keys = set()
        
        for dep in dependencies:
            if dep in self.dependency_graph:
                invalidated_keys.update(self.dependency_graph[dep])
        
        for key in invalidated_keys:
            await self._remove_entry(key)
        
        count = len(invalidated_keys)
        self.stats["invalidations"] += count
        logger.info(f"根据依赖关系失效了 {count} 个缓存条目")
        
        return count
    
    async def _cleanup_expired_entries(self):
        """清理过期条目的后台任务"""
        while True:
            try:
                expired_keys = []
                
                for key, entry in self.cache_entries.items():
                    if entry.is_expired():
                        expired_keys.append(key)
                
                for key in expired_keys:
                    await self._remove_entry(key)
                
                if expired_keys:
                    logger.info(f"清理了 {len(expired_keys)} 个过期缓存条目")
                
                await asyncio.sleep(300)  # 每5分钟清理一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理过期条目失败: {e}")
                await asyncio.sleep(60)
    
    async def _prefetch_predicted_entries(self):
        """预取预测条目的后台任务"""
        while True:
            try:
                if not self.prefetch_enabled or not self.prefetch_queue:
                    await asyncio.sleep(10)
                    continue
                
                # 处理预取队列
                prefetch_item = self.prefetch_queue.popleft()
                context = prefetch_item["context"]
                
                # 这里应该调用实际的数据获取逻辑
                # 由于我们不知道具体的数据获取方法，这里只是示例
                logger.debug(f"预取上下文: {context.to_key()}")
                
                await asyncio.sleep(1)  # 避免过于频繁的预取
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"预取失败: {e}")
                await asyncio.sleep(5)
    
    async def _optimize_cache_allocation(self):
        """优化缓存分配的后台任务"""
        while True:
            try:
                # 分析缓存使用情况
                total_entries = len(self.cache_entries)
                if total_entries == 0:
                    await asyncio.sleep(600)  # 10分钟
                    continue
                
                # 统计访问模式分布
                pattern_stats = defaultdict(int)
                affinity_stats = defaultdict(int)
                
                for entry in self.cache_entries.values():
                    pattern_stats[entry.access_pattern] += 1
                    affinity_stats[entry.affinity] += 1
                
                logger.info(f"缓存统计 - 总条目: {total_entries}, "
                          f"模式分布: {dict(pattern_stats)}, "
                          f"亲和性分布: {dict(affinity_stats)}")
                
                await asyncio.sleep(600)  # 每10分钟分析一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"缓存分配优化失败: {e}")
                await asyncio.sleep(300)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "total_entries": len(self.cache_entries),
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "context_predictions": self.stats["context_predictions"],
            "prefetch_hits": self.stats["prefetch_hits"],
            "invalidations": self.stats["invalidations"],
            "memory_usage": self.memory_cache.get_stats(),
            "context_clusters": len(self.context_analyzer.context_clusters),
            "prefetch_queue_size": len(self.prefetch_queue)
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 测试基本功能
            test_context = ContextVector(user_id="test", session_id="health_check")
            test_key = "health_check_key"
            test_value = {"test": True, "timestamp": datetime.now().isoformat()}
            
            # 测试设置
            set_success = await self.set(test_key, test_value, test_context, ttl_seconds=60)
            
            # 测试获取
            get_result = await self.get(test_key, test_context)
            get_success = get_result == test_value
            
            # 清理测试数据
            await self._remove_entry(test_key)
            
            return {
                "status": "healthy" if set_success and get_success else "degraded",
                "set_test": set_success,
                "get_test": get_success,
                "background_tasks_running": len([t for t in self._background_tasks if not t.done()]),
                "statistics": self.get_statistics(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def shutdown(self):
        """关闭缓存系统"""
        logger.info("关闭上下文感知缓存系统")
        
        # 取消后台任务
        for task in self._background_tasks:
            task.cancel()
        
        # 等待任务完成
        await asyncio.gather(*self._background_tasks, return_exceptions=True)


# 全局上下文感知缓存实例
_context_aware_cache: Optional[ContextAwareCache] = None

def get_context_aware_cache() -> ContextAwareCache:
    """获取全局上下文感知缓存实例"""
    global _context_aware_cache
    if _context_aware_cache is None:
        _context_aware_cache = ContextAwareCache()
    return _context_aware_cache