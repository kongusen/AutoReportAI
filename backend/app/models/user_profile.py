from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # 用户偏好设置
    language = Column(String(10), default="zh-CN")
    theme = Column(String(20), default="auto")
    email_notifications = Column(Boolean, default=True)
    default_report_format = Column(String(10), default="pdf")
    custom_css = Column(Text)
    
    # 系统设置
    timezone = Column(String(50), default="Asia/Shanghai")
    date_format = Column(String(20), default="YYYY-MM-DD")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系 - 临时注释以修复CI/CD
    # user = relationship("User", back_populates="profile")
