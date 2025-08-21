"""
Task Notification Service Implementation

任务通知服务实现
"""

import logging
from typing import Dict, Any

from ...application.interfaces.task_notification_interface import TaskNotificationInterface

logger = logging.getLogger(__name__)


class TaskNotificationService(TaskNotificationInterface):
    """任务通知服务实现"""
    
    def __init__(self):
        # 这里可以注入实际的通知服务
        self.notification_channels = {
            "email": True,
            "websocket": True,
            "database": True
        }
    
    async def send_task_created(self, task_id: str, task_name: str, owner_id: str):
        """发送任务创建通知"""
        try:
            notification_data = {
                "type": "task_created",
                "task_id": task_id,
                "task_name": task_name,
                "owner_id": owner_id,
                "message": f"任务 '{task_name}' 已创建成功",
                "timestamp": self._get_current_timestamp()
            }
            
            await self._send_notification(owner_id, notification_data)
            logger.info(f"Sent task created notification: {task_id}")
            
        except Exception as e:
            logger.error(f"Failed to send task created notification: {e}")
    
    async def send_task_updated(self, task_id: str, task_name: str, owner_id: str):
        """发送任务更新通知"""
        try:
            notification_data = {
                "type": "task_updated",
                "task_id": task_id,
                "task_name": task_name,
                "owner_id": owner_id,
                "message": f"任务 '{task_name}' 已更新",
                "timestamp": self._get_current_timestamp()
            }
            
            await self._send_notification(owner_id, notification_data)
            logger.info(f"Sent task updated notification: {task_id}")
            
        except Exception as e:
            logger.error(f"Failed to send task updated notification: {e}")
    
    async def send_task_deleted(self, task_id: str, task_name: str, owner_id: str):
        """发送任务删除通知"""
        try:
            notification_data = {
                "type": "task_deleted",
                "task_id": task_id,
                "task_name": task_name,
                "owner_id": owner_id,
                "message": f"任务 '{task_name}' 已删除",
                "timestamp": self._get_current_timestamp()
            }
            
            await self._send_notification(owner_id, notification_data)
            logger.info(f"Sent task deleted notification: {task_id}")
            
        except Exception as e:
            logger.error(f"Failed to send task deleted notification: {e}")
    
    async def send_task_activated(self, task_id: str, task_name: str, owner_id: str):
        """发送任务激活通知"""
        try:
            notification_data = {
                "type": "task_activated",
                "task_id": task_id,
                "task_name": task_name,
                "owner_id": owner_id,
                "message": f"任务 '{task_name}' 已激活",
                "timestamp": self._get_current_timestamp()
            }
            
            await self._send_notification(owner_id, notification_data)
            logger.info(f"Sent task activated notification: {task_id}")
            
        except Exception as e:
            logger.error(f"Failed to send task activated notification: {e}")
    
    async def send_task_deactivated(self, task_id: str, task_name: str, owner_id: str):
        """发送任务停用通知"""
        try:
            notification_data = {
                "type": "task_deactivated",
                "task_id": task_id,
                "task_name": task_name,
                "owner_id": owner_id,
                "message": f"任务 '{task_name}' 已停用",
                "timestamp": self._get_current_timestamp()
            }
            
            await self._send_notification(owner_id, notification_data)
            logger.info(f"Sent task deactivated notification: {task_id}")
            
        except Exception as e:
            logger.error(f"Failed to send task deactivated notification: {e}")
    
    async def send_execution_started(self, task_id: str, execution_id: str, owner_id: str):
        """发送执行开始通知"""
        try:
            notification_data = {
                "type": "execution_started",
                "task_id": task_id,
                "execution_id": execution_id,
                "owner_id": owner_id,
                "message": f"任务执行已开始",
                "timestamp": self._get_current_timestamp()
            }
            
            await self._send_notification(owner_id, notification_data)
            logger.info(f"Sent execution started notification: {task_id}/{execution_id}")
            
        except Exception as e:
            logger.error(f"Failed to send execution started notification: {e}")
    
    async def send_execution_completed(self, task_id: str, execution_id: str,
                                     result_data: Dict[str, Any], owner_id: str):
        """发送执行完成通知"""
        try:
            notification_data = {
                "type": "execution_completed",
                "task_id": task_id,
                "execution_id": execution_id,
                "owner_id": owner_id,
                "message": f"任务执行已完成",
                "result_summary": self._summarize_result(result_data),
                "timestamp": self._get_current_timestamp()
            }
            
            await self._send_notification(owner_id, notification_data)
            logger.info(f"Sent execution completed notification: {task_id}/{execution_id}")
            
        except Exception as e:
            logger.error(f"Failed to send execution completed notification: {e}")
    
    async def send_execution_failed(self, task_id: str, execution_id: str,
                                  error_message: str, owner_id: str):
        """发送执行失败通知"""
        try:
            notification_data = {
                "type": "execution_failed",
                "task_id": task_id,
                "execution_id": execution_id,
                "owner_id": owner_id,
                "message": f"任务执行失败",
                "error_message": error_message,
                "timestamp": self._get_current_timestamp()
            }
            
            await self._send_notification(owner_id, notification_data)
            logger.info(f"Sent execution failed notification: {task_id}/{execution_id}")
            
        except Exception as e:
            logger.error(f"Failed to send execution failed notification: {e}")
    
    async def send_execution_cancelled(self, task_id: str, execution_id: str, owner_id: str):
        """发送执行取消通知"""
        try:
            notification_data = {
                "type": "execution_cancelled",
                "task_id": task_id,
                "execution_id": execution_id,
                "owner_id": owner_id,
                "message": f"任务执行已取消",
                "timestamp": self._get_current_timestamp()
            }
            
            await self._send_notification(owner_id, notification_data)
            logger.info(f"Sent execution cancelled notification: {task_id}/{execution_id}")
            
        except Exception as e:
            logger.error(f"Failed to send execution cancelled notification: {e}")
    
    async def send_progress_update(self, task_id: str, execution_id: str,
                                 progress_data: Dict[str, Any], owner_id: str):
        """发送进度更新通知"""
        try:
            notification_data = {
                "type": "progress_update",
                "task_id": task_id,
                "execution_id": execution_id,
                "owner_id": owner_id,
                "progress": progress_data.get("progress", 0),
                "status": progress_data.get("status", "running"),
                "current_step": progress_data.get("current_step", "Processing..."),
                "timestamp": self._get_current_timestamp()
            }
            
            await self._send_notification(owner_id, notification_data)
            # 进度通知频率较高，使用debug级别
            logger.debug(f"Sent progress update notification: {task_id}/{execution_id}")
            
        except Exception as e:
            logger.error(f"Failed to send progress update notification: {e}")
    
    async def _send_notification(self, user_id: str, notification_data: Dict[str, Any]):
        """发送通知到各个渠道"""
        try:
            # WebSocket通知（实时）
            if self.notification_channels["websocket"]:
                await self._send_websocket_notification(user_id, notification_data)
            
            # 数据库通知（持久化）
            if self.notification_channels["database"]:
                await self._save_notification_to_database(user_id, notification_data)
            
            # 邮件通知（重要事件）
            if self.notification_channels["email"] and self._should_send_email(notification_data):
                await self._send_email_notification(user_id, notification_data)
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    async def _send_websocket_notification(self, user_id: str, notification_data: Dict[str, Any]):
        """发送WebSocket通知"""
        try:
            # 这里应该集成实际的WebSocket服务
            # 简化实现，记录日志
            logger.info(f"WebSocket notification sent to user {user_id}: {notification_data['type']}")
            
        except Exception as e:
            logger.error(f"Failed to send WebSocket notification: {e}")
    
    async def _save_notification_to_database(self, user_id: str, notification_data: Dict[str, Any]):
        """保存通知到数据库"""
        try:
            # 这里应该调用通知仓储服务保存到数据库
            # 简化实现，记录日志
            logger.info(f"Database notification saved for user {user_id}: {notification_data['type']}")
            
        except Exception as e:
            logger.error(f"Failed to save notification to database: {e}")
    
    async def _send_email_notification(self, user_id: str, notification_data: Dict[str, Any]):
        """发送邮件通知"""
        try:
            # 这里应该集成实际的邮件服务
            # 简化实现，记录日志
            logger.info(f"Email notification sent to user {user_id}: {notification_data['type']}")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    def _should_send_email(self, notification_data: Dict[str, Any]) -> bool:
        """判断是否应该发送邮件"""
        # 只有重要事件才发送邮件
        email_worthy_types = {
            "task_created",
            "execution_completed",
            "execution_failed",
            "task_deleted"
        }
        return notification_data["type"] in email_worthy_types
    
    def _summarize_result(self, result_data: Dict[str, Any]) -> str:
        """总结执行结果"""
        if not result_data:
            return "执行完成"
        
        summary_parts = []
        
        if "report_path" in result_data:
            summary_parts.append("报告已生成")
        
        if "execution_time" in result_data:
            exec_time = result_data["execution_time"]
            summary_parts.append(f"执行时间: {exec_time:.1f}秒")
        
        if "pipeline_mode" in result_data:
            mode = result_data["pipeline_mode"]
            summary_parts.append(f"执行模式: {mode}")
        
        return ", ".join(summary_parts) if summary_parts else "执行完成"
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.utcnow().isoformat()