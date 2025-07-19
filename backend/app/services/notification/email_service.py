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

    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 全局邮件服务实例
email_service = EmailService()
