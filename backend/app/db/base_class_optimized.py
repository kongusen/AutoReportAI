"""
优化的数据库基础类
提供统一的模型基类和软删除功能
"""

import uuid
from typing import Any, Dict
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Session


@as_declarative()
class Base:
    """基础模型类"""
    
    # 生成表名
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
    
    # 统一主键定义
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # 统一时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """从字典更新属性"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)


class SoftDeleteMixin:
    """软删除混入类"""
    
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    def soft_delete(self):
        """软删除"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
    
    def restore(self):
        """恢复"""
        self.is_deleted = False
        self.deleted_at = None
    
    @classmethod
    def active_query(cls, session: Session):
        """获取未删除的记录查询"""
        return session.query(cls).filter(cls.is_deleted == False)


class UserOwnedMixin:
    """用户所有权混入类"""
    
    @declared_attr
    def user_id(cls):
        from sqlalchemy import ForeignKey
        return Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False, index=True)
    
    @declared_attr
    def user(cls):
        from sqlalchemy.orm import relationship
        return relationship("User", back_populates=f"{cls.__name__.lower()}s")


class AuditMixin:
    """审计混入类"""
    
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    version = Column(String, default="1.0", nullable=False)
    
    def increment_version(self):
        """版本号递增"""
        try:
            major, minor = map(int, self.version.split('.'))
            self.version = f"{major}.{minor + 1}"
        except (ValueError, AttributeError):
            self.version = "1.1"


# 组合基类
class BaseModel(Base, SoftDeleteMixin, AuditMixin):
    """完整功能的基础模型"""
    __abstract__ = True


class UserOwnedModel(BaseModel, UserOwnedMixin):
    """用户拥有的模型基类"""
    __abstract__ = True