"""
Pipeline Cache Manager

两阶段流水线的缓存管理服务，统一管理占位符缓存、分析结果缓存等
"""

import asyncio
import logging
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.template_placeholder import TemplatePlaceholder, PlaceholderValue
from app.models.template import Template
from app.models.data_source import DataSource

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """缓存级别"""
    TEMPLATE = "template"           # 模板级别缓存
    PLACEHOLDER = "placeholder"     # 占位符级别缓存
    AGENT_ANALYSIS = "agent_analysis"  # Agent分析结果缓存
    DATA_EXTRACTION = "data_extraction"  # 数据提取结果缓存


class CacheStatus(Enum):
    """缓存状态"""
    VALID = "valid"                 # 有效
    EXPIRED = "expired"             # 过期
    INVALID = "invalid"             # 无效
    MISSING = "missing"             # 不存在


@dataclass
class CacheEntry:
    """缓存条目"""
    cache_key: str
    cache_level: CacheLevel
    data: Any
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    last_hit_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_valid(self) -> bool:
        return datetime.now() < self.expires_at
    
    @property
    def ttl_seconds(self) -> int:
        if self.is_valid:
            return int((self.expires_at - datetime.now()).total_seconds())
        return 0


@dataclass
class CacheStatistics:
    """缓存统计信息"""
    total_entries: int = 0
    valid_entries: int = 0
    expired_entries: int = 0
    total_hits: int = 0
    cache_hit_rate: float = 0.0
    total_size_bytes: int = 0
    avg_ttl_seconds: float = 0.0
    by_level: Dict[CacheLevel, Dict[str, Any]] = field(default_factory=dict)


class PipelineCacheManager:
    """两阶段流水线缓存管理器"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cache_config = {
            CacheLevel.TEMPLATE: {"default_ttl_hours": 24, "max_entries": 1000},
            CacheLevel.PLACEHOLDER: {"default_ttl_hours": 12, "max_entries": 5000},
            CacheLevel.AGENT_ANALYSIS: {"default_ttl_hours": 48, "max_entries": 2000},
            CacheLevel.DATA_EXTRACTION: {"default_ttl_hours": 6, "max_entries": 10000}
        }
    
    async def get_cache_entry(
        self,
        cache_key: str,
        cache_level: CacheLevel,
        auto_refresh: bool = True
    ) -> Optional[CacheEntry]:
        """获取缓存条目"""
        try:
            if cache_level == CacheLevel.PLACEHOLDER:
                # 从占位符值表获取
                cached_value = self.db.query(PlaceholderValue).filter(
                    PlaceholderValue.cache_key == cache_key,
                    PlaceholderValue.success == True
                ).first()
                
                if cached_value:
                    entry = CacheEntry(
                        cache_key=cache_key,
                        cache_level=cache_level,
                        data={
                            "formatted_text": cached_value.formatted_text,
                            "raw_result": cached_value.raw_query_result,
                            "processed_value": cached_value.processed_value,
                            "execution_sql": cached_value.execution_sql
                        },
                        created_at=cached_value.created_at,
                        expires_at=cached_value.expires_at,
                        hit_count=cached_value.hit_count,
                        last_hit_at=cached_value.last_hit_at,
                        metadata={
                            "placeholder_id": str(cached_value.placeholder_id),
                            "data_source_id": str(cached_value.data_source_id),
                            "execution_time_ms": cached_value.execution_time_ms,
                            "row_count": cached_value.row_count
                        }
                    )
                    
                    if entry.is_valid:
                        if auto_refresh:
                            await self._update_cache_hit_stats(cached_value)
                        return entry
                    else:
                        # 缓存过期，清理
                        if auto_refresh:
                            await self._cleanup_expired_entry(cached_value)
                
            # 其他缓存级别的实现...
            # TODO: 实现模板、Agent分析等其他缓存级别
            
            return None
            
        except Exception as e:
            logger.error(f"获取缓存条目失败: {cache_key}, 错误: {str(e)}")
            return None
    
    async def set_cache_entry(
        self,
        cache_key: str,
        cache_level: CacheLevel,
        data: Any,
        ttl_hours: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """设置缓存条目"""
        try:
            config = self.cache_config[cache_level]
            ttl_hours = ttl_hours or config["default_ttl_hours"]
            expires_at = datetime.now() + timedelta(hours=ttl_hours)
            metadata = metadata or {}
            
            if cache_level == CacheLevel.PLACEHOLDER:
                # 保存到占位符值表
                placeholder_id = metadata.get("placeholder_id")
                data_source_id = metadata.get("data_source_id")
                
                if not placeholder_id or not data_source_id:
                    logger.error("占位符缓存缺少必要的metadata: placeholder_id, data_source_id")
                    return False
                
                # 检查是否已存在
                existing = self.db.query(PlaceholderValue).filter(
                    PlaceholderValue.cache_key == cache_key
                ).first()
                
                if existing:
                    # 更新现有缓存
                    existing.formatted_text = data.get("formatted_text", "")
                    existing.raw_query_result = data.get("raw_result")
                    existing.processed_value = data.get("processed_value", {})
                    existing.execution_sql = data.get("execution_sql", "")
                    existing.expires_at = expires_at
                    existing.execution_time_ms = metadata.get("execution_time_ms", 0)
                    existing.row_count = metadata.get("row_count", 0)
                    existing.success = True
                else:
                    # 创建新缓存
                    cache_record = PlaceholderValue(
                        placeholder_id=placeholder_id,
                        data_source_id=data_source_id,
                        raw_query_result=data.get("raw_result"),
                        processed_value=data.get("processed_value", {}),
                        formatted_text=data.get("formatted_text", ""),
                        execution_sql=data.get("execution_sql", ""),
                        execution_time_ms=metadata.get("execution_time_ms", 0),
                        row_count=metadata.get("row_count", 0),
                        success=True,
                        cache_key=cache_key,
                        expires_at=expires_at,
                        hit_count=0
                    )
                    self.db.add(cache_record)
                
                self.db.commit()
                logger.debug(f"缓存条目已保存: {cache_key}")
                return True
            
            # 其他缓存级别的实现...
            # TODO: 实现其他缓存级别的存储
            
            return False
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"设置缓存条目失败: {cache_key}, 错误: {str(e)}")
            return False
    
    async def invalidate_cache(
        self,
        cache_pattern: str = None,
        cache_level: Optional[CacheLevel] = None,
        template_id: Optional[str] = None,
        data_source_id: Optional[str] = None
    ) -> int:
        """清除缓存"""
        try:
            invalidated_count = 0
            
            if cache_level == CacheLevel.PLACEHOLDER or cache_level is None:
                # 清除占位符缓存
                query = self.db.query(PlaceholderValue).filter(
                    PlaceholderValue.expires_at > datetime.now()
                )
                
                if template_id:
                    # 通过模板ID过滤
                    query = query.join(TemplatePlaceholder).filter(
                        TemplatePlaceholder.template_id == template_id
                    )
                
                if data_source_id:
                    query = query.filter(PlaceholderValue.data_source_id == data_source_id)
                
                if cache_pattern:
                    query = query.filter(PlaceholderValue.cache_key.like(f"%{cache_pattern}%"))
                
                # 设置过期时间为当前时间，实现软删除
                result = query.update({"expires_at": datetime.now()})
                invalidated_count += result
            
            # TODO: 实现其他缓存级别的清除
            
            self.db.commit()
            logger.info(f"缓存清除完成: 清除 {invalidated_count} 条缓存")
            return invalidated_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"清除缓存失败: {str(e)}")
            return 0
    
    async def get_cache_statistics(
        self,
        template_id: Optional[str] = None,
        data_source_id: Optional[str] = None,
        cache_level: Optional[CacheLevel] = None
    ) -> CacheStatistics:
        """获取缓存统计信息"""
        try:
            stats = CacheStatistics()
            
            # 占位符缓存统计
            if cache_level == CacheLevel.PLACEHOLDER or cache_level is None:
                query = self.db.query(PlaceholderValue)
                
                if template_id:
                    query = query.join(TemplatePlaceholder).filter(
                        TemplatePlaceholder.template_id == template_id
                    )
                
                if data_source_id:
                    query = query.filter(PlaceholderValue.data_source_id == data_source_id)
                
                total_entries = query.count()
                valid_entries = query.filter(PlaceholderValue.expires_at > datetime.now()).count()
                expired_entries = total_entries - valid_entries
                
                total_hits = query.with_entities(
                    self.db.func.sum(PlaceholderValue.hit_count)
                ).scalar() or 0
                
                avg_execution_time = query.filter(
                    PlaceholderValue.execution_time_ms.isnot(None)
                ).with_entities(
                    self.db.func.avg(PlaceholderValue.execution_time_ms)
                ).scalar() or 0
                
                cache_hit_rate = (total_hits / total_entries * 100) if total_entries > 0 else 0
                
                stats.total_entries += total_entries
                stats.valid_entries += valid_entries
                stats.expired_entries += expired_entries
                stats.total_hits += total_hits
                
                stats.by_level[CacheLevel.PLACEHOLDER] = {
                    "total_entries": total_entries,
                    "valid_entries": valid_entries,
                    "expired_entries": expired_entries,
                    "total_hits": total_hits,
                    "cache_hit_rate": round(cache_hit_rate, 2),
                    "avg_execution_time_ms": round(avg_execution_time, 2)
                }
            
            # 计算总体统计
            if stats.total_entries > 0:
                stats.cache_hit_rate = round(stats.total_hits / stats.total_entries * 100, 2)
            
            return stats
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {str(e)}")
            return CacheStatistics()
    
    async def optimize_cache(
        self,
        cleanup_expired: bool = True,
        compress_old_entries: bool = True,
        max_entries_per_level: Optional[Dict[CacheLevel, int]] = None
    ) -> Dict[str, Any]:
        """优化缓存性能"""
        try:
            optimization_result = {
                "cleanup_expired": 0,
                "compressed_entries": 0,
                "removed_old_entries": 0,
                "total_optimized": 0
            }
            
            # 1. 清理过期缓存
            if cleanup_expired:
                expired_count = await self._cleanup_expired_caches()
                optimization_result["cleanup_expired"] = expired_count
            
            # 2. 压缩旧缓存条目
            if compress_old_entries:
                compressed_count = await self._compress_old_cache_entries()
                optimization_result["compressed_entries"] = compressed_count
            
            # 3. 移除超出限制的旧条目
            if max_entries_per_level:
                for cache_level, max_entries in max_entries_per_level.items():
                    removed_count = await self._remove_excess_cache_entries(cache_level, max_entries)
                    optimization_result["removed_old_entries"] += removed_count
            
            optimization_result["total_optimized"] = sum(optimization_result.values())
            
            logger.info(f"缓存优化完成: {optimization_result}")
            return optimization_result
            
        except Exception as e:
            logger.error(f"缓存优化失败: {str(e)}")
            return {"error": str(e)}
    
    async def _update_cache_hit_stats(self, cached_value: PlaceholderValue):
        """更新缓存命中统计"""
        try:
            cached_value.hit_count += 1
            cached_value.last_hit_at = datetime.now()
            self.db.commit()
        except Exception as e:
            logger.error(f"更新缓存命中统计失败: {str(e)}")
    
    async def _cleanup_expired_entry(self, cached_value: PlaceholderValue):
        """清理单个过期缓存条目"""
        try:
            self.db.delete(cached_value)
            self.db.commit()
            logger.debug(f"清理过期缓存条目: {cached_value.cache_key}")
        except Exception as e:
            logger.error(f"清理过期缓存条目失败: {str(e)}")
    
    async def _cleanup_expired_caches(self) -> int:
        """批量清理过期缓存"""
        try:
            # 清理过期的占位符缓存
            expired_count = self.db.query(PlaceholderValue).filter(
                PlaceholderValue.expires_at <= datetime.now()
            ).delete()
            
            self.db.commit()
            return expired_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"批量清理过期缓存失败: {str(e)}")
            return 0
    
    async def _compress_old_cache_entries(self) -> int:
        """压缩旧的缓存条目（简化数据结构）"""
        try:
            # 查找超过一定时间的缓存条目，简化其数据结构
            old_threshold = datetime.now() - timedelta(days=7)
            
            old_entries = self.db.query(PlaceholderValue).filter(
                PlaceholderValue.created_at < old_threshold,
                PlaceholderValue.raw_query_result.isnot(None)
            ).all()
            
            compressed_count = 0
            for entry in old_entries:
                # 清除原始查询结果，只保留格式化文本
                if entry.raw_query_result:
                    entry.raw_query_result = None
                    compressed_count += 1
            
            self.db.commit()
            return compressed_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"压缩旧缓存条目失败: {str(e)}")
            return 0
    
    async def _remove_excess_cache_entries(self, cache_level: CacheLevel, max_entries: int) -> int:
        """移除超出限制的缓存条目"""
        try:
            if cache_level == CacheLevel.PLACEHOLDER:
                # 获取总数
                total_count = self.db.query(PlaceholderValue).count()
                
                if total_count > max_entries:
                    # 删除最旧的条目
                    excess_count = total_count - max_entries
                    
                    oldest_entries = self.db.query(PlaceholderValue).order_by(
                        PlaceholderValue.last_hit_at.asc().nullsfirst(),
                        PlaceholderValue.created_at.asc()
                    ).limit(excess_count).all()
                    
                    for entry in oldest_entries:
                        self.db.delete(entry)
                    
                    self.db.commit()
                    return excess_count
            
            return 0
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"移除超出限制的缓存条目失败: {str(e)}")
            return 0
    
    def generate_cache_key(
        self,
        cache_level: CacheLevel,
        template_id: Optional[str] = None,
        placeholder_id: Optional[str] = None,
        data_source_id: Optional[str] = None,
        additional_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成缓存键"""
        key_components = [cache_level.value]
        
        if template_id:
            key_components.append(f"template:{template_id}")
        if placeholder_id:
            key_components.append(f"placeholder:{placeholder_id}")
        if data_source_id:
            key_components.append(f"datasource:{data_source_id}")
        
        if additional_params:
            # 对参数进行排序以确保一致性
            sorted_params = sorted(additional_params.items())
            params_str = json.dumps(sorted_params, sort_keys=True)
            key_components.append(f"params:{hashlib.md5(params_str.encode()).hexdigest()}")
        
        key_string = ":".join(key_components)
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]  # 32字符的哈希


# 便捷函数
async def get_pipeline_cache_manager(db: Session) -> PipelineCacheManager:
    """获取流水线缓存管理器实例"""
    return PipelineCacheManager(db)


async def cleanup_all_pipeline_caches(db: Session) -> Dict[str, Any]:
    """清理所有流水线缓存"""
    cache_manager = PipelineCacheManager(db)
    return await cache_manager.optimize_cache(
        cleanup_expired=True,
        compress_old_entries=True,
        max_entries_per_level={
            CacheLevel.PLACEHOLDER: 5000,
            CacheLevel.AGENT_ANALYSIS: 2000
        }
    )