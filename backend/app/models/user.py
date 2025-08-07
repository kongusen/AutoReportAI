import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(
        String, unique=True, index=True, nullable=True
    )  # 添加缺失的username字段
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    full_name = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系定义
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    templates = relationship("Template", back_populates="user")
    data_sources = relationship("DataSource", back_populates="user")
    etl_jobs = relationship("ETLJob", back_populates="user")
    tasks = relationship("Task", back_populates="owner")
    report_histories = relationship("ReportHistory", back_populates="user")
    ai_providers = relationship("AIProvider", back_populates="user")

    # 学习系统关系
    processing_history = relationship(
        "PlaceholderProcessingHistory", back_populates="user"
    )
    error_logs = relationship("ErrorLog", back_populates="user")
    feedbacks = relationship("UserFeedback", back_populates="user")
    llm_call_logs = relationship("LLMCallLog", back_populates="user")
    quality_scores = relationship("ReportQualityScore", back_populates="user")
