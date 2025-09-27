"""
流水线WebSocket通知服务
为占位符流水线任务提供实时状态更新
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass

from app.websocket.manager import websocket_manager
from app.core.api_specification import WebSocketMessage, WebSocketMessageType, TaskUpdateMessage

logger = logging.getLogger(__name__)


class PipelineTaskStatus(str, Enum):
    """流水线任务状态"""
    PENDING = "pending"
    SCANNING = "scanning"
    ANALYZING = "analyzing"
    ASSEMBLING = "assembling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineTaskType(str, Enum):
    """流水线任务类型"""
    ETL_SCAN = "etl_scan"
    REPORT_ASSEMBLY = "report_assembly"
    HEALTH_CHECK = "health_check"
    TEMPLATE_ANALYSIS = "template_analysis"


@dataclass
class PipelineTaskUpdate:
    """流水线任务更新数据"""
    task_id: str
    task_type: PipelineTaskType
    status: PipelineTaskStatus
    progress: float  # 0.0 - 1.0
    message: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PipelineNotificationService:
    """流水线通知服务"""

    def __init__(self):
        self.active_tasks: Dict[str, PipelineTaskUpdate] = {}
        self.task_subscribers: Dict[str, List[str]] = {}  # task_id -> [user_ids]

    async def start_task(
        self,
        task_id: str,
        task_type: PipelineTaskType,
        user_id: str,
        initial_message: str = "任务开始",
        template_id: Optional[str] = None,
        data_source_id: Optional[str] = None
    ) -> None:
        """开始任务并发送通知"""

        task_update = PipelineTaskUpdate(
            task_id=task_id,
            task_type=task_type,
            status=PipelineTaskStatus.PENDING,
            progress=0.0,
            message=initial_message,
            details={
                "template_id": template_id,
                "data_source_id": data_source_id,
                "user_id": user_id
            },
            started_at=datetime.now()
        )

        self.active_tasks[task_id] = task_update

        # 注册用户订阅
        if task_id not in self.task_subscribers:
            self.task_subscribers[task_id] = []
        if user_id not in self.task_subscribers[task_id]:
            self.task_subscribers[task_id].append(user_id)

        await self._send_task_update(task_id, task_update)

        logger.info(f"Pipeline task started: {task_id} ({task_type.value}) for user {user_id}")

    async def update_task_progress(
        self,
        task_id: str,
        status: PipelineTaskStatus,
        progress: float,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """更新任务进度"""

        if task_id not in self.active_tasks:
            logger.warning(f"Attempt to update unknown task: {task_id}")
            return

        task_update = self.active_tasks[task_id]
        task_update.status = status
        task_update.progress = min(max(progress, 0.0), 1.0)  # 确保在0-1范围内
        task_update.message = message

        if details:
            task_update.details = {**(task_update.details or {}), **details}

        # 如果任务完成或失败，记录完成时间
        if status in [PipelineTaskStatus.COMPLETED, PipelineTaskStatus.FAILED, PipelineTaskStatus.CANCELLED]:
            task_update.completed_at = datetime.now()

        await self._send_task_update(task_id, task_update)

        logger.debug(f"Task progress updated: {task_id} - {status.value} ({progress:.1%}) - {message}")

    async def task_error(
        self,
        task_id: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """任务错误"""

        if task_id not in self.active_tasks:
            logger.warning(f"Attempt to error unknown task: {task_id}")
            return

        task_update = self.active_tasks[task_id]
        task_update.status = PipelineTaskStatus.FAILED
        task_update.error = error_message
        task_update.message = f"任务失败: {error_message}"
        task_update.completed_at = datetime.now()

        if error_details:
            task_update.details = {**(task_update.details or {}), "error_details": error_details}

        await self._send_task_update(task_id, task_update)

        logger.error(f"Pipeline task error: {task_id} - {error_message}")

    async def complete_task(
        self,
        task_id: str,
        result_data: Optional[Dict[str, Any]] = None,
        message: str = "任务完成"
    ) -> None:
        """完成任务"""

        if task_id not in self.active_tasks:
            logger.warning(f"Attempt to complete unknown task: {task_id}")
            return

        task_update = self.active_tasks[task_id]
        task_update.status = PipelineTaskStatus.COMPLETED
        task_update.progress = 1.0
        task_update.message = message
        task_update.completed_at = datetime.now()

        if result_data:
            task_update.details = {**(task_update.details or {}), "result": result_data}

        await self._send_task_update(task_id, task_update)

        # 延迟清理任务（保留一段时间以便客户端获取最终状态）
        asyncio.create_task(self._cleanup_task_after_delay(task_id, delay_seconds=300))

        logger.info(f"Pipeline task completed: {task_id}")

    async def subscribe_to_task(self, task_id: str, user_id: str) -> bool:
        """订阅任务更新"""

        if task_id not in self.task_subscribers:
            self.task_subscribers[task_id] = []

        if user_id not in self.task_subscribers[task_id]:
            self.task_subscribers[task_id].append(user_id)

        # 如果任务还在活跃状态，发送当前状态
        if task_id in self.active_tasks:
            await self._send_task_update_to_user(task_id, user_id, self.active_tasks[task_id])

        logger.debug(f"User {user_id} subscribed to task {task_id}")
        return True

    async def unsubscribe_from_task(self, task_id: str, user_id: str) -> bool:
        """取消订阅任务更新"""

        if task_id in self.task_subscribers and user_id in self.task_subscribers[task_id]:
            self.task_subscribers[task_id].remove(user_id)

            # 如果没有订阅者了，清理
            if not self.task_subscribers[task_id]:
                del self.task_subscribers[task_id]

            logger.debug(f"User {user_id} unsubscribed from task {task_id}")
            return True

        return False

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""

        if task_id not in self.active_tasks:
            return None

        task_update = self.active_tasks[task_id]
        return {
            "task_id": task_id,
            "task_type": task_update.task_type.value,
            "status": task_update.status.value,
            "progress": task_update.progress,
            "message": task_update.message,
            "details": task_update.details,
            "error": task_update.error,
            "started_at": task_update.started_at.isoformat() if task_update.started_at else None,
            "completed_at": task_update.completed_at.isoformat() if task_update.completed_at else None
        }

    async def list_user_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        """列出用户的任务"""

        user_tasks = []
        for task_id, task_update in self.active_tasks.items():
            if task_update.details and task_update.details.get("user_id") == user_id:
                user_tasks.append(await self.get_task_status(task_id))

        return user_tasks

    async def _send_task_update(self, task_id: str, task_update: PipelineTaskUpdate) -> None:
        """发送任务更新给所有订阅者"""

        if task_id not in self.task_subscribers:
            return

        # 构建WebSocket消息
        message_data = {
            "task_id": task_id,
            "task_type": task_update.task_type.value,
            "status": task_update.status.value,
            "progress": task_update.progress,
            "message": task_update.message,
            "timestamp": datetime.now().isoformat()
        }

        if task_update.details:
            message_data["details"] = task_update.details
        if task_update.error:
            message_data["error"] = task_update.error

        ws_message = WebSocketMessage(
            type=WebSocketMessageType.TASK_UPDATE,
            message=task_update.message,
            data=message_data
        )

        # 发送给所有订阅者
        sent_count = 0
        for user_id in self.task_subscribers[task_id]:
            count = await websocket_manager.send_to_user(user_id, ws_message)
            sent_count += count

        logger.debug(f"Task update sent to {sent_count} connections for task {task_id}")

    async def _send_task_update_to_user(
        self,
        task_id: str,
        user_id: str,
        task_update: PipelineTaskUpdate
    ) -> None:
        """发送任务更新给特定用户"""

        message_data = {
            "task_id": task_id,
            "task_type": task_update.task_type.value,
            "status": task_update.status.value,
            "progress": task_update.progress,
            "message": task_update.message,
            "timestamp": datetime.now().isoformat()
        }

        if task_update.details:
            message_data["details"] = task_update.details
        if task_update.error:
            message_data["error"] = task_update.error

        ws_message = WebSocketMessage(
            type=WebSocketMessageType.TASK_UPDATE,
            message=task_update.message,
            data=message_data
        )

        await websocket_manager.send_to_user(user_id, ws_message)

    async def _cleanup_task_after_delay(self, task_id: str, delay_seconds: int = 300) -> None:
        """延迟清理任务"""

        await asyncio.sleep(delay_seconds)

        if task_id in self.active_tasks:
            del self.active_tasks[task_id]

        if task_id in self.task_subscribers:
            del self.task_subscribers[task_id]

        logger.debug(f"Cleaned up task: {task_id}")

    async def broadcast_system_notification(
        self,
        message: str,
        notification_type: str = "info",
        data: Optional[Dict[str, Any]] = None
    ) -> int:
        """广播系统通知"""

        ws_message = WebSocketMessage(
            type=WebSocketMessageType.NOTIFICATION,
            message=message,
            data={
                "notification_type": notification_type,
                "timestamp": datetime.now().isoformat(),
                **(data or {})
            }
        )

        return await websocket_manager.broadcast_to_all(ws_message)

    def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计"""

        active_count = len(self.active_tasks)
        subscriber_count = sum(len(subs) for subs in self.task_subscribers.values())

        status_counts = {}
        for task_update in self.active_tasks.values():
            status = task_update.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "active_tasks": active_count,
            "total_subscribers": subscriber_count,
            "tasks_by_status": status_counts,
            "websocket_stats": websocket_manager.get_system_stats()
        }


# 全局服务实例
pipeline_notification_service = PipelineNotificationService()


# 便捷函数
async def notify_task_start(
    task_id: str,
    task_type: PipelineTaskType,
    user_id: str,
    message: str = "任务开始",
    **kwargs
) -> None:
    """启动任务通知"""
    await pipeline_notification_service.start_task(
        task_id, task_type, user_id, message, **kwargs
    )


async def notify_task_progress(
    task_id: str,
    status: PipelineTaskStatus,
    progress: float,
    message: str,
    **kwargs
) -> None:
    """任务进度通知"""
    await pipeline_notification_service.update_task_progress(
        task_id, status, progress, message, **kwargs
    )


async def notify_task_complete(
    task_id: str,
    result_data: Optional[Dict[str, Any]] = None,
    message: str = "任务完成"
) -> None:
    """任务完成通知"""
    await pipeline_notification_service.complete_task(task_id, result_data, message)


async def notify_task_error(
    task_id: str,
    error_message: str,
    error_details: Optional[Dict[str, Any]] = None
) -> None:
    """任务错误通知"""
    await pipeline_notification_service.task_error(task_id, error_message, error_details)