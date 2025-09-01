"""
Data Source CRUD operations
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text

from ..models.data_source import DataSource
from ..schemas.data_source import DataSourceCreate, DataSourceUpdate
from .base import CRUDBase
from ..core.data_source_utils import generate_slug
from ..core.security_utils import encrypt_data


class CRUDDataSource(CRUDBase[DataSource, DataSourceCreate, DataSourceUpdate]):
    """Data Source CRUD operations class"""

    def get_by_user(
        self, db: Session, *, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[DataSource]:
        """Get data sources by user ID"""
        return (
            db.query(DataSource)
            .filter(DataSource.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_name(
        self, db: Session, *, name: str, user_id: UUID
    ) -> Optional[DataSource]:
        """Get data source by name and user ID"""
        return (
            db.query(DataSource)
            .filter(
                DataSource.name == name,
                DataSource.user_id == user_id,
            )
            .first()
        )

    def get_active_by_user(
        self, db: Session, *, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[DataSource]:
        """Get active data sources by user ID"""
        return (
            db.query(DataSource)
            .filter(
                DataSource.user_id == user_id,
                DataSource.is_active == True,
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_with_user(self, db: Session, *, obj_in: DataSourceCreate, user_id: UUID) -> DataSource:
        obj_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
        obj_data['user_id'] = user_id
        
        # 加密敏感信息
        if obj_data.get('connection_string'):
            obj_data['connection_string'] = encrypt_data(obj_data['connection_string'])
        
        if obj_data.get('doris_password'):
            obj_data['doris_password'] = encrypt_data(obj_data['doris_password'])
        
        # 生成用户友好的slug（如果没有提供）
        if not obj_data.get('slug') and obj_data.get('name'):
            obj_data['slug'] = generate_slug(obj_data['name'], user_id, db)
        
        # 设置默认display_name（如果没有提供）
        if not obj_data.get('display_name'):
            obj_data['display_name'] = obj_data.get('name')
        
        db_obj = DataSource(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_user_data_source(self, db: Session, *, data_source_id: str, user_id: UUID) -> Optional[DataSource]:
        """获取用户的特定数据源"""
        return db.query(DataSource).filter(
            DataSource.id == data_source_id,
            DataSource.user_id == user_id,
            DataSource.is_active == True
        ).first()
        
    def update(self, db: Session, db_obj: DataSource, obj_in) -> DataSource:
        """更新数据源"""
        if hasattr(obj_in, 'model_dump'):
            # Pydantic model
            update_data = obj_in.model_dump(exclude_unset=True)
        else:
            # 字典
            update_data = obj_in
        
        # 加密敏感信息
        if update_data.get('connection_string'):
            update_data['connection_string'] = encrypt_data(update_data['connection_string'])
        
        if update_data.get('doris_password'):
            update_data['doris_password'] = encrypt_data(update_data['doris_password'])
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_count(self, db: Session) -> int:
        """获取所有数据源总数"""
        return db.query(DataSource).count()
    
    def get_count_by_user(self, db: Session, user_id: UUID) -> int:
        """获取用户数据源总数"""
        return db.query(DataSource).filter(DataSource.user_id == user_id).count()

# 顶层独立函数，支持直接导入

def get_wide_table_data(db: Session, table_name: str, limit: int = 100, offset: int = 0):
    sql = text(f"SELECT * FROM {table_name} LIMIT :limit OFFSET :offset")
    result = db.execute(sql, {"limit": limit, "offset": offset})
    rows = result.fetchall()
    fields = result.keys()
    return list(fields), [list(row) for row in rows]

crud_data_source = CRUDDataSource(DataSource)
