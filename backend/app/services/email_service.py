import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List

from app.core.config import settings

class EmailService:
    def send_email(
        self,
        *,
        recipients: List[str],
        subject: str,
        body: str,
        attachment_path: Path = None,
    ):
        if not settings.SMTP_HOST or not settings.SMTP_USER:
            print("SMTP settings not configured. Skipping email sending.")
            return

        msg = MIMEMultipart()
        msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        if attachment_path and attachment_path.is_file():
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {attachment_path.name}",
            )
            msg.attach(part)

        try:
            smtp_server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            smtp_server.starttls()  # Secure the connection
            smtp_server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp_server.send_message(msg)
            smtp_server.quit()
            print(f"Email sent successfully to {', '.join(recipients)}")
        except Exception as e:
            print(f"Failed to send email. Error: {e}")

email_service = EmailService()
