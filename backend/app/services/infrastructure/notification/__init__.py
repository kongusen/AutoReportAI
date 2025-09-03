"""
notification 服务模块

提供 notification 相关的业务逻辑处理
"""

# 模块版本
__version__ = "1.0.0"

# 导入核心组件
from .email_service import EmailService
from .notification_service import ReactAgentNotificationService, get_notification_service

# 向后兼容
NotificationService = ReactAgentNotificationService

# 模块导出
__all__ = [
    "EmailService",
    "ReactAgentNotificationService",
    "NotificationService",
    "get_notification_service"
]