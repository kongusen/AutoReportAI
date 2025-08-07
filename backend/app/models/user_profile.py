from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )

    # 用户偏好设置
    language = Column(String(10), default="zh-CN")
    theme = Column(String(20), default="light")
    email_notifications = Column(Boolean, default=True)
    report_notifications = Column(Boolean, default=True)
    system_notifications = Column(Boolean, default=True)
    default_storage_days = Column(Integer, default=90)
    auto_cleanup_enabled = Column(Boolean, default=True)
    default_report_format = Column(String(10), default="pdf")
    default_ai_provider = Column(String(100), nullable=True)
    custom_css = Column(Text, nullable=True)
    dashboard_layout = Column(Text, nullable=True)

    # 系统设置
    timezone = Column(String(50), default="Asia/Shanghai")
    date_format = Column(String(20), default="YYYY-MM-DD")

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系定义
    user = relationship("User", back_populates="profile")
