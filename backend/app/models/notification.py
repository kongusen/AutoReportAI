from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum as SqlEnum, JSON
from sqlalchemy.sql import func
from enum import Enum

from app.db.base_class import Base


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    READ = "read"
    DISMISSED = "dismissed"


class NotificationType(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    TASK_UPDATE = "task_update"
    REPORT_READY = "report_ready"
    SYSTEM = "system"


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Notification(Base):
    """通知数据模型"""
    
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True, comment="接收用户ID")
    
    # 通知基本信息
    type = Column(SqlEnum(NotificationType), nullable=False, comment="通知类型")
    priority = Column(SqlEnum(NotificationPriority), default=NotificationPriority.NORMAL, comment="优先级")
    status = Column(SqlEnum(NotificationStatus), default=NotificationStatus.PENDING, comment="状态")
    
    # 通知内容
    title = Column(String(500), comment="标题")
    message = Column(Text, nullable=False, comment="消息内容")
    details = Column(Text, comment="详细信息")
    
    # 行为配置
    persistent = Column(Boolean, default=False, comment="是否持久化显示")
    auto_dismiss_seconds = Column(Integer, comment="自动消失秒数")
    
    # 关联信息
    related_task_id = Column(Integer, comment="关联任务ID")
    related_report_id = Column(Integer, comment="关联报告ID")
    related_data_source_id = Column(Integer, comment="关联数据源ID")
    
    # 扩展数据
    extra_data = Column(JSON, comment="元数据，存储额外信息")
    actions = Column(JSON, comment="动作配置，按钮等")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    sent_at = Column(DateTime(timezone=True), comment="发送时间")
    read_at = Column(DateTime(timezone=True), comment="已读时间")
    dismissed_at = Column(DateTime(timezone=True), comment="忽略时间")
    expires_at = Column(DateTime(timezone=True), comment="过期时间")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "type": self.type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "title": self.title,
            "message": self.message,
            "details": self.details,
            "persistent": self.persistent,
            "auto_dismiss_seconds": self.auto_dismiss_seconds,
            "related_task_id": self.related_task_id,
            "related_report_id": self.related_report_id,
            "related_data_source_id": self.related_data_source_id,
            "extra_data": self.extra_data,
            "actions": self.actions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "dismissed_at": self.dismissed_at.isoformat() if self.dismissed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
    
    @property
    def is_read(self) -> bool:
        """是否已读"""
        return self.status in [NotificationStatus.READ, NotificationStatus.DISMISSED]
    
    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def mark_as_sent(self):
        """标记为已发送"""
        if self.status == NotificationStatus.PENDING:
            self.status = NotificationStatus.SENT
            self.sent_at = datetime.utcnow()
    
    def mark_as_read(self):
        """标记为已读"""
        if self.status in [NotificationStatus.PENDING, NotificationStatus.SENT]:
            self.status = NotificationStatus.READ
            self.read_at = datetime.utcnow()
    
    def mark_as_dismissed(self):
        """标记为已忽略"""
        if self.status in [NotificationStatus.PENDING, NotificationStatus.SENT, NotificationStatus.READ]:
            self.status = NotificationStatus.DISMISSED
            self.dismissed_at = datetime.utcnow()


class NotificationPreference(Base):
    """用户通知偏好设置"""
    
    __tablename__ = "notification_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, unique=True, index=True, comment="用户ID")
    
    # 推送渠道开关
    enable_websocket = Column(Boolean, default=True, comment="启用WebSocket实时通知")
    enable_email = Column(Boolean, default=True, comment="启用邮件通知")
    enable_browser = Column(Boolean, default=True, comment="启用浏览器通知")
    enable_sound = Column(Boolean, default=True, comment="启用声音提示")
    
    # 通知类型开关
    enable_task_notifications = Column(Boolean, default=True, comment="启用任务通知")
    enable_report_notifications = Column(Boolean, default=True, comment="启用报告通知")
    enable_system_notifications = Column(Boolean, default=True, comment="启用系统通知")
    enable_error_notifications = Column(Boolean, default=True, comment="启用错误通知")
    
    # 高级设置
    quiet_hours_start = Column(String(5), comment="免打扰开始时间 HH:MM")
    quiet_hours_end = Column(String(5), comment="免打扰结束时间 HH:MM")
    max_notifications_per_day = Column(Integer, default=50, comment="每日最大通知数")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": self.user_id,
            "enable_websocket": self.enable_websocket,
            "enable_email": self.enable_email,
            "enable_browser": self.enable_browser,
            "enable_sound": self.enable_sound,
            "enable_task_notifications": self.enable_task_notifications,
            "enable_report_notifications": self.enable_report_notifications,
            "enable_system_notifications": self.enable_system_notifications,
            "enable_error_notifications": self.enable_error_notifications,
            "quiet_hours_start": self.quiet_hours_start,
            "quiet_hours_end": self.quiet_hours_end,
            "max_notifications_per_day": self.max_notifications_per_day,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }