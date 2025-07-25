"""
优化的数据源CRUD操作
"""

from typing import List, Optional, Union
from uuid import UUID
from sqlalchemy.orm import Session

from app.crud.base_optimized import CRUDComplete
from app.models.optimized.data_source import DataSource, DataSourceType, ConnectionStatus
from app.schemas.data_source import DataSourceCreate, DataSourceUpdate


class CRUDDataSource(CRUDComplete[DataSource, DataSourceCreate, DataSourceUpdate]):
    """数据源CRUD操作类"""
    
    def __init__(self):
        super().__init__(DataSource, search_fields=["name", "description"])
    
    def get_by_type(
        self, 
        db: Session, 
        *, 
        source_type: DataSourceType,
        user_id: Union[UUID, str] = None,
        include_inactive: bool = False
    ) -> List[DataSource]:
        """根据类型获取数据源"""
        query = db.query(self.model).filter(self.model.source_type == source_type)
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        if not include_inactive:
            query = query.filter(self.model.is_active == True)
        
        if hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
        
        return query.all()
    
    def get_by_status(
        self,
        db: Session,
        *,
        status: ConnectionStatus,
        user_id: Union[UUID, str] = None
    ) -> List[DataSource]:
        """根据连接状态获取数据源"""
        query = db.query(self.model).filter(self.model.status == status)
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        if hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
        
        return query.all()
    
    def get_database_sources(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None
    ) -> List[DataSource]:
        """获取数据库类型的数据源"""
        database_types = [
            DataSourceType.POSTGRESQL,
            DataSourceType.MYSQL,
            DataSourceType.DORIS,
            DataSourceType.CLICKHOUSE
        ]
        
        query = db.query(self.model).filter(self.model.source_type.in_(database_types))
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        query = query.filter(
            self.model.is_active == True,
            self.model.is_deleted == False
        )
        
        return query.all()
    
    def update_connection_status(
        self,
        db: Session,
        *,
        data_source_id: Union[UUID, str],
        status: ConnectionStatus,
        error_message: str = None
    ) -> Optional[DataSource]:
        """更新连接状态"""
        data_source = self.get(db, id=data_source_id)
        if not data_source:
            return None
        
        from datetime import datetime
        
        data_source.status = status
        data_source.last_tested_at = datetime.utcnow().isoformat()
        
        if status == ConnectionStatus.FAILED and error_message:
            if not data_source.metadata:
                data_source.metadata = {}
            data_source.metadata["last_error"] = error_message
        elif status == ConnectionStatus.CONNECTED:
            # 清除错误信息
            if data_source.metadata and "last_error" in data_source.metadata:
                del data_source.metadata["last_error"]
        
        db.add(data_source)
        db.commit()
        db.refresh(data_source)
        
        return data_source
    
    def get_healthy_sources(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None
    ) -> List[DataSource]:
        """获取健康的数据源"""
        query = db.query(self.model).filter(
            self.model.status == ConnectionStatus.CONNECTED,
            self.model.is_active == True,
            self.model.is_deleted == False
        )
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        return query.all()
    
    def search_by_tags(
        self,
        db: Session,
        *,
        tags: List[str],
        user_id: Union[UUID, str] = None
    ) -> List[DataSource]:
        """根据标签搜索数据源"""
        query = db.query(self.model).filter(self.model.is_deleted == False)
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        # 使用JSON操作符查询包含指定标签的数据源
        for tag in tags:
            query = query.filter(self.model.tags.contains([tag]))
        
        return query.all()
    
    def get_connection_summary(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None
    ) -> dict:
        """获取连接状态摘要"""
        base_query = db.query(self.model).filter(self.model.is_deleted == False)
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            base_query = base_query.filter(self.model.user_id == user_id)
        
        summary = {
            "total": base_query.count(),
            "active": base_query.filter(self.model.is_active == True).count(),
            "connected": base_query.filter(self.model.status == ConnectionStatus.CONNECTED).count(),
            "failed": base_query.filter(self.model.status == ConnectionStatus.FAILED).count(),
            "pending": base_query.filter(self.model.status == ConnectionStatus.PENDING).count(),
            "by_type": {}
        }
        
        # 按类型统计
        for source_type in DataSourceType:
            count = base_query.filter(self.model.source_type == source_type).count()
            if count > 0:
                summary["by_type"][source_type.value] = count
        
        return summary


# 创建CRUD实例
crud_data_source = CRUDDataSource()