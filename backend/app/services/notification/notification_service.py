import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.services.notification.email_service import EmailService
from app.websocket.manager import NotificationMessage, manager

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self):
        self.email_service = EmailService()
        self.websocket_manager = manager
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )

    async def notify_task_started(
        self, db: Session, task_id: int, user_id: str, task_name: str
    ):
        """通知任务开始执行"""
        try:
            # WebSocket通知
            if settings.ENABLE_WEBSOCKET_NOTIFICATIONS:
                await self.websocket_manager.send_task_notification(
                    task_id=task_id,
                    user_id=user_id,
                    status="started",
                    message=f"Task '{task_name}' has started execution.",
                )

            logger.info(f"Task {task_id} start notification sent to user {user_id}")
        except Exception as e:
            logger.error(f"Error sending task start notification: {e}")

    async def notify_task_completed(
        self,
        db: Session,
        task_id: int,
        user_id: str,
        task_name: str,
        report_path: Optional[str] = None,
    ):
        """通知任务完成"""
        try:
            # WebSocket通知
            if settings.ENABLE_WEBSOCKET_NOTIFICATIONS:
                await self.websocket_manager.send_task_notification(
                    task_id=task_id,
                    user_id=user_id,
                    status="completed",
                    message=f"Task '{task_name}' completed successfully. Report is ready for download.",
                )

            # 邮件通知
            if settings.ENABLE_EMAIL_NOTIFICATIONS:
                user = crud.user.get(db, id=user_id)
                if user and user.email:
                    # 检查用户通知偏好
                    if self._should_send_email_notification(
                        db, user_id, "report_completion"
                    ):
                        self.email_service.send_report_completion_notification(
                            to_emails=[user.email],
                            task_name=task_name,
                            report_path=report_path,
                        )

            logger.info(
                f"Task {task_id} completion notification sent to user {user_id}"
            )
        except Exception as e:
            logger.error(f"Error sending task completion notification: {e}")

    async def notify_task_failed(
        self,
        db: Session,
        task_id: int,
        user_id: str,
        task_name: str,
        error_message: str,
    ):
        """通知任务失败"""
        try:
            # WebSocket通知
            if settings.ENABLE_WEBSOCKET_NOTIFICATIONS:
                await self.websocket_manager.send_task_notification(
                    task_id=task_id,
                    user_id=user_id,
                    status="failed",
                    message=f"Task '{task_name}' failed: {error_message}",
                )

            # 邮件通知
            if settings.ENABLE_EMAIL_NOTIFICATIONS:
                user = crud.user.get(db, id=user_id)
                if user and user.email:
                    # 检查用户通知偏好
                    if self._should_send_email_notification(
                        db, user_id, "error_alerts"
                    ):
                        self.email_service.send_error_notification(
                            to_emails=[user.email],
                            task_name=task_name,
                            error_message=error_message,
                        )

            logger.info(f"Task {task_id} failure notification sent to user {user_id}")
        except Exception as e:
            logger.error(f"Error sending task failure notification: {e}")

    async def notify_report_generated(
        self, db: Session, report_id: int, user_id: str, file_path: Optional[str] = None
    ):
        """通知报告生成完成"""
        try:
            if settings.ENABLE_WEBSOCKET_NOTIFICATIONS:
                await self.websocket_manager.send_report_notification(
                    report_id=report_id,
                    user_id=user_id,
                    status="completed",
                    file_path=file_path,
                )

            logger.info(f"Report {report_id} notification sent to user {user_id}")
        except Exception as e:
            logger.error(f"Error sending report notification: {e}")

    async def notify_system_maintenance(
        self, title: str, message: str, notification_type: str = "info"
    ):
        """发送系统维护通知"""
        try:
            if settings.ENABLE_WEBSOCKET_NOTIFICATIONS:
                await self.websocket_manager.send_system_notification(
                    title=title, message=message, notification_type=notification_type
                )

            logger.info(f"System notification sent: {title}")
        except Exception as e:
            logger.error(f"Error sending system notification: {e}")

    async def send_weekly_summary(self, db: Session):
        """发送周报摘要"""
        try:
            if not settings.ENABLE_EMAIL_NOTIFICATIONS:
                return

            # 获取所有启用周报的用户
            users = crud.user.get_multi(db)

            for user in users:
                if not user.email:
                    continue

                # 检查用户是否启用了周报
                if not self._should_send_email_notification(
                    db, str(user.id), "weekly_summary"
                ):
                    continue

                # 获取用户的周报数据
                summary_data = self._get_user_weekly_summary(db, str(user.id))

                # 发送周报邮件
                self.email_service.send_weekly_summary(
                    to_emails=[user.email], summary_data=summary_data
                )

            logger.info("Weekly summary emails sent")
        except Exception as e:
            logger.error(f"Error sending weekly summary: {e}")

    def _should_send_email_notification(
        self, db: Session, user_id: str, notification_type: str
    ) -> bool:
        """检查用户是否启用了特定类型的邮件通知"""
        try:
            # 这里应该从用户配置表中查询通知偏好
            # 为了演示，我们假设所有通知都是启用的
            return True
        except Exception as e:
            logger.error(f"Error checking notification preference: {e}")
            return False

    def _get_user_weekly_summary(self, db: Session, user_id: str) -> dict:
        """获取用户的周报数据"""
        try:
            from datetime import datetime, timedelta

            # 获取过去一周的数据
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)

            # 查询用户的报告历史
            history_records = crud.report_history.get_multi_by_owner(
                db=db, owner_id=user_id, skip=0, limit=1000
            )

            # 过滤过去一周的记录
            weekly_records = [
                record
                for record in history_records
                if start_date <= record.created_at <= end_date
            ]

            total_reports = len(weekly_records)
            successful_reports = len(
                [r for r in weekly_records if r.status == "success"]
            )
            failed_reports = len([r for r in weekly_records if r.status == "failure"])

            return {
                "total_reports": total_reports,
                "successful_reports": successful_reports,
                "failed_reports": failed_reports,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            }
        except Exception as e:
            logger.error(f"Error getting weekly summary: {e}")
            return {"total_reports": 0, "successful_reports": 0, "failed_reports": 0}

    async def send_task_progress_update(
        self, 
        task_id: int, 
        progress_data: Dict[str, Any]
    ):
        """
        发送任务进度更新通知
        基于设计文档的实时通知系统
        """
        try:
            # 从Redis获取任务所有者信息
            task_owner_key = f"report_task:{task_id}:owner"
            user_id = await self.redis_client.get(task_owner_key)
            
            if not user_id:
                logger.warning(f"无法找到任务 {task_id} 的所有者")
                return
            
            # 构建通知消息
            notification = NotificationMessage(
                type="info",
                title=f"报告任务 #{task_id}",
                message=f"处理进度: {progress_data.get('progress', 0)}%",
                data={
                    "task_id": task_id,
                    "progress": progress_data.get("progress", 0),
                    "status": progress_data.get("status"),
                    "current_step": progress_data.get("current_step"),
                    "updated_at": progress_data.get("updated_at")
                },
                user_id=user_id
            )
            
            # 发送WebSocket通知
            if settings.ENABLE_WEBSOCKET_NOTIFICATIONS:
                await self.websocket_manager.send_personal_message(notification, user_id)
            
            logger.debug(f"任务进度通知已发送: 任务{task_id}, 进度{progress_data.get('progress', 0)}%")
            
        except Exception as e:
            logger.error(f"发送任务进度通知失败: {str(e)}")

    async def send_task_completion_notification(
        self, 
        task_id: int, 
        report_path: str,
        user_id: str
    ):
        """
        发送任务完成通知
        """
        try:
            notification = NotificationMessage(
                type="success",
                title="报告生成完成",
                message=f"报告任务 #{task_id} 已完成，可以下载查看。",
                data={
                    "task_id": task_id,
                    "report_path": report_path,
                    "download_url": f"/api/reports/{task_id}/download",
                    "completed_at": datetime.utcnow().isoformat()
                },
                user_id=user_id
            )
            
            # WebSocket通知
            if settings.ENABLE_WEBSOCKET_NOTIFICATIONS:
                await self.websocket_manager.send_personal_message(notification, user_id)
            
            # 邮件通知
            if settings.ENABLE_EMAIL_NOTIFICATIONS:
                db = next(get_db())
                try:
                    user = crud.user.get(db, id=user_id)
                    if user and user.email:
                        self.email_service.send_report_completion_notification(
                            to_emails=[user.email],
                            task_name=f"Task #{task_id}",
                            report_path=report_path
                        )
                finally:
                    db.close()
            
            logger.info(f"任务完成通知已发送: 任务{task_id}")
            
        except Exception as e:
            logger.error(f"发送任务完成通知失败: {str(e)}")

    async def send_task_failure_notification(
        self,
        task_id: int,
        user_id: str,
        error_message: str
    ):
        """
        发送任务失败通知
        """
        try:
            notification = NotificationMessage(
                type="error",
                title="报告生成失败",
                message=f"报告任务 #{task_id} 执行失败: {error_message}",
                data={
                    "task_id": task_id,
                    "error": error_message,
                    "failed_at": datetime.utcnow().isoformat()
                },
                user_id=user_id
            )
            
            # WebSocket通知
            if settings.ENABLE_WEBSOCKET_NOTIFICATIONS:
                await self.websocket_manager.send_personal_message(notification, user_id)
            
            # 邮件通知
            if settings.ENABLE_EMAIL_NOTIFICATIONS:
                db = next(get_db())
                try:
                    user = crud.user.get(db, id=user_id)
                    if user and user.email:
                        self.email_service.send_error_notification(
                            to_emails=[user.email],
                            task_name=f"Task #{task_id}",
                            error_message=error_message
                        )
                finally:
                    db.close()
            
            logger.info(f"任务失败通知已发送: 任务{task_id}")
            
        except Exception as e:
            logger.error(f"发送任务失败通知失败: {str(e)}")

    async def send_system_alert(
        self,
        level: str,
        title: str, 
        message: str
    ):
        """
        发送系统告警
        基于设计文档的告警机制
        """
        try:
            # 记录告警日志
            log_level = getattr(logging, level.upper(), logging.INFO)
            logger.log(log_level, f"系统告警 [{level}]: {title} - {message}")
            
            # 发送WebSocket系统通知
            if settings.ENABLE_WEBSOCKET_NOTIFICATIONS:
                await self.websocket_manager.send_system_notification(
                    title=title,
                    message=message,
                    notification_type=level
                )
            
            # 严重告警发送邮件给管理员
            if level in ["warning", "error"] and settings.ENABLE_EMAIL_NOTIFICATIONS:
                admin_emails = ["admin@autoreportai.com"]  # 这应该从配置中获取
                self.email_service.send_email(
                    to_emails=admin_emails,
                    subject=f"系统告警: {title}",
                    body=f"""
                    系统告警通知
                    
                    级别: {level}
                    标题: {title}
                    消息: {message}
                    时间: {datetime.utcnow().isoformat()}
                    
                    请及时处理此告警。
                    """
                )
            
            logger.info(f"系统告警已发送: {title}")
            
        except Exception as e:
            logger.error(f"发送系统告警失败: {str(e)}")

    async def check_task_failure_rate(self):
        """
        检查任务失败率并发送告警
        基于设计文档的监控机制
        """
        try:
            # 从Redis获取最近一小时的任务统计
            current_time = datetime.utcnow()
            one_hour_ago = current_time.timestamp() - 3600
            
            # 获取任务指标
            total_key = "task_metrics:total_tasks"
            failed_key = "task_metrics:failed_tasks"
            
            total_tasks = await self.redis_client.get(total_key) or "0"
            failed_tasks = await self.redis_client.get(failed_key) or "0"
            
            total_count = int(total_tasks)
            failed_count = int(failed_tasks)
            
            if total_count == 0:
                return
            
            failure_rate = failed_count / total_count
            
            # 如果失败率超过10%，发送告警
            if failure_rate > 0.1:
                await self.send_system_alert(
                    level="warning",
                    title="报告生成任务失败率过高",
                    message=f"最近一小时任务失败率达到 {failure_rate:.2%} ({failed_count}/{total_count})"
                )
            
        except Exception as e:
            logger.error(f"检查任务失败率失败: {str(e)}")

    async def record_task_metrics(
        self,
        task_id: int,
        status: str,
        duration: float = None,
        error: str = None
    ):
        """
        记录任务指标到Redis
        """
        try:
            # 更新任务计数器
            await self.redis_client.incr("task_metrics:total_tasks")
            
            if status == "failed":
                await self.redis_client.incr("task_metrics:failed_tasks")
            elif status == "completed":
                await self.redis_client.incr("task_metrics:completed_tasks")
            
            # 记录任务详细信息
            task_metrics = {
                "task_id": task_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat(),
                "duration": duration,
                "error": error
            }
            
            await self.redis_client.lpush(
                "task_metrics:history",
                json.dumps(task_metrics)
            )
            
            # 保持最新1000条记录
            await self.redis_client.ltrim("task_metrics:history", 0, 999)
            
            # 设置过期时间（24小时）
            await self.redis_client.expire("task_metrics:total_tasks", 86400)
            await self.redis_client.expire("task_metrics:failed_tasks", 86400)
            await self.redis_client.expire("task_metrics:completed_tasks", 86400)
            
        except Exception as e:
            logger.error(f"记录任务指标失败: {str(e)}")

    async def send_custom_notification(
        self,
        db: Session,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = "info",
        data: Optional[dict] = None,
        send_email: bool = False,
    ):
        """发送自定义通知"""
        try:
            # WebSocket通知
            if settings.ENABLE_WEBSOCKET_NOTIFICATIONS:
                notification = NotificationMessage(
                    type=notification_type,
                    title=title,
                    message=message,
                    data=data,
                    user_id=user_id,
                )
                await self.websocket_manager.send_personal_message(
                    notification, user_id
                )

            # 邮件通知（如果需要）
            if send_email and settings.ENABLE_EMAIL_NOTIFICATIONS:
                user = crud.user.get(db, id=user_id)
                if user and user.email:
                    self.email_service.send_email(
                        to_emails=[user.email], subject=title, body=message
                    )

            logger.info(f"Custom notification sent to user {user_id}: {title}")
        except Exception as e:
            logger.error(f"Error sending custom notification: {e}")


# 全局通知服务实例
notification_service = NotificationService()
