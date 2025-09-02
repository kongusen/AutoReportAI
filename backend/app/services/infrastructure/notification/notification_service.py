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

logger = logging.getLogger(__name__)


class ReactAgentNotificationService:
    """基于React Agent架构的现代化通知服务"""
    
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
                from app.services.infrastructure.ai.agents import create_react_agent
                self.agent = create_react_agent(user_id="notification_system")
                await self.agent.initialize()
                self._initialized = True
                logger.info("React Agent通知服务初始化成功")
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
            
            return await self.agent.chat(prompt, context={
                "task_type": "notification_generation",
                "event_type": event_type,
                **context
            })
        except Exception as e:
            logger.error(f"智能消息生成失败: {str(e)}")
            return f"{event_type} 事件通知"

    async def notify_task_started(
        self, db: Session, task_id: int, user_id: str, task_name: str
    ):
        """通知任务开始执行"""
        try:
            message = await self.generate_intelligent_message("task_started", {
                "task_id": task_id,
                "task_name": task_name,
                "user_id": user_id
            })
            
            notification = {
                "type": "task_notification",
                "event": "task_started", 
                "task_id": task_id,
                "task_name": task_name,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id
            }
            
            if settings.ENABLE_WEBSOCKET_NOTIFICATIONS:
                await self.send_direct_message(user_id, notification)

            logger.info(f"Task {task_id} start notification sent to user {user_id}")
        except Exception as e:
            logger.error(f"Error sending task start notification: {e}")

    async def notify_task_completed(
        self, db: Session, task_id: int, user_id: str, task_name: str, result_data: Dict = None
    ):
        """通知任务完成"""
        try:
            message = await self.generate_intelligent_message("task_completed", {
                "task_id": task_id,
                "task_name": task_name,
                "user_id": user_id,
                "result_data": result_data
            })
            
            notification = {
                "type": "task_notification",
                "event": "task_completed",
                "task_id": task_id,
                "task_name": task_name,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "result_data": result_data
            }
            
            if settings.ENABLE_WEBSOCKET_NOTIFICATIONS:
                await self.send_direct_message(user_id, notification)

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
        self, db: Session, report_id: int, user_id: str, report_name: str
    ):
        """通知报告生成完成"""
        try:
            message = await self.generate_intelligent_message("report_generated", {
                "report_id": report_id,
                "report_name": report_name,
                "user_id": user_id
            })
            
            notification = {
                "type": "report_notification",
                "event": "report_generated",
                "report_id": report_id,
                "report_name": report_name,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id
            }
            
            if settings.ENABLE_WEBSOCKET_NOTIFICATIONS:
                await self.send_direct_message(user_id, notification)

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

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            await self.initialize()
            return {
                "status": "healthy",
                "active_connections": len(self._active_connections),
                "agent_initialized": self._initialized,
                "service_type": "react_agent_notification_service"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "service_type": "react_agent_notification_service"
            }


# 全局通知服务实例 - 基于React Agent架构
_notification_service = None

def get_notification_service() -> ReactAgentNotificationService:
    """获取通知服务实例"""
    global _notification_service
    if _notification_service is None:
        _notification_service = ReactAgentNotificationService()
    return _notification_service

# React Agent架构的通知服务类型别名
NotificationService = ReactAgentNotificationService