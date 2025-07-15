from typing import Optional
from pydantic import BaseModel, Field


class UserProfileBase(BaseModel):
    """用户配置基础模型"""
    language: str = Field(default="zh-CN", description="界面语言")
    theme: str = Field(default="light", description="主题设置")
    email_notifications: bool = Field(default=True, description="邮件通知")
    report_notifications: bool = Field(default=True, description="报告通知")
    system_notifications: bool = Field(default=True, description="系统通知")
    default_storage_days: int = Field(default=90, ge=1, le=365, description="默认存储天数")
    auto_cleanup_enabled: bool = Field(default=True, description="自动清理")
    default_report_format: str = Field(default="pdf", description="默认报告格式")
    default_ai_provider: Optional[str] = Field(None, description="默认AI提供商")
    custom_css: Optional[str] = Field(None, description="自定义CSS")
    dashboard_layout: Optional[str] = Field(None, description="仪表板布局配置")


class UserProfileCreate(UserProfileBase):
    """创建用户配置"""
    pass


class UserProfileUpdate(UserProfileBase):
    """更新用户配置"""
    pass


class UserProfile(UserProfileBase):
    """用户配置响应模型"""
    id: int
    user_id: int
    
    class Config:
        from_attributes = True
