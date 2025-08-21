"""
Placeholder Repository

占位符数据访问层，提供占位符相关的专业化查询方法
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload

from app.models.template_placeholder import TemplatePlaceholder, PlaceholderValue
from .base_repository import BaseRepository, TransactionalRepository

logger = logging.getLogger(__name__)


class PlaceholderRepository(TransactionalRepository[TemplatePlaceholder]):
    """占位符Repository"""
    
    def __init__(self, session: Session):
        super().__init__(session, TemplatePlaceholder)
    
    async def find_by_template_id(self, template_id: str, include_values: bool = True) -> List[TemplatePlaceholder]:
        """根据模板ID查找占位符"""
        try:
            query = self.session.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.template_id == template_id
            )
            
            if include_values:
                query = query.options(joinedload(TemplatePlaceholder.values))
            
            return query.all()
        except Exception as e:
            self.logger.error(f"Error finding placeholders by template_id {template_id}: {e}")
            return []
    
    async def find_by_user_id(self, user_id: str, limit: int = 100) -> List[TemplatePlaceholder]:
        """根据用户ID查找占位符"""
        return await self.list(
            filters={'user_id': user_id},
            limit=limit,
            order_by='created_at',
            desc_order=True
        )
    
    async def find_pending_analysis(self, data_source_id: str = None) -> List[TemplatePlaceholder]:
        """查找待分析的占位符"""
        filters = {
            'analysis_status': 'pending',
            'is_active': True
        }
        
        if data_source_id:
            filters['data_source_id'] = data_source_id
        
        return await self.list(filters=filters)
    
    async def find_by_name_pattern(self, pattern: str, template_id: str = None) -> List[TemplatePlaceholder]:
        """根据名称模式查找占位符"""
        try:
            query = self.session.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.placeholder_name.ilike(f"%{pattern}%")
            )
            
            if template_id:
                query = query.filter(TemplatePlaceholder.template_id == template_id)
            
            return query.all()
        except Exception as e:
            self.logger.error(f"Error finding placeholders by pattern {pattern}: {e}")
            return []
    
    async def find_with_analysis_results(self, confidence_threshold: float = 0.8) -> List[TemplatePlaceholder]:
        """查找有分析结果的占位符"""
        filters = {
            'analysis_status': 'completed',
            'confidence_score': {'gte': confidence_threshold}
        }
        
        return await self.list(filters=filters)
    
    async def find_failed_analysis(self, retry_limit: int = 3) -> List[TemplatePlaceholder]:
        """查找分析失败的占位符"""
        filters = {
            'analysis_status': 'failed',
            'retry_count': {'lt': retry_limit}
        }
        
        return await self.list(filters=filters)
    
    async def update_analysis_status(self, placeholder_id: str, status: str, 
                                   analysis_result: Dict[str, Any] = None,
                                   confidence_score: float = None) -> bool:
        """更新分析状态"""
        try:
            placeholder = await self.get_by_id(placeholder_id)
            if not placeholder:
                return False
            
            placeholder.analysis_status = status
            
            if analysis_result:
                placeholder.analysis_result = analysis_result
            
            if confidence_score is not None:
                placeholder.confidence_score = confidence_score
            
            await self.update_and_commit(placeholder)
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating analysis status for {placeholder_id}: {e}")
            return False
    
    async def increment_retry_count(self, placeholder_id: str) -> bool:
        """增加重试计数"""
        try:
            placeholder = await self.get_by_id(placeholder_id)
            if not placeholder:
                return False
            
            placeholder.retry_count = (placeholder.retry_count or 0) + 1
            await self.update_and_commit(placeholder)
            return True
            
        except Exception as e:
            self.logger.error(f"Error incrementing retry count for {placeholder_id}: {e}")
            return False
    
    async def get_analysis_statistics(self, template_id: str = None) -> Dict[str, int]:
        """获取分析统计"""
        try:
            base_query = self.session.query(TemplatePlaceholder)
            
            if template_id:
                base_query = base_query.filter(TemplatePlaceholder.template_id == template_id)
            
            stats = {
                'total': base_query.count(),
                'pending': base_query.filter(TemplatePlaceholder.analysis_status == 'pending').count(),
                'completed': base_query.filter(TemplatePlaceholder.analysis_status == 'completed').count(),
                'failed': base_query.filter(TemplatePlaceholder.analysis_status == 'failed').count()
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting analysis statistics: {e}")
            return {}
    
    async def bulk_update_status(self, placeholder_ids: List[str], status: str) -> int:
        """批量更新状态"""
        try:
            count = self.session.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.id.in_(placeholder_ids)
            ).update(
                {'analysis_status': status},
                synchronize_session=False
            )
            self.session.commit()
            return count
            
        except Exception as e:
            self.logger.error(f"Error bulk updating status: {e}")
            self.session.rollback()
            return 0


class PlaceholderValueRepository(BaseRepository[PlaceholderValue]):
    """占位符值Repository"""
    
    def __init__(self, session: Session):
        super().__init__(session, PlaceholderValue)
    
    async def find_by_placeholder_id(self, placeholder_id: str) -> List[PlaceholderValue]:
        """根据占位符ID查找值"""
        return await self.list(filters={'placeholder_id': placeholder_id})
    
    async def find_latest_value(self, placeholder_id: str) -> Optional[PlaceholderValue]:
        """查找最新的值"""
        try:
            return self.session.query(PlaceholderValue).filter(
                PlaceholderValue.placeholder_id == placeholder_id
            ).order_by(PlaceholderValue.created_at.desc()).first()
            
        except Exception as e:
            self.logger.error(f"Error finding latest value for placeholder {placeholder_id}: {e}")
            return None
    
    async def find_by_execution_id(self, execution_id: str) -> List[PlaceholderValue]:
        """根据执行ID查找值"""
        return await self.list(filters={'execution_id': execution_id})
    
    async def get_value_history(self, placeholder_id: str, limit: int = 50) -> List[PlaceholderValue]:
        """获取值历史"""
        return await self.list(
            filters={'placeholder_id': placeholder_id},
            limit=limit,
            order_by='created_at',
            desc_order=True
        )
    
    async def clean_old_values(self, placeholder_id: str, keep_latest: int = 10) -> int:
        """清理旧值，保留最新的N个"""
        try:
            # 查找要保留的值的ID
            latest_values = self.session.query(PlaceholderValue).filter(
                PlaceholderValue.placeholder_id == placeholder_id
            ).order_by(PlaceholderValue.created_at.desc()).limit(keep_latest).all()
            
            if len(latest_values) < keep_latest:
                return 0  # 不需要清理
            
            keep_ids = [v.id for v in latest_values]
            
            # 删除其他值
            deleted_count = self.session.query(PlaceholderValue).filter(
                PlaceholderValue.placeholder_id == placeholder_id,
                ~PlaceholderValue.id.in_(keep_ids)
            ).delete(synchronize_session=False)
            
            self.session.commit()
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning old values for placeholder {placeholder_id}: {e}")
            self.session.rollback()
            return 0