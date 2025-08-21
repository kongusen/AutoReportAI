"""
占位符缓存层

负责缓存读写、缓存验证、缓存策略
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from .models import (
    PlaceholderRequest, CacheKey, CacheEntry, AgentExecutionResult,
    CacheServiceInterface, ResultSource
)


class CacheService(CacheServiceInterface):
    """缓存服务 - 只负责缓存操作"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.reader = CacheReader(db_session)
        self.writer = CacheWriter(db_session)
        self.validator = CacheValidator()
        self.logger = logging.getLogger(__name__)
    
    async def get_result(self, request: PlaceholderRequest) -> Optional[CacheEntry]:
        """获取缓存结果"""
        try:
            cache_key = self._generate_cache_key(request)
            
            # 读取缓存
            cache_entry = await self.reader.read(cache_key)
            if not cache_entry:
                self.logger.debug(f"缓存未命中: {request.placeholder_name}")
                return None
            
            # 验证缓存有效性
            if not self.validator.is_valid(cache_entry):
                self.logger.debug(f"缓存已过期: {request.placeholder_name}")
                await self.writer.invalidate(cache_key)
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
            cache_entry = CacheEntry(
                key=cache_key.to_string(),
                value=result.formatted_value,
                confidence=result.confidence,
                cached_at=datetime.now(),
                expires_at=self._calculate_expiry_time(request),
                source_metadata={
                    "execution_time_ms": result.execution_time_ms,
                    "row_count": result.row_count,
                    "metadata": result.metadata
                }
            )
            
            saved = await self.writer.write(cache_entry, request)
            if saved:
                self.logger.debug(f"缓存保存成功: {request.placeholder_name}")
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
    
    def _calculate_expiry_time(self, request: PlaceholderRequest) -> datetime:
        """计算过期时间"""
        # 默认24小时过期
        # TODO: 可以根据占位符类型和数据更新频率调整
        return datetime.now() + timedelta(hours=24)


class CacheReader:
    """缓存读取器"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.logger = logging.getLogger(__name__)
    
    async def read(self, cache_key: CacheKey) -> Optional[CacheEntry]:
        """读取缓存"""
        try:
            from app.models.template_placeholder import PlaceholderValue
            
            cached = self.db.query(PlaceholderValue).filter(
                PlaceholderValue.cache_key == cache_key.to_string(),
                PlaceholderValue.success == True,
                PlaceholderValue.expires_at > datetime.now(),
                PlaceholderValue.source == "agent"  # 只读取Agent缓存
            ).first()
            
            if cached:
                return CacheEntry(
                    key=cached.cache_key,
                    value=cached.formatted_text or "",
                    confidence=getattr(cached, 'confidence_score', 0.0) or 0.0,
                    cached_at=cached.created_at,
                    expires_at=cached.expires_at,
                    source_metadata=getattr(cached, 'analysis_metadata', {}) or {}
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"缓存读取失败: {e}")
            # 缓存读取失败不应该影响主流程
            return None


class CacheWriter:
    """缓存写入器"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.logger = logging.getLogger(__name__)
    
    async def write(self, cache_entry: CacheEntry, request: PlaceholderRequest) -> bool:
        """写入缓存"""
        try:
            from app.models.template_placeholder import PlaceholderValue
            
            # 检查是否已存在相同的缓存
            existing = self.db.query(PlaceholderValue).filter(
                PlaceholderValue.cache_key == cache_entry.key
            ).first()
            
            if existing:
                # 更新现有缓存
                existing.formatted_text = cache_entry.value
                existing.confidence_score = cache_entry.confidence
                existing.expires_at = cache_entry.expires_at
                existing.analysis_metadata = cache_entry.source_metadata
                existing.updated_at = datetime.now()
            else:
                # 创建新缓存记录
                record = PlaceholderValue(
                    placeholder_id=request.placeholder_id,
                    data_source_id=request.data_source_id,
                    cache_key=cache_entry.key,
                    formatted_text=cache_entry.value,
                    confidence_score=cache_entry.confidence,
                    created_at=cache_entry.cached_at,
                    expires_at=cache_entry.expires_at,
                    success=True,
                    source="agent",
                    analysis_metadata=cache_entry.source_metadata,
                    execution_time=request.execution_time,
                    user_id=request.user_id
                )
                self.db.add(record)
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"缓存写入失败: {e}")
            return False
    
    async def invalidate(self, cache_key: CacheKey) -> bool:
        """失效缓存"""
        try:
            from app.models.template_placeholder import PlaceholderValue
            
            updated_count = self.db.query(PlaceholderValue).filter(
                PlaceholderValue.cache_key == cache_key.to_string()
            ).update({"expires_at": datetime.now()})
            
            self.db.commit()
            
            if updated_count > 0:
                self.logger.debug(f"缓存失效成功: {cache_key.to_string()}")
            
            return True
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"缓存失效失败: {e}")
            return False


class CacheValidator:
    """缓存验证器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def is_valid(self, cache_entry: CacheEntry) -> bool:
        """验证缓存是否有效"""
        try:
            # 检查过期时间
            if cache_entry.expires_at <= datetime.now():
                self.logger.debug("缓存已过期")
                return False
            
            # 检查置信度阈值
            if cache_entry.confidence < 0.5:  # 降低阈值
                self.logger.debug(f"缓存置信度过低: {cache_entry.confidence}")
                return False
            
            # 检查缓存值是否有效
            if not cache_entry.value or cache_entry.value.strip() == "":
                self.logger.debug("缓存值为空")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"缓存验证异常: {e}")
            return False


class CacheMetrics:
    """缓存指标收集器"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.logger = logging.getLogger(__name__)
    
    async def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        try:
            from app.models.template_placeholder import PlaceholderValue
            
            # 总缓存数量
            total_cache = self.db.query(PlaceholderValue).filter(
                PlaceholderValue.source == "agent"
            ).count()
            
            # 有效缓存数量
            valid_cache = self.db.query(PlaceholderValue).filter(
                PlaceholderValue.source == "agent",
                PlaceholderValue.expires_at > datetime.now(),
                PlaceholderValue.success == True
            ).count()
            
            # 今日缓存命中数量
            today = datetime.now().date()
            today_hits = self.db.query(PlaceholderValue).filter(
                PlaceholderValue.source == "agent",
                PlaceholderValue.last_hit_at >= today,
                PlaceholderValue.last_hit_at < datetime.combine(today, datetime.min.time()) + timedelta(days=1)
            ).count()
            
            return {
                "total_cache_entries": total_cache,
                "valid_cache_entries": valid_cache,
                "cache_hit_rate": (valid_cache / total_cache * 100) if total_cache > 0 else 0,
                "today_cache_hits": today_hits,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"获取缓存统计失败: {e}")
            return {
                "error": str(e),
                "last_updated": datetime.now().isoformat()
            }