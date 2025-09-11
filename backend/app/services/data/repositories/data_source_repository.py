"""
Data Source Repository

数据源数据访问层，提供数据源相关的专业化查询方法
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.data_source import DataSource
from .base_repository import BaseRepository, TransactionalRepository

logger = logging.getLogger(__name__)


class DataSourceRepository(TransactionalRepository[DataSource]):
    """数据源Repository"""
    
    def __init__(self, session: Session):
        super().__init__(session, DataSource)
    
    async def find_by_user_id(self, user_id: str, include_inactive: bool = False) -> List[DataSource]:
        """根据用户ID查找数据源"""
        filters = {'user_id': user_id}
        
        if not include_inactive:
            filters['is_active'] = True
        
        return await self.list(
            filters=filters,
            order_by='name'
        )
    
    async def find_by_type(self, source_type: str, user_id: str = None) -> List[DataSource]:
        """根据数据源类型查找"""
        filters = {
            'source_type': source_type,
            'is_active': True
        }
        
        if user_id:
            filters['user_id'] = user_id
        
        return await self.list(filters=filters)
    
    async def find_by_name(self, name: str, user_id: str = None) -> Optional[DataSource]:
        """根据名称查找数据源"""
        filters = {'name': name}
        
        if user_id:
            filters['user_id'] = user_id
        
        return await self.find_one(**filters)
    
    async def find_active_sources(self, user_id: str = None) -> List[DataSource]:
        """查找活跃的数据源"""
        filters = {'is_active': True}
        
        if user_id:
            filters['user_id'] = user_id
        
        return await self.list(
            filters=filters,
            order_by='last_used_at',
            desc_order=True
        )
    
    async def find_recently_used(self, user_id: str, limit: int = 10) -> List[DataSource]:
        """查找最近使用的数据源"""
        return await self.list(
            filters={
                'user_id': user_id,
                'is_active': True,
                'last_used_at': {'ne': None}
            },
            limit=limit,
            order_by='last_used_at',
            desc_order=True
        )
    
    async def test_connection_status(self, data_source_id: str) -> Dict[str, Any]:
        """测试连接状态（占位符方法，实际实现需要连接测试逻辑）"""
        try:
            data_source = await self.get_by_id(data_source_id)
            if not data_source:
                return {'status': 'error', 'message': 'Data source not found'}
            
            # 这里应该实现实际的连接测试逻辑
            # 目前返回占位符状态
            return {
                'status': 'success',
                'message': 'Connection test successful',
                'timestamp': data_source.updated_at
            }
            
        except Exception as e:
            self.logger.error(f"Error testing connection for data source {data_source_id}: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def update_last_used(self, data_source_id: str) -> bool:
        """更新最后使用时间"""
        try:
            data_source = await self.get_by_id(data_source_id)
            if not data_source:
                return False
            
            data_source.last_used_at = datetime.utcnow()
            await self.update_and_commit(data_source)
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating last used time for {data_source_id}: {e}")
            return False
    
    async def update_connection_config(self, data_source_id: str, 
                                     config: Dict[str, Any]) -> bool:
        """更新连接配置"""
        try:
            data_source = await self.get_by_id(data_source_id)
            if not data_source:
                return False
            
            # 合并配置，而不是完全替换
            current_config = data_source.connection_config or {}
            current_config.update(config)
            
            data_source.connection_config = current_config
            await self.update_and_commit(data_source)
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating connection config for {data_source_id}: {e}")
            return False
    
    async def get_statistics(self, user_id: str = None) -> Dict[str, Any]:
        """获取数据源统计信息"""
        try:
            base_query = self.session.query(DataSource)
            
            if user_id:
                base_query = base_query.filter(DataSource.user_id == user_id)
            
            total = base_query.count()
            active = base_query.filter(DataSource.is_active == True).count()
            
            # 按类型统计
            type_stats = {}
            for source_type in ['mysql', 'postgresql', 'doris', 'api', 'csv']:
                count = base_query.filter(DataSource.source_type == source_type).count()
                if count > 0:
                    type_stats[source_type] = count
            
            return {
                'total': total,
                'active': active,
                'inactive': total - active,
                'by_type': type_stats
            }
            
        except Exception as e:
            self.logger.error(f"Error getting data source statistics: {e}")
            return {}
    
    async def find_similar_sources(self, data_source_id: str, 
                                 similarity_threshold: float = 0.8) -> List[DataSource]:
        """查找相似的数据源（基于配置相似性）"""
        try:
            current_source = await self.get_by_id(data_source_id)
            if not current_source:
                return []
            
            # 查找相同类型的数据源
            similar_sources = await self.find_by_type(
                current_source.source_type, 
                current_source.user_id
            )
            
            # 过滤掉当前数据源
            similar_sources = [s for s in similar_sources if s.id != data_source_id]
            
            # TODO: 实现更复杂的相似性计算
            # 目前简单返回同类型的数据源
            return similar_sources
            
        except Exception as e:
            self.logger.error(f"Error finding similar sources for {data_source_id}: {e}")
            return []
    
    async def bulk_activate_sources(self, data_source_ids: List[str]) -> int:
        """批量激活数据源"""
        try:
            count = self.session.query(DataSource).filter(
                DataSource.id.in_(data_source_ids)
            ).update(
                {'is_active': True},
                synchronize_session=False
            )
            self.session.commit()
            return count
            
        except Exception as e:
            self.logger.error(f"Error bulk activating sources: {e}")
            self.session.rollback()
            return 0
    
    async def bulk_deactivate_sources(self, data_source_ids: List[str]) -> int:
        """批量停用数据源"""
        try:
            count = self.session.query(DataSource).filter(
                DataSource.id.in_(data_source_ids)
            ).update(
                {'is_active': False},
                synchronize_session=False
            )
            self.session.commit()
            return count
            
        except Exception as e:
            self.logger.error(f"Error bulk deactivating sources: {e}")
            self.session.rollback()
            return 0