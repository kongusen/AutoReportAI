"""
统一占位符缓存服务

基于统一缓存系统重新实现的占位符缓存服务，兼容原有接口
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session

from .models import PlaceholderRequest, AgentExecutionResult, CacheKey
from ...infrastructure.cache.unified_cache_system import (
    UnifiedCacheManager, UnifiedCacheEntry, CacheType, CacheLevel,
    initialize_cache_manager, get_cache_manager
)

logger = logging.getLogger(__name__)


class UnifiedCacheService:
    """统一占位符缓存服务"""
    
    def __init__(self, db_session: Session, cache_manager: Optional[UnifiedCacheManager] = None):
        self.db = db_session
        self.cache_manager = cache_manager or get_cache_manager()
        
        # 如果没有缓存管理器，初始化一个
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
                logger.warning(f"Redis连接失败，仅使用内存缓存: {e}")
                self.cache_manager = initialize_cache_manager(
                    enable_memory=True,
                    enable_redis=False,
                    enable_database=True,
                    db_session=db_session
                )
        
        self.logger = logging.getLogger(__name__)
    
    async def get_result(self, request: PlaceholderRequest) -> Optional[UnifiedCacheEntry]:
        """获取缓存结果（兼容原接口）"""
        try:
            cache_key = self._generate_cache_key(request)
            
            # 使用统一缓存管理器获取
            entry = await self.cache_manager.get(cache_key)
            
            if not entry:
                self.logger.debug(f"缓存未命中: {request.placeholder_name}")
                return None
            
            # 验证缓存有效性
            if not entry.is_valid:
                self.logger.debug(f"缓存已过期: {request.placeholder_name}")
                await self.cache_manager.delete(cache_key)
                return None
            
            self.logger.debug(f"缓存命中: {request.placeholder_name}")
            return entry
            
        except Exception as e:
            self.logger.warning(f"缓存获取失败: {request.placeholder_name}, 错误: {e}")
            return None
    
    async def save_result(self, request: PlaceholderRequest, result: AgentExecutionResult) -> bool:
        """保存结果到缓存（兼容原接口）"""
        try:
            cache_key = self._generate_cache_key(request)
            
            # 构建缓存值
            cache_value = {
                "value": result.formatted_value if hasattr(result, 'formatted_value') else str(result.raw_data),
                "raw_data": result.raw_data,
                "confidence": getattr(result, 'confidence', 0.8),
                "execution_time": getattr(result, 'execution_time_ms', 0),
                "success": result.success,
                "error_message": getattr(result, 'error_message', None)
            }
            
            # 确定TTL（基于置信度和数据类型）
            confidence = getattr(result, 'confidence', 0.8)
            base_ttl = 3600  # 1小时
            
            if confidence > 0.9:
                ttl_seconds = base_ttl * 2  # 高置信度，缓存2小时
            elif confidence > 0.7:
                ttl_seconds = base_ttl  # 中等置信度，缓存1小时
            else:
                ttl_seconds = base_ttl // 2  # 低置信度，缓存30分钟
            
            # 根据占位符类型设置缓存级别
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
                "execution_time": request.execution_time.isoformat() if request.execution_time else None,
                "agent_analysis": True
            }
            
            # 尝试自动清理内存（如果需要）
            try:
                await self.cache_manager.auto_cleanup_if_needed()
            except Exception as cleanup_error:
                self.logger.warning(f"自动清理检查失败: {cleanup_error}")
            
            success = await self.cache_manager.set(
                key=cache_key,
                value=cache_value,
                cache_type=CacheType.PLACEHOLDER_RESULT,
                cache_level=cache_level,
                ttl_seconds=ttl_seconds,
                confidence=confidence,
                metadata=metadata,
                tags=tags
            )
            
            if success:
                self.logger.debug(f"结果已缓存: {request.placeholder_name}, TTL: {ttl_seconds}s, Level: {cache_level.value}")
            else:
                self.logger.warning(f"结果缓存失败: {request.placeholder_name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"缓存保存失败: {request.placeholder_name}, 错误: {e}")
            return False
    
    async def invalidate(self, cache_key: CacheKey) -> bool:
        """使缓存失效（兼容原接口）"""
        try:
            key_str = cache_key.to_string()
            success = await self.cache_manager.delete(key_str)
            
            if success:
                self.logger.debug(f"缓存已失效: {key_str}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"缓存失效失败: {e}")
            return False
    
    async def invalidate_by_template(self, template_id: str) -> int:
        """根据模板ID批量失效缓存"""
        try:
            tags = {f"template:{template_id}"}
            count = await self.cache_manager.invalidate_by_tags(tags)
            
            self.logger.info(f"模板缓存已失效: {template_id}, 影响条目: {count}")
            return count
            
        except Exception as e:
            self.logger.error(f"模板缓存失效失败: {template_id}, 错误: {e}")
            return 0
    
    async def invalidate_by_data_source(self, data_source_id: str) -> int:
        """根据数据源ID批量失效缓存"""
        try:
            tags = {f"datasource:{data_source_id}"}
            count = await self.cache_manager.invalidate_by_tags(tags)
            
            self.logger.info(f"数据源缓存已失效: {data_source_id}, 影响条目: {count}")
            return count
            
        except Exception as e:
            self.logger.error(f"数据源缓存失效失败: {data_source_id}, 错误: {e}")
            return 0
    
    async def cleanup_expired(self) -> int:
        """清理过期缓存"""
        try:
            count = await self.cache_manager.cleanup_expired()
            self.logger.info(f"清理过期缓存: {count} 个条目")
            return count
            
        except Exception as e:
            self.logger.error(f"清理过期缓存失败: {e}")
            return 0
    
    async def get_cache_statistics(self) -> dict:
        """获取缓存统计信息"""
        try:
            stats = await self.cache_manager.get_statistics()
            return stats
            
        except Exception as e:
            self.logger.error(f"获取缓存统计失败: {e}")
            return {}
    
    def _generate_cache_key(self, request: PlaceholderRequest) -> str:
        """生成缓存键"""
        cache_key = CacheKey(
            placeholder_id=request.placeholder_id,
            data_source_id=request.data_source_id,
            user_id=request.user_id,
            time_context=""  # 可以根据需要添加时间上下文
        )
        return cache_key.to_string()
    
    def _determine_cache_level(self, request: PlaceholderRequest) -> CacheLevel:
        """确定缓存级别"""
        # 根据占位符类型和重要性确定缓存级别
        placeholder_type = request.placeholder_type.lower()
        
        # 高频访问的数据类型使用内存缓存
        if placeholder_type in ['统计', 'count', 'sum', 'avg']:
            return CacheLevel.MEMORY
        
        # 图表数据使用Redis缓存（中等频率访问）
        elif placeholder_type.startswith('图表'):
            return CacheLevel.REDIS
        
        # 其他数据使用数据库缓存
        else:
            return CacheLevel.DATABASE


# 向后兼容的别名
CacheService = UnifiedCacheService


# 便捷函数
def create_unified_cache_service(db_session: Session) -> UnifiedCacheService:
    """创建统一缓存服务"""
    return UnifiedCacheService(db_session)


async def get_placeholder_cache(request: PlaceholderRequest) -> Optional[dict]:
    """便捷的占位符缓存获取函数"""
    # 这需要一个全局的缓存服务实例
    # 在实际使用中应该通过依赖注入或全局变量获取
    return None


async def set_placeholder_cache(request: PlaceholderRequest, result: AgentExecutionResult) -> bool:
    """便捷的占位符缓存设置函数"""
    # 这需要一个全局的缓存服务实例
    # 在实际使用中应该通过依赖注入或全局变量获取
    return False