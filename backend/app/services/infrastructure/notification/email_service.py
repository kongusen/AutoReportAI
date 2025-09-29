import logging
import smtplib
import os
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """邮件发送服务 - 优化版本"""

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
        self.host = smtp_server or settings.SMTP_SERVER
        self.port = smtp_port or settings.SMTP_PORT
        self.username = username or settings.SMTP_USERNAME
        self.password = password or settings.SMTP_PASSWORD
        self.use_tls = use_tls if use_tls is not None else settings.SMTP_USE_TLS
        self.from_email = sender_email or settings.SENDER_EMAIL
        self.sender_name = sender_name or settings.SENDER_NAME or "AutoReportAI"

        # 兼容旧属性名
        self.smtp_server = self.host
        self.smtp_port = self.port
        self.sender_email = self.from_email

    def validate_email_config(self) -> bool:
        """验证邮箱配置"""
        required_configs = [
            ('host', self.host),
            ('port', self.port),
            ('username', self.username),
            ('password', self.password),
            ('from_email', self.from_email)
        ]

        missing_configs = [name for name, value in required_configs if not value]

        if missing_configs:
            logger.error(f"缺少邮箱配置: {', '.join(missing_configs)}")
            return False

        return True

    def test_connection(self) -> bool:
        """测试邮件服务器连接"""
        try:
            if not self.validate_email_config():
                return False

            server = smtplib.SMTP(self.host, self.port)
            if self.use_tls:
                server.starttls()
            server.login(self.username, self.password)
            server.quit()
            logger.info("邮件服务器连接测试成功")
            return True
        except Exception as e:
            logger.error(f"邮件服务器连接测试失败: {e}")
            return False

    def _send_email(self, subject: str, body: str, to_emails: List[str], attachments: List[str] = None) -> bool:
        """发送邮件 - 优化版本"""
        if attachments is None:
            attachments = []

        try:
            # 验证邮箱配置
            if not self.validate_email_config():
                return False

            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject

            # 添加HTML正文
            msg.attach(MIMEText(body, 'html', 'utf-8'))

            # 添加附件
            for attachment_path in attachments:
                if os.path.exists(attachment_path):
                    filename = os.path.basename(attachment_path)
                    try:
                        # 读取文档内容
                        with open(attachment_path, 'rb') as f:
                            attachment_data = f.read()

                        # 使用MIMEApplication处理Word文档
                        if filename.lower().endswith('.docx'):
                            part = MIMEApplication(
                                attachment_data,
                                _subtype='vnd.openxmlformats-officedocument.wordprocessingml.document',
                                name=filename
                            )
                            part.set_type('application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                        elif filename.lower().endswith('.doc'):
                            part = MIMEApplication(
                                attachment_data,
                                _subtype='msword',
                                name=filename
                            )
                            part.set_type('application/msword')
                        else:
                            part = MIMEApplication(
                                attachment_data,
                                _subtype='octet-stream',
                                name=filename
                            )

                        part.add_header('Content-Disposition', 'attachment', filename=filename)
                        msg.attach(part)

                        mime_info = 'Word文档' if filename.lower().endswith(('.docx', '.doc')) else '其他文档'
                        logger.info(f"📎 已添加附件: {filename} ({mime_info})")

                    except Exception as e:
                        logger.warning(f"⚠️ 无法添加附件 {attachment_path}: {e}")
                else:
                    logger.warning(f"⚠️ 附件文件不存在: {attachment_path}")

            # 发送邮件
            server = smtplib.SMTP(self.host, self.port)
            try:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            finally:
                server.quit()

            logger.info(f"✅ 邮件发送成功: {', '.join(to_emails)}")
            if attachments:
                logger.info(f"📎 包含 {len(attachments)} 个附件")
            return True

        except Exception as e:
            logger.error(f"❌ SMTP发送失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> bool:
        """发送邮件 - 兼容旧接口"""
        # 使用HTML版本，如果没有提供则使用纯文本
        email_body = html_body if html_body else f"<pre>{body}</pre>"
        return self._send_email(subject, email_body, to_emails, attachments or [])

    def send_report_notification(
        self,
        to_emails: List[str],
        report_name: str,
        report_path: str,
        generation_time: datetime,
        period_info: str = "",
        attach_report: bool = True
    ) -> bool:
        """
        发送报告生成完成通知邮件

        Args:
            to_emails: 收件人邮箱列表
            report_name: 报告名称
            report_path: 报告文件路径
            generation_time: 报告生成时间
            period_info: 报告周期信息
            attach_report: 是否附加报告文件

        Returns:
            bool: 发送是否成功
        """
        try:
            # 验证邮箱配置
            if not self.validate_email_config():
                return False

            # 创建邮件正文
            body = self._create_notification_body(
                report_name, generation_time, period_info
            )

            # 发送邮件
            return self._send_email(
                subject=f'报告生成完成通知 - {report_name}',
                body=body,
                to_emails=to_emails,
                attachments=[report_path] if attach_report and os.path.exists(report_path) else []
            )

        except Exception as e:
            logger.error(f"❌ 发送邮件失败: {e}")
            return False

    def send_analysis_notification(
        self,
        to_emails: List[str],
        analysis_type: str,
        output_files: dict,
        completion_time: datetime
    ) -> bool:
        """
        发送分析完成通知邮件

        Args:
            to_emails: 收件人邮箱列表
            analysis_type: 分析类型
            output_files: 输出文件路径字典
            completion_time: 完成时间

        Returns:
            bool: 发送是否成功
        """
        try:
            # 验证邮箱配置
            if not self.validate_email_config():
                return False

            # 创建邮件正文
            body = self._create_analysis_notification_body(
                analysis_type, output_files, completion_time
            )

            # 发送邮件
            return self._send_email(
                subject=f'分析任务完成通知 - {analysis_type}',
                body=body,
                to_emails=to_emails,
                attachments=[]
            )

        except Exception as e:
            logger.error(f"❌ 发送分析通知邮件失败: {e}")
            return False

    def send_task_failure_notification(
        self,
        to_emails: List[str],
        task_name: str,
        error_message: str,
        failure_time: datetime
    ) -> bool:
        """
        发送任务失败通知邮件

        Args:
            to_emails: 收件人邮箱列表
            task_name: 任务名称
            error_message: 错误信息
            failure_time: 失败时间

        Returns:
            bool: 发送是否成功
        """
        try:
            # 验证邮箱配置
            if not self.validate_email_config():
                return False

            # 创建邮件正文
            body = self._create_failure_notification_body(
                task_name, error_message, failure_time
            )

            # 发送邮件
            return self._send_email(
                subject=f'⚠️ 任务执行失败通知 - {task_name}',
                body=body,
                to_emails=to_emails,
                attachments=[]
            )

        except Exception as e:
            logger.error(f"❌ 发送失败通知邮件失败: {e}")
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

    def _create_notification_body(
        self,
        report_name: str,
        generation_time: datetime,
        period_info: str
    ) -> str:
        """创建报告生成成功通知邮件正文"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2e8b57;">📊 报告生成完成通知</h2>

                <div style="background-color: #f0f8ff; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #1e6091;">报告信息</h3>
                    <p><strong>报告名称:</strong> {report_name}</p>
                    <p><strong>生成时间:</strong> {self._format_time_shanghai(generation_time)}</p>
                    {f'<p><strong>报告周期:</strong> {period_info}</p>' if period_info else ''}
                </div>

                <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px;">
                    <h3 style="margin-top: 0; color: #d2691e;">📋 说明</h3>
                    <ul>
                        <li>报告已成功生成并保存</li>
                        <li>如有附件，请查看邮件附件中的报告文件</li>
                        <li>如有任何问题，请联系系统管理员</li>
                    </ul>
                </div>

                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="text-align: center; color: #888; font-size: 12px;">
                    此邮件由报告生成系统自动发送，请勿回复
                </p>
            </div>
        </body>
        </html>
        """

    def _create_failure_notification_body(
        self,
        task_name: str,
        error_message: str,
        failure_time: datetime
    ) -> str:
        """创建任务失败通知邮件正文"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #dc143c;">⚠️ 任务执行失败通知</h2>

                <div style="background-color: #ffe4e1; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #dc143c;">
                    <h3 style="margin-top: 0; color: #8b0000;">失败信息</h3>
                    <p><strong>任务名称:</strong> {task_name}</p>
                    <p><strong>失败时间:</strong> {self._format_time_shanghai(failure_time)}</p>
                    <p><strong>错误信息:</strong></p>
                    <pre style="background-color: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto;">{error_message}</pre>
                </div>

                <div style="background-color: #fff8dc; padding: 15px; border-radius: 5px; border-left: 4px solid #ffa500;">
                    <h3 style="margin-top: 0; color: #ff8c00;">🔧 建议操作</h3>
                    <ul>
                        <li>检查任务配置是否正确</li>
                        <li>验证数据库连接是否正常</li>
                        <li>查看系统日志获取详细错误信息</li>
                        <li>联系系统管理员进行故障排查</li>
                    </ul>
                </div>

                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="text-align: center; color: #888; font-size: 12px;">
                    此邮件由报告生成系统自动发送，请勿回复
                </p>
            </div>
        </body>
        </html>
        """

    def _create_analysis_notification_body(
        self,
        analysis_type: str,
        output_files: dict,
        completion_time: datetime
    ) -> str:
        """创建分析完成通知邮件正文"""

        # 生成文件列表HTML
        file_list_html = ""
        for file_type, file_path in output_files.items():
            file_name = os.path.basename(file_path)
            file_list_html += f"<li><strong>{file_type}:</strong> {file_name}</li>"

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2e8b57;">🔍 分析任务完成通知</h2>

                <div style="background-color: #f0f8ff; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #1e6091;">分析信息</h3>
                    <p><strong>分析类型:</strong> {analysis_type}</p>
                    <p><strong>完成时间:</strong> {self._format_time_shanghai(completion_time)}</p>
                    <p><strong>生成文件数量:</strong> {len(output_files)} 个</p>
                </div>

                <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px;">
                    <h3 style="margin-top: 0; color: #d2691e;">📁 生成的文件</h3>
                    <ul>
                        {file_list_html}
                    </ul>
                </div>

                <div style="background-color: #e6ffe6; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #006400;">📋 说明</h3>
                    <ul>
                        <li>分析结果已成功生成并保存</li>
                        <li>所有文件均为JSON格式，便于程序处理</li>
                        <li>如需重新分析，请联系系统管理员</li>
                    </ul>
                </div>

                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="text-align: center; color: #888; font-size: 12px;">
                    此邮件由报告生成系统自动发送，请勿回复
                </p>
            </div>
        </body>
        </html>
        """

    def _format_time_shanghai(self, dt: datetime) -> str:
        """将时间格式化为上海时区"""
        try:
            from app.core.timezone import format_time
            return format_time(dt)
        except ImportError:
            # 如果没有时区信息，使用本地时间格式化
            if dt.tzinfo is None:
                # 假设为上海时区
                import pytz
                shanghai_tz = pytz.timezone('Asia/Shanghai')
                dt = shanghai_tz.localize(dt)
            else:
                # 转换为上海时区
                import pytz
                shanghai_tz = pytz.timezone('Asia/Shanghai')
                dt = dt.astimezone(shanghai_tz)

            return dt.strftime('%Y年%m月%d日 %H:%M:%S (上海时间)')

    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        return self._format_time_shanghai(datetime.now())


# 全局邮件服务实例
email_service = EmailService()
