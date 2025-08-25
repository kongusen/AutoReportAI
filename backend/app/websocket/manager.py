import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect
from app.core.time_utils import format_iso

logger = logging.getLogger(__name__)


class NotificationMessage:
    def __init__(
        self,
        type: str,
        title: str,
        message: str,
        data: Optional[dict] = None,
        user_id: Optional[str] = None,
    ):
        self.id = str(uuid.uuid4())
        self.type = type  # 'info', 'success', 'warning', 'error'
        self.title = title
        self.message = message
        self.data = data or {}
        self.user_id = user_id
        self.timestamp = format_iso()

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class ConnectionManager:
    def __init__(self):
        # 存储活跃连接: {user_id: [websocket_connections]}
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # 存储连接到用户的映射: {websocket: user_id}
        self.connection_user_map: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """接受WebSocket连接并关联用户"""
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = []

        self.active_connections[user_id].append(websocket)
        self.connection_user_map[websocket] = user_id

        logger.info(f"User {user_id} connected via WebSocket")

        # 发送连接成功消息
        await self.send_personal_message(
            NotificationMessage(
                type="info",
                title="Connected",
                message="Real-time notifications are now active",
                user_id=user_id,
            ),
            user_id,
        )

    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        user_id = self.connection_user_map.get(websocket)
        if user_id:
            if user_id in self.active_connections:
                self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]

            del self.connection_user_map[websocket]
            logger.info(f"User {user_id} disconnected from WebSocket")

    async def send_to_user(self, user_id: str, message_dict: dict):
        """发送消息字典给特定用户"""
        if user_id in self.active_connections:
            message_data = json.dumps(message_dict)
            disconnected_connections = []

            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message_data)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected_connections.append(connection)

            # 清理断开的连接
            for connection in disconnected_connections:
                self.disconnect(connection)

    async def send_personal_message(self, message: NotificationMessage, user_id: str):
        """发送消息给特定用户"""
        if user_id in self.active_connections:
            message_data = json.dumps(message.to_dict())
            disconnected_connections = []

            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message_data)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected_connections.append(connection)

            # 清理断开的连接
            for connection in disconnected_connections:
                self.disconnect(connection)

    async def broadcast_message(self, message: NotificationMessage):
        """广播消息给所有连接的用户"""
        message_data = json.dumps(message.to_dict())
        disconnected_connections = []

        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_text(message_data)
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {e}")
                    disconnected_connections.append(connection)

        # 清理断开的连接
        for connection in disconnected_connections:
            self.disconnect(connection)

    async def send_task_notification(
        self, task_id: int, user_id: str, status: str, message: str
    ):
        """发送任务相关通知"""
        notification_type = (
            "success"
            if status == "completed"
            else "error" if status == "failed" else "info"
        )

        notification = NotificationMessage(
            type=notification_type,
            title=f"Task #{task_id} {status.title()}",
            message=message,
            data={"task_id": task_id, "status": status},
            user_id=user_id,
        )

        await self.send_personal_message(notification, user_id)

    async def send_report_notification(
        self, report_id: int, user_id: str, status: str, file_path: Optional[str] = None
    ):
        """发送报告生成通知"""
        if status == "completed":
            notification = NotificationMessage(
                type="success",
                title="Report Generated Successfully",
                message=f"Your report #{report_id} has been generated and is ready for download.",
                data={"report_id": report_id, "file_path": file_path},
                user_id=user_id,
            )
        elif status == "failed":
            notification = NotificationMessage(
                type="error",
                title="Report Generation Failed",
                message=f"Failed to generate report #{report_id}. Please check the logs for details.",
                data={"report_id": report_id},
                user_id=user_id,
            )
        else:
            notification = NotificationMessage(
                type="info",
                title="Report Generation Started",
                message=f"Report #{report_id} generation has started.",
                data={"report_id": report_id},
                user_id=user_id,
            )

        await self.send_personal_message(notification, user_id)

    async def send_system_notification(
        self, title: str, message: str, notification_type: str = "info"
    ):
        """发送系统通知给所有用户"""
        notification = NotificationMessage(
            type=notification_type, title=title, message=message
        )

        await self.broadcast_message(notification)

    def get_connected_users(self) -> List[str]:
        """获取当前连接的用户列表"""
        return list(self.active_connections.keys())

    def is_user_connected(self, user_id: str) -> bool:
        """检查用户是否在线"""
        return (
            user_id in self.active_connections
            and len(self.active_connections[user_id]) > 0
        )


# 全局连接管理器实例
manager = ConnectionManager()
