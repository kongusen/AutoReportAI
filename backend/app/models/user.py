from sqlalchemy import Boolean, Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=True)  # 添加缺失的username字段
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    full_name = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系 - 临时简化以修复CI/CD
    # profile = relationship("UserProfile", back_populates="user", uselist=False)
    # templates = relationship("Template", back_populates="user")
    # enhanced_data_sources = relationship("EnhancedDataSource", back_populates="user")
    # etl_jobs = relationship("ETLJob", back_populates="user")
    # tasks = relationship("Task", back_populates="user")
    # report_histories = relationship("ReportHistory", back_populates="user")
    # ai_providers = relationship("AIProvider", back_populates="user")
