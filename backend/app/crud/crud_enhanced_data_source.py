"""
Enhanced Data Source CRUD operations
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.enhanced_data_source import EnhancedDataSource
from ..schemas.enhanced_data_source import (
    EnhancedDataSourceCreate,
    EnhancedDataSourceUpdate,
)
from .base import CRUDBase


class CRUDEnhancedDataSource(
    CRUDBase[EnhancedDataSource, EnhancedDataSourceCreate, EnhancedDataSourceUpdate]
):
    """Enhanced Data Source CRUD operations class"""

    def get_by_user(
        self, db: Session, *, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[EnhancedDataSource]:
        """Get enhanced data sources by user ID"""
        return (
            db.query(EnhancedDataSource)
            .filter(EnhancedDataSource.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_name(
        self, db: Session, *, name: str, user_id: UUID
    ) -> Optional[EnhancedDataSource]:
        """Get enhanced data source by name and user ID"""
        return (
            db.query(EnhancedDataSource)
            .filter(
                EnhancedDataSource.name == name,
                EnhancedDataSource.user_id == user_id,
            )
            .first()
        )

    def get_active_by_user(
        self, db: Session, *, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[EnhancedDataSource]:
        """Get active enhanced data sources by user ID"""
        return (
            db.query(EnhancedDataSource)
            .filter(
                EnhancedDataSource.user_id == user_id,
                EnhancedDataSource.is_active == True,
            )
            .offset(skip)
            .limit(limit)
            .all()
        )


crud_enhanced_data_source = CRUDEnhancedDataSource(EnhancedDataSource)