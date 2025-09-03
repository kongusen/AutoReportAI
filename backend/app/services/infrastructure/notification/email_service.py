import logging
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(
        self,
        smtp_server: str = None,
        smtp_port: int = None,
        username: str = None,
        password: str = None,
        use_tls: bool = True,
        sender_email: str = None,
        sender_name: str = None,
    ):
        self.smtp_server = smtp_server or settings.SMTP_SERVER
        self.smtp_port = smtp_port or settings.SMTP_PORT
        self.username = username or settings.SMTP_USERNAME
        self.password = password or settings.SMTP_PASSWORD
        self.use_tls = use_tls if use_tls is not None else settings.SMTP_USE_TLS
        self.sender_email = sender_email or settings.SENDER_EMAIL
        self.sender_name = sender_name or settings.SENDER_NAME or "AutoReportAI"

    def test_connection(self) -> bool:
        """测试邮件服务器连接"""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()
            server.login(self.username, self.password)
            server.quit()
            return True
        except Exception as e:
            logger.error(f"Email connection test failed: {e}")
            return False

    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> bool:
        """发送邮件"""
        try:
            # 创建邮件消息
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{self.sender_name} <{self.sender_email}>"
            msg["To"] = ", ".join(to_emails)
            msg["Subject"] = subject

            # 添加文本内容
            text_part = MIMEText(body, "plain", "utf-8")
            msg.attach(text_part)

            # 添加HTML内容（如果提供）
            if html_body:
                html_part = MIMEText(html_body, "html", "utf-8")
                msg.attach(html_part)

            # 添加附件
            if attachments:
                for file_path in attachments:
                    if Path(file_path).exists():
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                "Content-Disposition",
                                f"attachment; filename= {Path(file_path).name}",
                            )
                            msg.attach(part)

            # 发送邮件
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()

            logger.info(f"Email sent successfully to {', '.join(to_emails)}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def send_report_completion_notification(
        self, to_emails: List[str], task_name: str, report_path: Optional[str] = None
    ) -> bool:
        """发送报告完成通知"""
        subject = f"Report Generated: {task_name}"

        body = f"""
Dear User,

Your report "{task_name}" has been generated successfully.

Report Details:
- Task: {task_name}
- Generated at: {self._get_current_time()}
- Status: Completed

You can download the report from the AutoReportAI dashboard.

Best regards,
AutoReportAI Team
        """.strip()

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Report Generated</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4f46e5; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .footer {{ padding: 20px; text-align: center; color: #666; }}
        .success {{ color: #10b981; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AutoReportAI</h1>
            <h2>Report Generated Successfully</h2>
        </div>
        <div class="content">
            <p>Dear User,</p>
            <p>Your report "<strong>{task_name}</strong>" has been generated successfully.</p>
            
            <h3>Report Details:</h3>
            <ul>
                <li><strong>Task:</strong> {task_name}</li>
                <li><strong>Generated at:</strong> {self._get_current_time()}</li>
                <li><strong>Status:</strong> <span class="success">Completed</span></li>
            </ul>
            
            <p>You can download the report from the AutoReportAI dashboard.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>AutoReportAI Team</p>
        </div>
    </div>
</body>
</html>
        """.strip()

        attachments = (
            [report_path] if report_path and Path(report_path).exists() else None
        )

        return self.send_email(
            to_emails=to_emails,
            subject=subject,
            body=body,
            html_body=html_body,
            attachments=attachments,
        )

    def send_error_notification(
        self, to_emails: List[str], task_name: str, error_message: str
    ) -> bool:
        """发送错误通知"""
        subject = f"Report Generation Failed: {task_name}"

        body = f"""
Dear User,

Unfortunately, the report generation for "{task_name}" has failed.

Error Details:
- Task: {task_name}
- Failed at: {self._get_current_time()}
- Error: {error_message}

Please check your task configuration and try again. If the problem persists, contact support.

Best regards,
AutoReportAI Team
        """.strip()

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Report Generation Failed</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #dc2626; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .footer {{ padding: 20px; text-align: center; color: #666; }}
        .error {{ color: #dc2626; font-weight: bold; }}
        .error-box {{ background-color: #fef2f2; border: 1px solid #fecaca; padding: 10px; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AutoReportAI</h1>
            <h2>Report Generation Failed</h2>
        </div>
        <div class="content">
            <p>Dear User,</p>
            <p>Unfortunately, the report generation for "<strong>{task_name}</strong>" has failed.</p>
            
            <h3>Error Details:</h3>
            <ul>
                <li><strong>Task:</strong> {task_name}</li>
                <li><strong>Failed at:</strong> {self._get_current_time()}</li>
                <li><strong>Status:</strong> <span class="error">Failed</span></li>
            </ul>
            
            <div class="error-box">
                <strong>Error Message:</strong><br>
                {error_message}
            </div>
            
            <p>Please check your task configuration and try again. If the problem persists, contact support.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>AutoReportAI Team</p>
        </div>
    </div>
</body>
</html>
        """.strip()

        return self.send_email(
            to_emails=to_emails, subject=subject, body=body, html_body=html_body
        )

    def send_weekly_summary(self, to_emails: List[str], summary_data: dict) -> bool:
        """发送周报摘要"""
        subject = "AutoReportAI Weekly Summary"

        total_reports = summary_data.get("total_reports", 0)
        successful_reports = summary_data.get("successful_reports", 0)
        failed_reports = summary_data.get("failed_reports", 0)
        success_rate = (
            (successful_reports / total_reports * 100) if total_reports > 0 else 0
        )

        body = f"""
Dear User,

Here's your weekly AutoReportAI summary:

Report Statistics:
- Total Reports Generated: {total_reports}
- Successful Reports: {successful_reports}
- Failed Reports: {failed_reports}
- Success Rate: {success_rate:.1f}%

Thank you for using AutoReportAI!

Best regards,
AutoReportAI Team
        """.strip()

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Weekly Summary</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4f46e5; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .footer {{ padding: 20px; text-align: center; color: #666; }}
        .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .stat {{ text-align: center; padding: 15px; background: white; border-radius: 8px; }}
        .stat-number {{ font-size: 2em; font-weight: bold; color: #4f46e5; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AutoReportAI</h1>
            <h2>Weekly Summary</h2>
        </div>
        <div class="content">
            <p>Dear User,</p>
            <p>Here's your weekly AutoReportAI summary:</p>
            
            <div class="stats">
                <div class="stat">
                    <div class="stat-number">{total_reports}</div>
                    <div>Total Reports</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{successful_reports}</div>
                    <div>Successful</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{success_rate:.1f}%</div>
                    <div>Success Rate</div>
                </div>
            </div>
            
            <p>Thank you for using AutoReportAI!</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>AutoReportAI Team</p>
        </div>
    </div>
</body>
</html>
        """.strip()

        return self.send_email(
            to_emails=to_emails, subject=subject, body=body, html_body=html_body
        )

    def send_notification_email(
        self, 
        to_emails: List[str], 
        notification_type: str,
        title: str,
        message: str,
        details: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """发送通知邮件 - 通用方法"""
        try:
            # 根据通知类型设置邮件主题和样式
            type_configs = {
                "task_update": {
                    "subject_prefix": "任务更新",
                    "color": "#4f46e5",
                    "icon": "📋"
                },
                "report_ready": {
                    "subject_prefix": "报告完成",
                    "color": "#10b981",
                    "icon": "📊"
                },
                "error": {
                    "subject_prefix": "错误通知",
                    "color": "#dc2626",
                    "icon": "⚠️"
                },
                "system": {
                    "subject_prefix": "系统通知",
                    "color": "#6b7280",
                    "icon": "🔔"
                }
            }
            
            config = type_configs.get(notification_type, {
                "subject_prefix": "通知",
                "color": "#4f46e5",
                "icon": "📢"
            })
            
            subject = f"{config['icon']} {config['subject_prefix']}: {title}"
            
            # 文本版本
            body_parts = [
                f"{config['icon']} {title}",
                "",
                message
            ]
            
            if details:
                body_parts.extend(["", "详细信息:", details])
            
            if metadata:
                body_parts.extend(["", "相关信息:"])
                for key, value in metadata.items():
                    if key in ['task_name', 'report_name', 'task_id', 'report_id']:
                        body_parts.append(f"- {key}: {value}")
            
            body_parts.extend([
                "",
                f"发送时间: {self._get_current_time()}",
                "",
                "您可以在 AutoReportAI 控制台中查看完整信息。",
                "",
                "Best regards,",
                "AutoReportAI Team"
            ])
            
            body = "\n".join(body_parts)
            
            # HTML版本
            details_html = ""
            if details:
                details_html = f"""
                <div style="background-color: #f3f4f6; padding: 15px; border-radius: 8px; margin: 15px 0;">
                    <h4 style="margin: 0 0 10px 0; color: #374151;">详细信息:</h4>
                    <p style="margin: 0; color: #6b7280; white-space: pre-line;">{details}</p>
                </div>
                """
            
            metadata_html = ""
            if metadata:
                metadata_items = []
                for key, value in metadata.items():
                    if key in ['task_name', 'report_name', 'task_id', 'report_id']:
                        metadata_items.append(f"<li><strong>{key}:</strong> {value}</li>")
                
                if metadata_items:
                    metadata_html = f"""
                    <div style="margin: 15px 0;">
                        <h4 style="margin: 0 0 10px 0; color: #374151;">相关信息:</h4>
                        <ul style="margin: 0; padding-left: 20px; color: #6b7280;">
                            {"".join(metadata_items)}
                        </ul>
                    </div>
                    """
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>{subject}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: {config['color']}; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ padding: 20px; background-color: #ffffff; border: 1px solid #e5e7eb; }}
                    .footer {{ padding: 20px; text-align: center; color: #666; background-color: #f9fafb; border-radius: 0 0 8px 8px; }}
                    .icon {{ font-size: 2em; margin-bottom: 10px; }}
                    .message {{ color: #374151; margin: 15px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="icon">{config['icon']}</div>
                        <h1 style="margin: 0;">AutoReportAI</h1>
                        <h2 style="margin: 10px 0 0 0;">{title}</h2>
                    </div>
                    <div class="content">
                        <p class="message">{message}</p>
                        {details_html}
                        {metadata_html}
                        <p style="margin-top: 20px; color: #6b7280; font-size: 14px;">
                            发送时间: {self._get_current_time()}
                        </p>
                        <p style="margin-top: 15px; color: #6b7280;">
                            您可以在 AutoReportAI 控制台中查看完整信息。
                        </p>
                    </div>
                    <div class="footer">
                        <p>Best regards,<br>AutoReportAI Team</p>
                    </div>
                </div>
            </body>
            </html>
            """.strip()
            
            return self.send_email(
                to_emails=to_emails,
                subject=subject,
                body=body,
                html_body=html_body,
                attachments=attachments
            )
            
        except Exception as e:
            logger.error(f"Failed to send notification email: {e}")
            return False
    
    def send_report_with_attachment(
        self, 
        to_emails: List[str], 
        report_name: str,
        report_path: str,
        task_info: Optional[dict] = None
    ) -> bool:
        """发送带有报告附件的邮件"""
        try:
            subject = f"📊 报告已生成: {report_name}"
            
            # 构建任务信息
            task_details = ""
            if task_info:
                details_list = []
                if task_info.get('task_name'):
                    details_list.append(f"任务名称: {task_info['task_name']}")
                if task_info.get('data_source'):
                    details_list.append(f"数据源: {task_info['data_source']}")
                if task_info.get('template'):
                    details_list.append(f"模板: {task_info['template']}")
                if task_info.get('execution_time'):
                    details_list.append(f"执行时间: {task_info['execution_time']}")
                
                task_details = "\n".join([f"- {detail}" for detail in details_list])
            
            body = f"""
您好！

您的报告 "{report_name}" 已经生成完成，请查看附件中的报告文件。

{f"任务详情:{chr(10)}{task_details}{chr(10)}" if task_details else ""}

报告生成时间: {self._get_current_time()}

如有任何问题，请联系我们的技术支持。

Best regards,
AutoReportAI Team
            """.strip()
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>报告已生成</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #10b981; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ padding: 20px; background-color: #ffffff; border: 1px solid #e5e7eb; }}
                    .footer {{ padding: 20px; text-align: center; color: #666; background-color: #f9fafb; border-radius: 0 0 8px 8px; }}
                    .report-info {{ background-color: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 8px; margin: 15px 0; }}
                    .attachment-notice {{ background-color: #eff6ff; border: 1px solid #bfdbfe; padding: 15px; border-radius: 8px; margin: 15px 0; }}
                    .success {{ color: #10b981; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 style="margin: 0;">📊 AutoReportAI</h1>
                        <h2 style="margin: 10px 0 0 0;">报告生成完成</h2>
                    </div>
                    <div class="content">
                        <p>您好！</p>
                        
                        <div class="report-info">
                            <h3 style="margin: 0 0 10px 0; color: #059669;">报告信息</h3>
                            <p style="margin: 0;"><strong>报告名称:</strong> {report_name}</p>
                            <p style="margin: 5px 0 0 0;"><strong>生成时间:</strong> {self._get_current_time()}</p>
                        </div>
                        
                        {f'''
                        <div style="margin: 15px 0;">
                            <h4 style="margin: 0 0 10px 0; color: #374151;">任务详情:</h4>
                            <div style="background-color: #f9fafb; padding: 10px; border-radius: 4px;">
                                <pre style="margin: 0; white-space: pre-line; color: #6b7280;">{task_details}</pre>
                            </div>
                        </div>
                        ''' if task_details else ''}
                        
                        <div class="attachment-notice">
                            <h4 style="margin: 0 0 10px 0; color: #1d4ed8;">📎 附件说明</h4>
                            <p style="margin: 0;">报告文件已作为附件发送，请下载查看完整内容。</p>
                        </div>
                        
                        <p>如有任何问题，请联系我们的技术支持。</p>
                    </div>
                    <div class="footer">
                        <p>Best regards,<br>AutoReportAI Team</p>
                    </div>
                </div>
            </body>
            </html>
            """.strip()
            
            # 检查报告文件是否存在
            attachments = [report_path] if report_path and Path(report_path).exists() else None
            if not attachments:
                logger.warning(f"Report file not found: {report_path}")
                # 如果文件不存在，发送无附件版本
                body += "\n\n注意: 报告文件未找到，请联系技术支持。"
                html_body = html_body.replace(
                    '<div class="attachment-notice">',
                    '<div class="attachment-notice" style="background-color: #fef2f2; border-color: #fecaca;">'
                ).replace(
                    '<h4 style="margin: 0 0 10px 0; color: #1d4ed8;">📎 附件说明</h4>',
                    '<h4 style="margin: 0 0 10px 0; color: #dc2626;">⚠️ 附件说明</h4>'
                ).replace(
                    '<p style="margin: 0;">报告文件已作为附件发送，请下载查看完整内容。</p>',
                    '<p style="margin: 0; color: #dc2626;">报告文件未找到，请联系技术支持。</p>'
                )
            
            return self.send_email(
                to_emails=to_emails,
                subject=subject,
                body=body,
                html_body=html_body,
                attachments=attachments
            )
            
        except Exception as e:
            logger.error(f"Failed to send report email: {e}")
            return False

    def send_task_notification_email(
        self,
        to_emails: List[str],
        task_name: str,
        status: str,
        message: str,
        task_id: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """发送任务状态通知邮件"""
        notification_type = "error" if status == "failed" else "task_update"
        
        metadata = {
            "task_name": task_name,
            "task_id": task_id,
            "status": status
        }
        
        details = error_message if error_message else None
        
        return self.send_notification_email(
            to_emails=to_emails,
            notification_type=notification_type,
            title=f"任务 {task_name} - {status}",
            message=message,
            details=details,
            metadata=metadata
        )

    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from app.core.timezone import format_time
        
        return format_time()


# 全局邮件服务实例
email_service = EmailService()
