import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from .email_service import EmailService
from app.websocket.manager import NotificationMessage, manager

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self):
        self.email_service = EmailService()
        self.websocket_manager = manager

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
