"""
CRUD operations for PlaceholderValue

占位符值CRUD操作 - 精简版（针对100占位符场景优化）
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.crud.base import CRUDBase
from app.models.template_placeholder import PlaceholderValue
from app.schemas.placeholder_value import PlaceholderValueCreate, PlaceholderValueUpdate


class CRUDPlaceholderValue(CRUDBase[PlaceholderValue, PlaceholderValueCreate, PlaceholderValueUpdate]):
    """占位符值CRUD操作"""

    def create_batch(
        self,
        db: Session,
        *,
        values: List[PlaceholderValueCreate]
    ) -> List[PlaceholderValue]:
        """
        批量创建占位符值（100条数据优化）

        Args:
            db: 数据库会话
            values: 要创建的占位符值列表

        Returns:
            创建的占位符值列表
        """
        db_objs = [PlaceholderValue(**value.dict()) for value in values]
        db.add_all(db_objs)  # 批量添加
        db.flush()  # 刷新但不提交，由调用方统一管理事务
        return db_objs

    def get_by_batch_id(
        self,
        db: Session,
        *,
        batch_id: str
    ) -> List[PlaceholderValue]:
        """
        根据批次ID获取所有占位符值

        Args:
            db: 数据库会话
            batch_id: 批次ID

        Returns:
            占位符值列表
        """
        return db.query(self.model).filter(
            PlaceholderValue.execution_batch_id == batch_id
        ).all()

    def get_by_placeholder_and_source(
        self,
        db: Session,
        *,
        placeholder_id: str,
        data_source_id: str,
        is_latest: bool = True
    ) -> Optional[PlaceholderValue]:
        """
        获取指定占位符和数据源的值

        Args:
            db: 数据库会话
            placeholder_id: 占位符ID
            data_source_id: 数据源ID
            is_latest: 是否只获取最新版本

        Returns:
            占位符值或None
        """
        query = db.query(self.model).filter(
            PlaceholderValue.placeholder_id == placeholder_id,
            PlaceholderValue.data_source_id == data_source_id
        )

        if is_latest:
            query = query.filter(PlaceholderValue.is_latest_version == True)

        return query.order_by(PlaceholderValue.created_at.desc()).first()

    def get_cached_value(
        self,
        db: Session,
        *,
        cache_key: str
    ) -> Optional[PlaceholderValue]:
        """
        根据缓存键获取有效缓存

        Args:
            db: 数据库会话
            cache_key: 缓存键

        Returns:
            缓存的占位符值或None
        """
        return db.query(self.model).filter(
            PlaceholderValue.cache_key == cache_key,
            PlaceholderValue.expires_at > datetime.utcnow(),
            PlaceholderValue.success == True
        ).first()

    def mark_as_outdated(
        self,
        db: Session,
        *,
        placeholder_id: str,
        data_source_id: str
    ) -> int:
        """
        将占位符的旧值标记为过期

        Args:
            db: 数据库会话
            placeholder_id: 占位符ID
            data_source_id: 数据源ID

        Returns:
            更新的记录数
        """
        count = db.query(self.model).filter(
            PlaceholderValue.placeholder_id == placeholder_id,
            PlaceholderValue.data_source_id == data_source_id
        ).update({"is_latest_version": False}, synchronize_session=False)
        return count

    def cleanup_old_versions(
        self,
        db: Session,
        *,
        placeholder_id: str,
        keep_versions: int = 10
    ) -> int:
        """
        清理旧版本，保留最新N个

        Args:
            db: 数据库会话
            placeholder_id: 占位符ID
            keep_versions: 保留的版本数

        Returns:
            删除的记录数
        """
        # 查找要保留的版本ID
        keep_ids = db.query(self.model.id).filter(
            PlaceholderValue.placeholder_id == placeholder_id
        ).order_by(
            PlaceholderValue.created_at.desc()
        ).limit(keep_versions).all()

        keep_ids = [id[0] for id in keep_ids]

        # 删除其他版本
        if keep_ids:
            deleted = db.query(self.model).filter(
                PlaceholderValue.placeholder_id == placeholder_id,
                ~PlaceholderValue.id.in_(keep_ids)
            ).delete(synchronize_session=False)
            return deleted
        return 0


placeholder_value = CRUDPlaceholderValue(PlaceholderValue)
