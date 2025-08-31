"""
上下文缓存

缓存文档上下文、业务上下文等分析结果
"""

import logging
import hashlib
import json
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio

from ..models import DocumentContext, BusinessContext, TimeContext

logger = logging.getLogger(__name__)

@dataclass
class ContextCacheEntry:
    """上下文缓存条目"""
    key: str
    context_type: str  # 'document', 'business', 'time'
    context_data: Dict[str, Any]
    timestamp: datetime
    ttl_seconds: int
    dependencies: Set[str]  # 依赖的其他缓存键
    access_count: int = 0
    last_access: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl_seconds <= 0:
            return False
        return datetime.now() > (self.timestamp + timedelta(seconds=self.ttl_seconds))
    
    def update_access(self):
        """更新访问信息"""
        self.access_count += 1
        self.last_access = datetime.now()

class ContextCache:
    """上下文缓存"""
    
    def __init__(self, 
                 max_entries: int = 500,
                 default_ttl: int = 7200,  # 2小时默认TTL
                 cleanup_interval: int = 600):  # 10分钟清理间隔
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        
        # 存储缓存条目
        self._cache: Dict[str, ContextCacheEntry] = {}
        self._lock = asyncio.Lock()
        
        # 依赖关系映射
        self._dependency_graph: Dict[str, Set[str]] = {}
        
        # 统计信息
        self.stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'dependency_cascades': 0
        }
        
        # 启动定期清理任务
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _generate_context_key(self, 
                             context_type: str,
                             identifier: str,
                             context_params: Dict[str, Any] = None) -> str:
        """生成上下文缓存键"""
        hash_data = {
            'context_type': context_type,
            'identifier': identifier,
            'params': context_params or {}
        }
        
        json_str = json.dumps(hash_data, sort_keys=True, ensure_ascii=False)
        hash_obj = hashlib.md5(json_str.encode('utf-8'))
        return f"ctx_{context_type}_{hash_obj.hexdigest()}"
    
    async def get_document_context(self, 
                                  document_id: str,
                                  version: Optional[str] = None) -> Optional[DocumentContext]:
        """获取文档上下文"""
        key = self._generate_context_key('document', document_id, {'version': version})
        
        async with self._lock:
            entry = self._cache.get(key)
            if not entry or entry.is_expired():
                if entry:
                    del self._cache[key]
                self.stats['misses'] += 1
                return None
            
            entry.update_access()
            self.stats['hits'] += 1
            
            # 转换为DocumentContext对象
            try:
                return DocumentContext(**entry.context_data)
            except Exception as e:
                logger.error(f"反序列化DocumentContext失败: {e}")
                return None
    
    async def set_document_context(self, 
                                  document_id: str,
                                  context: DocumentContext,
                                  ttl_seconds: Optional[int] = None,
                                  dependencies: Set[str] = None):
        """设置文档上下文"""
        key = self._generate_context_key('document', document_id)
        await self._set_context_entry(key, 'document', context, ttl_seconds, dependencies)
    
    async def get_business_context(self, 
                                  business_id: str,
                                  domain: Optional[str] = None) -> Optional[BusinessContext]:
        """获取业务上下文"""
        key = self._generate_context_key('business', business_id, {'domain': domain})
        
        async with self._lock:
            entry = self._cache.get(key)
            if not entry or entry.is_expired():
                if entry:
                    del self._cache[key]
                self.stats['misses'] += 1
                return None
            
            entry.update_access()
            self.stats['hits'] += 1
            
            try:
                return BusinessContext(**entry.context_data)
            except Exception as e:
                logger.error(f"反序列化BusinessContext失败: {e}")
                return None
    
    async def set_business_context(self, 
                                  business_id: str,
                                  context: BusinessContext,
                                  ttl_seconds: Optional[int] = None,
                                  dependencies: Set[str] = None):
        """设置业务上下文"""
        key = self._generate_context_key('business', business_id)
        await self._set_context_entry(key, 'business', context, ttl_seconds, dependencies)
    
    async def get_time_context(self, 
                              time_id: str,
                              time_range: Optional[Dict[str, Any]] = None) -> Optional[TimeContext]:
        """获取时间上下文"""
        key = self._generate_context_key('time', time_id, time_range)
        
        async with self._lock:
            entry = self._cache.get(key)
            if not entry or entry.is_expired():
                if entry:
                    del self._cache[key]
                self.stats['misses'] += 1
                return None
            
            entry.update_access()
            self.stats['hits'] += 1
            
            try:
                return TimeContext(**entry.context_data)
            except Exception as e:
                logger.error(f"反序列化TimeContext失败: {e}")
                return None
    
    async def set_time_context(self, 
                              time_id: str,
                              context: TimeContext,
                              ttl_seconds: Optional[int] = None,
                              dependencies: Set[str] = None):
        """设置时间上下文"""
        key = self._generate_context_key('time', time_id)
        await self._set_context_entry(key, 'time', context, ttl_seconds, dependencies)
    
    async def _set_context_entry(self, 
                                key: str,
                                context_type: str,
                                context: Any,
                                ttl_seconds: Optional[int] = None,
                                dependencies: Set[str] = None):
        """设置上下文缓存条目"""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        deps = dependencies or set()
        
        async with self._lock:
            # 如果缓存已满，进行LRU驱逐
            if len(self._cache) >= self.max_entries:
                await self._evict_lru()
            
            # 将上下文对象转换为字典
            if hasattr(context, '__dict__'):
                context_data = context.__dict__.copy()
            elif isinstance(context, dict):
                context_data = context.copy()
            else:
                context_data = {'data': context}
            
            entry = ContextCacheEntry(
                key=key,
                context_type=context_type,
                context_data=context_data,
                timestamp=datetime.now(),
                ttl_seconds=ttl,
                dependencies=deps
            )
            
            self._cache[key] = entry
            
            # 更新依赖关系图
            if deps:
                self._dependency_graph[key] = deps
    
    async def invalidate_by_key(self, key: str):
        """根据键使缓存失效"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self.stats['invalidations'] += 1
            
            # 清理依赖关系
            if key in self._dependency_graph:
                del self._dependency_graph[key]
    
    async def invalidate_by_dependency(self, dependency_key: str):
        """根据依赖关系使缓存失效"""
        async with self._lock:
            keys_to_invalidate = [
                key for key, deps in self._dependency_graph.items()
                if dependency_key in deps
            ]
            
            for key in keys_to_invalidate:
                if key in self._cache:
                    del self._cache[key]
                    self.stats['invalidations'] += 1
                    self.stats['dependency_cascades'] += 1
                
                if key in self._dependency_graph:
                    del self._dependency_graph[key]
    
    async def invalidate_by_type(self, context_type: str):
        """根据上下文类型使缓存失效"""
        async with self._lock:
            keys_to_invalidate = [
                key for key, entry in self._cache.items()
                if entry.context_type == context_type
            ]
            
            for key in keys_to_invalidate:
                del self._cache[key]
                self.stats['invalidations'] += 1
                
                if key in self._dependency_graph:
                    del self._dependency_graph[key]
    
    async def clear(self):
        """清空所有缓存"""
        async with self._lock:
            self._cache.clear()
            self._dependency_graph.clear()
    
    async def _evict_lru(self):
        """驱逐最少使用的缓存条目"""
        if not self._cache:
            return
        
        lru_key = min(
            self._cache.keys(),
            key=lambda k: (
                self._cache[k].access_count,
                self._cache[k].last_access or self._cache[k].timestamp
            )
        )
        
        del self._cache[lru_key]
        if lru_key in self._dependency_graph:
            del self._dependency_graph[lru_key]
    
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
                    logger.error(f"上下文缓存清理任务出错: {e}")
        
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
                if key in self._dependency_graph:
                    del self._dependency_graph[key]
            
            if expired_keys:
                logger.debug(f"清理了 {len(expired_keys)} 个过期上下文缓存条目")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0
        
        # 按类型统计
        type_stats = {}
        for entry in self._cache.values():
            type_name = entry.context_type
            if type_name not in type_stats:
                type_stats[type_name] = {'count': 0, 'avg_access': 0}
            type_stats[type_name]['count'] += 1
            type_stats[type_name]['avg_access'] += entry.access_count
        
        # 计算平均访问次数
        for type_name in type_stats:
            if type_stats[type_name]['count'] > 0:
                type_stats[type_name]['avg_access'] /= type_stats[type_name]['count']
        
        return {
            'cache_size': len(self._cache),
            'max_entries': self.max_entries,
            'hit_rate': hit_rate,
            'dependency_count': len(self._dependency_graph),
            'type_distribution': type_stats,
            'stats': self.stats.copy()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        stats = self.get_stats()
        
        health_status = "healthy"
        issues = []
        
        # 检查命中率
        if stats['hit_rate'] < 0.2:
            issues.append("上下文缓存命中率过低")
            health_status = "warning"
        
        # 检查缓存大小
        if stats['cache_size'] >= self.max_entries * 0.9:
            issues.append("上下文缓存容量即将用完")
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
        logger.info("上下文缓存已关闭")