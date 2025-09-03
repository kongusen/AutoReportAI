from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.models.notification import NotificationStatus, NotificationType, NotificationPriority


class NotificationAction(BaseModel):
    """通知动作配置"""
    label: str = Field(..., description="按钮文本")
    action_type: str = Field(..., description="动作类型：navigate, api_call, dismiss")
    action_data: Dict[str, Any] = Field(default_factory=dict, description="动作数据")
    variant: str = Field(default="default", description="按钮样式：default, primary, danger")


class NotificationBase(BaseModel):
    """通知基础模型"""
    user_id: str = Field(..., description="用户ID")
    type: NotificationType = Field(..., description="通知类型")
    priority: NotificationPriority = Field(default=NotificationPriority.NORMAL, description="优先级")
    title: Optional[str] = Field(None, description="标题")
    message: str = Field(..., description="消息内容")
    details: Optional[str] = Field(None, description="详细信息")
    persistent: bool = Field(default=False, description="是否持久化显示")
    auto_dismiss_seconds: Optional[int] = Field(None, description="自动消失秒数")
    related_task_id: Optional[int] = Field(None, description="关联任务ID")
    related_report_id: Optional[int] = Field(None, description="关联报告ID")
    related_data_source_id: Optional[int] = Field(None, description="关联数据源ID")
    extra_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    actions: Optional[List[NotificationAction]] = Field(default_factory=list, description="动作列表")
    expires_at: Optional[datetime] = Field(None, description="过期时间")


class NotificationCreate(NotificationBase):
    """创建通知请求"""
    pass


class NotificationUpdate(BaseModel):
    """更新通知请求"""
    status: Optional[NotificationStatus] = None
    read_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None


class NotificationResponse(NotificationBase):
    """通知响应"""
    id: str = Field(..., description="通知ID")
    status: NotificationStatus = Field(..., description="状态")
    created_at: datetime = Field(..., description="创建时间")
    sent_at: Optional[datetime] = Field(None, description="发送时间")
    read_at: Optional[datetime] = Field(None, description="已读时间")
    dismissed_at: Optional[datetime] = Field(None, description="忽略时间")
    is_read: bool = Field(..., description="是否已读")
    is_expired: bool = Field(..., description="是否已过期")
    
    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """通知列表响应"""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int
    page: int
    size: int
    has_more: bool


class NotificationPreferenceBase(BaseModel):
    """通知偏好基础模型"""
    enable_websocket: bool = Field(default=True, description="启用WebSocket实时通知")
    enable_email: bool = Field(default=True, description="启用邮件通知")
    enable_browser: bool = Field(default=True, description="启用浏览器通知")
    enable_sound: bool = Field(default=True, description="启用声音提示")
    enable_task_notifications: bool = Field(default=True, description="启用任务通知")
    enable_report_notifications: bool = Field(default=True, description="启用报告通知")
    enable_system_notifications: bool = Field(default=True, description="启用系统通知")
    enable_error_notifications: bool = Field(default=True, description="启用错误通知")
    quiet_hours_start: Optional[str] = Field(None, description="免打扰开始时间 HH:MM", pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    quiet_hours_end: Optional[str] = Field(None, description="免打扰结束时间 HH:MM", pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    max_notifications_per_day: int = Field(default=50, description="每日最大通知数", ge=1, le=100)


class NotificationPreferenceCreate(NotificationPreferenceBase):
    """创建通知偏好"""
    user_id: str = Field(..., description="用户ID")


class NotificationPreferenceUpdate(NotificationPreferenceBase):
    """更新通知偏好"""
    pass


class NotificationPreferenceResponse(NotificationPreferenceBase):
    """通知偏好响应"""
    user_id: str = Field(..., description="用户ID")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    class Config:
        from_attributes = True


class NotificationStatsResponse(BaseModel):
    """通知统计响应"""
    total_notifications: int = Field(..., description="总通知数")
    unread_count: int = Field(..., description="未读数量")
    today_count: int = Field(..., description="今日通知数")
    this_week_count: int = Field(..., description="本周通知数")
    by_type: Dict[str, int] = Field(..., description="按类型统计")
    by_status: Dict[str, int] = Field(..., description="按状态统计")


class BulkNotificationCreate(BaseModel):
    """批量创建通知"""
    user_ids: List[str] = Field(..., description="用户ID列表")
    notification: NotificationBase = Field(..., description="通知内容")


class NotificationTemplateBase(BaseModel):
    """通知模板基础"""
    name: str = Field(..., description="模板名称")
    type: NotificationType = Field(..., description="通知类型")
    title_template: str = Field(..., description="标题模板")
    message_template: str = Field(..., description="消息模板")
    details_template: Optional[str] = Field(None, description="详情模板")
    default_priority: NotificationPriority = Field(default=NotificationPriority.NORMAL)
    default_persistent: bool = Field(default=False)
    default_auto_dismiss_seconds: Optional[int] = Field(None)


class NotificationTemplateResponse(NotificationTemplateBase):
    """通知模板响应"""
    id: int = Field(..., description="模板ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    class Config:
        from_attributes = True


class WebSocketNotificationMessage(BaseModel):
    """WebSocket通知消息格式"""
    type: str = Field(default="notification", description="消息类型")
    data: NotificationResponse = Field(..., description="通知数据")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间戳")