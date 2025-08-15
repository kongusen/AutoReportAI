"""
Notification Utils

通知工具，负责：
- 任务相关通知
- 通知格式化
- 通知发送
"""

import logging
from typing import Any, Dict, Optional

from app.services.notification.notification_service import NotificationService

logger = logging.getLogger(__name__)


class NotificationUtils:
    """通知工具类"""
    
    def __init__(self):
        self.notification_service = NotificationService()
    
    def send_task_started_notification(
        self,
        task_id: int,
        task_name: str,
        user_id: str
    ) -> bool:
        """
        发送任务开始通知
        
        Args:
            task_id: 任务ID
            task_name: 任务名称
            user_id: 用户ID
            
        Returns:
            是否发送成功
        """
        try:
            message = f"任务 '{task_name}' 已开始执行"
            
            self.notification_service.send_task_notification(
                task_id=task_id,
                task_name=task_name,
                message=message,
                user_id=user_id,
                notification_type="task_started"
            )
            
            logger.info(f"任务开始通知已发送 - 任务ID: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"发送任务开始通知失败 - 任务ID: {task_id}: {e}")
            return False
    
    def send_task_completed_notification(
        self,
        task_id: int,
        task_name: str,
        user_id: str,
        execution_time: float,
        report_path: Optional[str] = None
    ) -> bool:
        """
        发送任务完成通知
        
        Args:
            task_id: 任务ID
            task_name: 任务名称
            user_id: 用户ID
            execution_time: 执行时间
            report_path: 报告文件路径
            
        Returns:
            是否发送成功
        """
        try:
            message = f"任务 '{task_name}' 已完成，执行时间: {execution_time:.2f}秒"
            
            if report_path:
                message += f"，报告文件: {report_path}"
            
            self.notification_service.send_task_notification(
                task_id=task_id,
                task_name=task_name,
                message=message,
                user_id=user_id,
                notification_type="task_completed",
                extra_data={
                    "execution_time": execution_time,
                    "report_path": report_path
                }
            )
            
            logger.info(f"任务完成通知已发送 - 任务ID: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"发送任务完成通知失败 - 任务ID: {task_id}: {e}")
            return False
    
    def send_task_failed_notification(
        self,
        task_id: int,
        task_name: str,
        user_id: str,
        error_message: str
    ) -> bool:
        """
        发送任务失败通知
        
        Args:
            task_id: 任务ID
            task_name: 任务名称
            user_id: 用户ID
            error_message: 错误信息
            
        Returns:
            是否发送成功
        """
        try:
            message = f"任务 '{task_name}' 执行失败: {error_message}"
            
            self.notification_service.send_task_notification(
                task_id=task_id,
                task_name=task_name,
                message=message,
                user_id=user_id,
                notification_type="task_failed",
                extra_data={
                    "error_message": error_message
                }
            )
            
            logger.info(f"任务失败通知已发送 - 任务ID: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"发送任务失败通知失败 - 任务ID: {task_id}: {e}")
            return False
    
    def send_task_progress_notification(
        self,
        task_id: int,
        task_name: str,
        user_id: str,
        progress: int,
        current_step: str
    ) -> bool:
        """
        发送任务进度通知
        
        Args:
            task_id: 任务ID
            task_name: 任务名称
            user_id: 用户ID
            progress: 进度百分比
            current_step: 当前步骤
            
        Returns:
            是否发送成功
        """
        try:
            # 只在关键进度点发送通知
            if progress in [25, 50, 75]:
                message = f"任务 '{task_name}' 进度: {progress}% - {current_step}"
                
                self.notification_service.send_task_notification(
                    task_id=task_id,
                    task_name=task_name,
                    message=message,
                    user_id=user_id,
                    notification_type="task_progress",
                    extra_data={
                        "progress": progress,
                        "current_step": current_step
                    }
                )
                
                logger.debug(f"任务进度通知已发送 - 任务ID: {task_id}, 进度: {progress}%")
            
            return True
            
        except Exception as e:
            logger.error(f"发送任务进度通知失败 - 任务ID: {task_id}: {e}")
            return False
    
    def send_system_notification(
        self,
        title: str,
        message: str,
        user_id: Optional[str] = None,
        notification_type: str = "system"
    ) -> bool:
        """
        发送系统通知
        
        Args:
            title: 通知标题
            message: 通知内容
            user_id: 用户ID（可选）
            notification_type: 通知类型
            
        Returns:
            是否发送成功
        """
        try:
            self.notification_service.send_system_notification(
                title=title,
                message=message,
                user_id=user_id,
                notification_type=notification_type
            )
            
            logger.info(f"系统通知已发送 - 标题: {title}")
            return True
            
        except Exception as e:
            logger.error(f"发送系统通知失败: {e}")
            return False
    
    def format_task_notification_message(
        self,
        task_name: str,
        status: str,
        extra_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        格式化任务通知消息
        
        Args:
            task_name: 任务名称
            status: 任务状态
            extra_info: 额外信息
            
        Returns:
            格式化的消息
        """
        base_message = f"任务 '{task_name}' {status}"
        
        if extra_info:
            if "execution_time" in extra_info:
                base_message += f"，执行时间: {extra_info['execution_time']:.2f}秒"
            
            if "error_message" in extra_info:
                base_message += f"，错误: {extra_info['error_message']}"
            
            if "progress" in extra_info:
                base_message += f"，进度: {extra_info['progress']}%"
        
        return base_message
