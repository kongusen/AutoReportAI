"""
占位符缓存层 - 基于统一缓存系统重新实现

负责占位符相关的缓存读写、缓存验证、缓存策略
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session

from .models import (
    PlaceholderRequest, CacheKey, AgentExecutionResult,
    CacheServiceInterface, ResultSource
)
from ...infrastructure.cache.unified_cache_system import (
    UnifiedCacheManager, UnifiedCacheEntry, CacheType, CacheLevel,
    initialize_cache_manager, get_cache_manager
)


class CacheService(CacheServiceInterface):
    """缓存服务 - 基于统一缓存系统"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.cache_manager = get_cache_manager()
        
        # 如果没有全局缓存管理器，初始化一个
        if not self.cache_manager:
            try:
                import redis
                redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                self.cache_manager = initialize_cache_manager(
                    enable_memory=True,
                    enable_redis=True,
                    enable_database=True,
                    redis_client=redis_client,
                    db_session=db_session
                )
            except Exception as e:
                logging.warning(f"Redis连接失败，仅使用内存缓存: {e}")
                self.cache_manager = initialize_cache_manager(
                    enable_memory=True,
                    enable_redis=False,
                    enable_database=True,
                    db_session=db_session
                )
        
        self.logger = logging.getLogger(__name__)
    
    async def get_result(self, request: PlaceholderRequest) -> Optional[UnifiedCacheEntry]:
        """获取缓存结果"""
        try:
            cache_key = self._generate_cache_key(request)
            
            # 使用统一缓存管理器获取
            cache_entry = await self.cache_manager.get(cache_key)
            if not cache_entry:
                self.logger.debug(f"缓存未命中: {request.placeholder_name}")
                return None
            
            # 验证缓存有效性
            if not cache_entry.is_valid:
                self.logger.debug(f"缓存已过期: {request.placeholder_name}")
                await self.cache_manager.delete(cache_key)
                return None
            
            self.logger.debug(f"缓存命中: {request.placeholder_name}")
            return cache_entry
            
        except Exception as e:
            self.logger.warning(f"缓存获取失败: {request.placeholder_name}, 错误: {e}")
            return None
    
    async def save_result(self, request: PlaceholderRequest, result: AgentExecutionResult) -> bool:
        """保存结果到缓存 - 只保存Agent成功的结果"""
        try:
            if not result.success:
                self.logger.debug("Agent结果失败，不缓存")
                return False
            
            cache_key = self._generate_cache_key(request)
            
            # 构建缓存值
            cache_value = {
                "value": result.formatted_value,
                "raw_data": result.raw_data,
                "confidence": result.confidence,
                "execution_time_ms": result.execution_time_ms,
                "row_count": getattr(result, 'row_count', 0),
                "success": result.success,
                "metadata": getattr(result, 'metadata', {})
            }
            
            # 确定TTL和缓存级别
            ttl_seconds = self._calculate_ttl(request, result)
            cache_level = self._determine_cache_level(request)
            
            # 设置标签和元数据
            tags = {
                f"template:{request.metadata.get('template_id', 'unknown')}",
                f"datasource:{request.data_source_id}",
                f"user:{request.user_id}",
                f"type:{request.placeholder_type}"
            }
            
            metadata = {
                "placeholder_id": request.placeholder_id,
                "placeholder_name": request.placeholder_name,
                "placeholder_type": request.placeholder_type,
                "data_source_id": request.data_source_id,
                "user_id": request.user_id,
                "template_id": request.metadata.get('template_id'),
                "execution_time": request.execution_time.isoformat() if request.execution_time else None
            }
            
            saved = await self.cache_manager.set(
                key=cache_key,
                value=cache_value,
                cache_type=CacheType.PLACEHOLDER_RESULT,
                cache_level=cache_level,
                ttl_seconds=ttl_seconds,
                confidence=result.confidence,
                metadata=metadata,
                tags=tags
            )
            
            if saved:
                self.logger.debug(f"缓存保存成功: {request.placeholder_name}, TTL: {ttl_seconds}s")
            else:
                self.logger.warning(f"缓存保存失败: {request.placeholder_name}")
            
            return saved
            
        except Exception as e:
            self.logger.error(f"缓存保存异常: {request.placeholder_name}, 错误: {e}")
            return False
    
    def _generate_cache_key(self, request: PlaceholderRequest) -> CacheKey:
        """生成缓存键"""
        time_context = "default"
        if request.execution_time:
            # 根据执行时间生成时间上下文 - 按天缓存
            time_context = request.execution_time.strftime("%Y%m%d")
        
        return CacheKey(
            placeholder_id=request.placeholder_id,
            data_source_id=request.data_source_id,
            user_id=request.user_id,
            time_context=time_context
        )
    
    def _calculate_ttl(self, request: PlaceholderRequest, result: AgentExecutionResult) -> int:
        """计算TTL（秒）"""
        base_ttl = 3600  # 1小时基准
        
        # 根据置信度调整TTL
        if result.confidence > 0.9:
            ttl_seconds = base_ttl * 4  # 高置信度，缓存4小时
        elif result.confidence > 0.7:
            ttl_seconds = base_ttl * 2  # 中等置信度，缓存2小时
        else:
            ttl_seconds = base_ttl  # 低置信度，缓存1小时
        
        # 根据占位符类型调整TTL
        placeholder_type = request.placeholder_type.lower()
        if '统计' in placeholder_type or 'count' in placeholder_type:
            ttl_seconds = ttl_seconds * 2  # 统计数据缓存时间更长
        elif '实时' in placeholder_type or 'realtime' in placeholder_type:
            ttl_seconds = ttl_seconds // 4  # 实时数据缓存时间更短
        
        return min(ttl_seconds, 24 * 3600)  # 最长24小时
    
    def _determine_cache_level(self, request: PlaceholderRequest) -> CacheLevel:
        """确定缓存级别"""
        placeholder_type = request.placeholder_type.lower()
        
        # 高频访问的统计数据使用内存缓存
        if any(keyword in placeholder_type for keyword in ['统计', 'count', 'sum', 'avg', '总数']):
            return CacheLevel.MEMORY
        
        # 图表数据使用Redis缓存
        elif '图表' in placeholder_type or 'chart' in placeholder_type:
            return CacheLevel.REDIS
        
        # 其他数据使用数据库缓存
        else:
            return CacheLevel.DATABASE