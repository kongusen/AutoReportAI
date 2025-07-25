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
        db_obj = DataSource(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

# 顶层独立函数，支持直接导入

def get_wide_table_data(db: Session, table_name: str, limit: int = 100, offset: int = 0):
    sql = text(f"SELECT * FROM {table_name} LIMIT :limit OFFSET :offset")
    result = db.execute(sql, {"limit": limit, "offset": offset})
    rows = result.fetchall()
    fields = result.keys()
    return list(fields), [list(row) for row in rows]

crud_data_source = CRUDDataSource(DataSource)
