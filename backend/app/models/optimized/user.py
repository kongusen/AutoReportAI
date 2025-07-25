"""
优化的用户模型
统一用户管理，移除冗余字段
"""

import enum
from sqlalchemy import Boolean, Column, Enum, String, Text, JSON
from sqlalchemy.orm import relationship

from app.db.base_class_optimized import BaseModel


class UserStatus(str, enum.Enum):
    """用户状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class UserRole(str, enum.Enum):
    """用户角色枚举"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class User(BaseModel):
    """用户模型"""
    
    __tablename__ = "user"
    
    # 基本信息
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=True)
    
    # 认证信息
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # 角色和权限
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING_VERIFICATION, nullable=False)
    
    # 个人设置
    preferences = Column(JSON, nullable=True)  # 用户偏好设置
    profile_settings = Column(JSON, nullable=True)  # 个人资料设置
    
    # 扩展信息
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    timezone = Column(String(50), default="UTC", nullable=False)
    language = Column(String(10), default="zh-CN", nullable=False)
    
    # 验证相关
    email_verification_token = Column(String(255), nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    
    # 关联关系
    data_sources = relationship("DataSource", back_populates="user", cascade="all, delete-orphan")
    templates = relationship("Template", back_populates="user", cascade="all, delete-orphan")
    etl_jobs = relationship("ETLJob", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    
    @property
    def is_admin(self) -> bool:
        """是否为管理员"""
        return self.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
    
    @property
    def is_super_admin(self) -> bool:
        """是否为超级管理员"""
        return self.role == UserRole.SUPER_ADMIN
    
    @property
    def display_name(self) -> str:
        """显示名称"""
        return self.full_name or self.username
    
    @property
    def is_email_verified(self) -> bool:
        """邮箱是否已验证"""
        return self.is_verified and not self.email_verification_token
    
    def get_preferences(self, key: str, default=None):
        """获取用户偏好设置"""
        if not self.preferences:
            return default
        return self.preferences.get(key, default)
    
    def set_preference(self, key: str, value):
        """设置用户偏好"""
        if not self.preferences:
            self.preferences = {}
        self.preferences[key] = value
    
    def has_permission(self, permission: str) -> bool:
        """检查用户权限"""
        if self.is_super_admin:
            return True
        
        # 基础权限检查
        admin_permissions = [
            "manage_users", "manage_system", "view_all_data", 
            "manage_ai_providers", "system_settings"
        ]
        
        if self.is_admin and permission in admin_permissions:
            return True
        
        # 普通用户权限
        user_permissions = [
            "create_data_source", "create_template", "create_report", 
            "view_own_data", "manage_own_profile"
        ]
        
        return permission in user_permissions
    
    def to_profile_dict(self) -> dict:
        """转换为个人资料字典"""
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "timezone": self.timezone,
            "language": self.language,
            "role": self.role.value,
            "status": self.status.value,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "preferences": self.preferences or {}
        }