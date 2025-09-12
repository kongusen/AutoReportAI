import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from app.core.time_utils import now, format_iso
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.db.session import get_db
from app.services.infrastructure.notification.email_service import EmailService
from app.core.api_specification import NotificationMessage
from app.models.notification import NotificationType, NotificationPriority
from app.schemas.notification import NotificationCreate

logger = logging.getLogger(__name__)


class NotificationService:
    """基于Claude Code架构的现代化通知服务"""
    
    def __init__(self):
        self.email_service = EmailService()
        self._active_connections: Dict[str, Any] = {}
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        self._initialized = False
    
    async def initialize(self):
        """初始化通知服务"""
        if not self._initialized:
            try:
                # Service orchestrator migrated to agents
                from app.services.infrastructure.agents import execute_agent_task
                self.orchestrator = execute_agent_task
                self._initialized = True
                logger.info("ServiceOrchestrator通知服务初始化成功")
            except Exception as e:
                logger.error(f"通知服务初始化失败: {str(e)}")
                raise
    
    async def add_connection(self, user_id: str, websocket):
        """添加WebSocket连接"""
        await self.initialize()
        self._active_connections[user_id] = websocket
        logger.info(f"用户 {user_id} WebSocket连接已建立")
    
    async def remove_connection(self, user_id: str):
        """移除WebSocket连接"""
        if user_id in self._active_connections:
            del self._active_connections[user_id]
            logger.info(f"用户 {user_id} WebSocket连接已断开")
    
    async def send_direct_message(self, user_id: str, message: Dict[str, Any]):
        """直接发送消息给特定用户"""
        if user_id in self._active_connections:
            try:
                websocket = self._active_connections[user_id]
                await websocket.send_text(json.dumps(message))
                return True
            except Exception as e:
                logger.error(f"发送消息失败: {str(e)}")
                await self.remove_connection(user_id)
        return False
    
    async def generate_intelligent_message(self, event_type: str, context: Dict[str, Any]) -> str:
        """使用React Agent生成智能通知消息"""
        try:
            await self.initialize()
            
            prompt = f"""
            生成 {event_type} 事件的通知消息。
            
            上下文信息: {json.dumps(context, ensure_ascii=False)}
            
            请生成一个简洁、专业、友好的通知消息。
            """
            
            # 使用ServiceOrchestrator进行智能消息生成
            result = await self.orchestrator.analyze_template_simple(
                user_id="system",
                template_id="notification_generation",
                template_content=prompt,
                data_source_info={
                    "task_type": "notification_generation",
                    "event_type": event_type,
                    **context
                }
            )
            return result.get("suggestions", f"{event_type} 事件通知")
        except Exception as e:
            logger.error(f"智能消息生成失败: {str(e)}")
            return f"{event_type} 事件通知"

    async def notify_task_started(
        self, db: Session, task_id: int, user_id: str, task_name: str
    ):
        """通知任务开始执行"""
        try:
            # 检查用户通知偏好
            if not crud.notification_preference.is_notification_allowed(
                db, user_id, NotificationType.TASK_UPDATE, "websocket"
            ):
                return
            
            message = await self.generate_intelligent_message("task_started", {
                "task_id": task_id,
                "task_name": task_name,
                "user_id": user_id
            })
            
            # 保存到数据库
            notification_data = NotificationCreate(
                user_id=user_id,
                type=NotificationType.TASK_UPDATE,
                priority=NotificationPriority.NORMAL,
                title="任务开始",
                message=message,
                related_task_id=task_id,
                persistent=False,
                auto_dismiss_seconds=10,
                metadata={"task_name": task_name, "event": "task_started"}
            )
            
            notification = crud.notification.create(db=db, obj_in=notification_data)
            
            # 发送WebSocket通知
            websocket_notification = {
                "type": "notification",
                "data": {
                    "id": str(notification.id),
                    "type": notification.type.value,
                    "title": notification.title,
                    "message": notification.message,
                    "timestamp": notification.created_at.isoformat(),
                    "metadata": notification.metadata
                }
            }
            
            if settings.ENABLE_WEBSOCKET_NOTIFICATIONS:
                await self.send_direct_message(user_id, websocket_notification)

            logger.info(f"Task {task_id} start notification sent to user {user_id}")
        except Exception as e:
            logger.error(f"Error sending task start notification: {e}")

    async def notify_task_completed(
        self, db: Session, task_id: int, user_id: str, task_name: str, result_data: Dict = None
    ):
        """通知任务完成"""
        try:
            # 检查用户通知偏好
            if not crud.notification_preference.is_notification_allowed(
                db, user_id, NotificationType.TASK_UPDATE, "websocket"
            ):
                return
            
            message = await self.generate_intelligent_message("task_completed", {
                "task_id": task_id,
                "task_name": task_name,
                "user_id": user_id,
                "result_data": result_data
            })
            
            # 保存到数据库
            notification_data = NotificationCreate(
                user_id=user_id,
                type=NotificationType.TASK_UPDATE,
                priority=NotificationPriority.NORMAL,
                title="任务完成",
                message=message,
                related_task_id=task_id,
                persistent=True,
                metadata={"task_name": task_name, "event": "task_completed", "result_data": result_data}
            )
            
            notification = crud.notification.create(db=db, obj_in=notification_data)
            
            # 发送WebSocket通知
            websocket_notification = {
                "type": "notification",
                "data": {
                    "id": str(notification.id),
                    "type": notification.type.value,
                    "title": notification.title,
                    "message": notification.message,
                    "timestamp": notification.created_at.isoformat(),
                    "metadata": notification.metadata
                }
            }
            
            if settings.ENABLE_WEBSOCKET_NOTIFICATIONS:
                await self.send_direct_message(user_id, websocket_notification)

            # 发送邮件通知
            await self._send_email_notification(db, user_id, notification, result_data)

            logger.info(f"Task {task_id} completion notification sent to user {user_id}")
        except Exception as e:
            logger.error(f"Error sending task completion notification: {e}")

    async def notify_task_failed(
        self, db: Session, task_id: int, user_id: str, task_name: str, error_message: str
    ):
        """通知任务失败"""
        try:
            message = await self.generate_intelligent_message("task_failed", {
                "task_id": task_id,
                "task_name": task_name,
                "user_id": user_id,
                "error_message": error_message
            })
            
            notification = {
                "type": "task_notification",
                "event": "task_failed",
                "task_id": task_id,
                "task_name": task_name,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "error_message": error_message
            }
            
            if settings.ENABLE_WEBSOCKET_NOTIFICATIONS:
                await self.send_direct_message(user_id, notification)

            logger.info(f"Task {task_id} failure notification sent to user {user_id}")
        except Exception as e:
            logger.error(f"Error sending task failure notification: {e}")

    async def notify_report_generated(
        self, db: Session, report_id: int, user_id: str, report_name: str, 
        report_path: str = None, task_info: Dict = None
    ):
        """通知报告生成完成"""
        try:
            # 检查用户通知偏好
            if not crud.notification_preference.is_notification_allowed(
                db, user_id, NotificationType.REPORT_READY, "websocket"
            ):
                return
            
            message = await self.generate_intelligent_message("report_generated", {
                "report_id": report_id,
                "report_name": report_name,
                "user_id": user_id,
                "task_info": task_info
            })
            
            # 保存到数据库
            notification_data = NotificationCreate(
                user_id=user_id,
                type=NotificationType.REPORT_READY,
                priority=NotificationPriority.HIGH,
                title="报告已生成",
                message=message,
                related_report_id=report_id,
                persistent=True,
                metadata={"report_name": report_name, "event": "report_generated", "task_info": task_info}
            )
            
            notification = crud.notification.create(db=db, obj_in=notification_data)
            
            # 发送WebSocket通知
            websocket_notification = {
                "type": "notification",
                "data": {
                    "id": str(notification.id),
                    "type": notification.type.value,
                    "title": notification.title,
                    "message": notification.message,
                    "timestamp": notification.created_at.isoformat(),
                    "metadata": notification.metadata
                }
            }
            
            if settings.ENABLE_WEBSOCKET_NOTIFICATIONS:
                await self.send_direct_message(user_id, websocket_notification)

            # 发送邮件通知和报告文件
            await self._send_report_email(db, user_id, report_name, report_path, task_info)

            logger.info(f"Report {report_id} generation notification sent to user {user_id}")
        except Exception as e:
            logger.error(f"Error sending report generation notification: {e}")

    async def notify_system_maintenance(
        self, maintenance_message: str, affected_users: List[str] = None
    ):
        """通知系统维护"""
        try:
            message = await self.generate_intelligent_message("system_maintenance", {
                "maintenance_message": maintenance_message,
                "affected_users_count": len(affected_users) if affected_users else 0
            })
            
            notification = {
                "type": "system_notification",
                "event": "system_maintenance",
                "message": message,
                "maintenance_message": maintenance_message,
                "timestamp": datetime.now().isoformat()
            }
            
            if settings.ENABLE_WEBSOCKET_NOTIFICATIONS:
                if affected_users:
                    for user_id in affected_users:
                        await self.send_direct_message(user_id, notification)
                else:
                    # 广播给所有连接的用户
                    for user_id in self._active_connections.keys():
                        await self.send_direct_message(user_id, notification)

            logger.info("System maintenance notification sent")
        except Exception as e:
            logger.error(f"Error sending system maintenance notification: {e}")

    async def _send_email_notification(self, db: Session, user_id: str, notification, result_data: Dict = None):
        """发送邮件通知的内部方法"""
        try:
            # 检查邮件通知偏好
            if not crud.notification_preference.is_notification_allowed(
                db, user_id, notification.type, "email"
            ):
                return
            
            # 获取用户信息
            from app import crud
            user = crud.crud_user.get(db, id=user_id)
            if not user or not user.email:
                logger.warning(f"User {user_id} not found or no email")
                return
            
            # 发送邮件
            self.email_service.send_notification_email(
                to_emails=[user.email],
                notification_type=notification.type.value,
                title=notification.title,
                message=notification.message,
                details=notification.details,
                metadata=notification.metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    async def _send_report_email(self, db: Session, user_id: str, report_name: str, 
                                report_path: str = None, task_info: Dict = None):
        """发送报告邮件的内部方法"""
        try:
            # 检查邮件通知偏好
            if not crud.notification_preference.is_notification_allowed(
                db, user_id, NotificationType.REPORT_READY, "email"
            ):
                return
            
            # 获取用户信息
            from app import crud
            user = crud.crud_user.get(db, id=user_id)
            if not user or not user.email:
                logger.warning(f"User {user_id} not found or no email")
                return
            
            # 发送带附件的报告邮件
            if report_path:
                self.email_service.send_report_with_attachment(
                    to_emails=[user.email],
                    report_name=report_name,
                    report_path=report_path,
                    task_info=task_info
                )
            else:
                # 发送无附件的报告完成通知
                self.email_service.send_notification_email(
                    to_emails=[user.email],
                    notification_type="report_ready",
                    title=f"报告已生成: {report_name}",
                    message=f"您的报告 '{report_name}' 已经生成完成。",
                    metadata={"report_name": report_name, "task_info": task_info}
                )
            
        except Exception as e:
            logger.error(f"Failed to send report email: {e}")
    
    async def _send_task_email(self, db: Session, user_id: str, task_name: str, 
                              status: str, message: str, task_id: int = None, 
                              error_message: str = None):
        """发送任务邮件的内部方法"""
        try:
            # 检查邮件通知偏好
            notification_type = NotificationType.ERROR if status == "failed" else NotificationType.TASK_UPDATE
            if not crud.notification_preference.is_notification_allowed(
                db, user_id, notification_type, "email"
            ):
                return
            
            # 获取用户信息
            from app import crud
            user = crud.crud_user.get(db, id=user_id)
            if not user or not user.email:
                logger.warning(f"User {user_id} not found or no email")
                return
            
            # 发送任务状态邮件
            self.email_service.send_task_notification_email(
                to_emails=[user.email],
                task_name=task_name,
                status=status,
                message=message,
                task_id=task_id,
                error_message=error_message
            )
            
        except Exception as e:
            logger.error(f"Failed to send task email: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            await self.initialize()
            email_healthy = self.email_service.test_connection()
            
            return {
                "status": "healthy",
                "active_connections": len(self._active_connections),
                "agent_initialized": self._initialized,
                "email_service_healthy": email_healthy,
                "service_type": "react_agent_notification_service"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "service_type": "react_agent_notification_service"
            }


# 全局通知服务实例 - 基于Claude Code架构
_notification_service = None

def get_notification_service() -> NotificationService:
    """获取通知服务实例"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service