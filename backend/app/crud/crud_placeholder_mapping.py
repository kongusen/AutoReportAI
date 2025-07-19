"""
占位符映射CRUD操作
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..models.placeholder_mapping import PlaceholderMapping
from ..schemas.placeholder_mapping import (
    PlaceholderMappingCreate,
    PlaceholderMappingUpdate,
)
from .base import CRUDBase


class CRUDPlaceholderMapping(
    CRUDBase[PlaceholderMapping, PlaceholderMappingCreate, PlaceholderMappingUpdate]
):
    """占位符映射CRUD操作类"""

    def get_by_signature(
        self, db: Session, *, signature: str, data_source_id: int
    ) -> Optional[PlaceholderMapping]:
        """根据签名和数据源ID获取映射"""
        return (
            db.query(PlaceholderMapping)
            .filter(
                PlaceholderMapping.placeholder_signature == signature,
                PlaceholderMapping.data_source_id == data_source_id,
            )
            .first()
        )

    def get_by_data_source(
        self, db: Session, *, data_source_id: int, limit: int = 100
    ) -> List[PlaceholderMapping]:
        """根据数据源ID获取映射列表"""
        return (
            db.query(PlaceholderMapping)
            .filter(PlaceholderMapping.data_source_id == data_source_id)
            .order_by(desc(PlaceholderMapping.last_used_at))
            .limit(limit)
            .all()
        )

    def update_usage(
        self, db: Session, *, db_obj: PlaceholderMapping
    ) -> PlaceholderMapping:
        """更新使用次数"""
        db_obj.usage_count += 1
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_popular_mappings(
        self, db: Session, *, data_source_id: int, limit: int = 50
    ) -> List[PlaceholderMapping]:
        """获取热门映射"""
        return (
            db.query(PlaceholderMapping)
            .filter(PlaceholderMapping.data_source_id == data_source_id)
            .order_by(desc(PlaceholderMapping.usage_count))
            .limit(limit)
            .all()
        )


crud_placeholder_mapping = CRUDPlaceholderMapping(PlaceholderMapping)
