from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.notification.email_service import EmailService

router = APIRouter()

@router.get("/email-settings")
async def get_email_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    # TODO: 从数据库获取用户邮件设置
    return {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_username": "",
        "smtp_use_tls": True,
        "sender_email": "noreply@autoreportai.com",
        "sender_name": "AutoReportAI",
    }

@router.put("/email-settings")
async def update_email_settings(
    email_settings: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    # TODO: 保存邮件设置到数据库
    return {"msg": "Email settings updated successfully"}

@router.post("/test-email")
async def test_email_connection(
    email_settings: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    try:
        email_service = EmailService(
            smtp_server=email_settings.get("smtp_server"),
            smtp_port=email_settings.get("smtp_port"),
            username=email_settings.get("smtp_username"),
            password=email_settings.get("smtp_password"),
            use_tls=email_settings.get("smtp_use_tls", True),
            sender_email=email_settings.get("sender_email"),
            sender_name=email_settings.get("sender_name"),
        )
        if email_service.test_connection():
            return {"msg": "Email connection test successful"}
        else:
            raise HTTPException(status_code=400, detail="Email connection test failed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Email connection test failed: {str(e)}")

@router.post("/send-test-email")
async def send_test_email(
    test_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    try:
        email_service = EmailService()
        success = email_service.send_email(
            to_emails=[current_user.email],
            subject="AutoReportAI Test Email",
            body="This is a test email from AutoReportAI. If you received this, your email configuration is working correctly!",
            html_body="""
            <html>
            <body>
                <h2>AutoReportAI Test Email</h2>
                <p>This is a test email from AutoReportAI.</p>
                <p>If you received this, your email configuration is working correctly!</p>
                <br>
                <p>Best regards,<br>AutoReportAI Team</p>
            </body>
            </html>
            """,
        )
        if success:
            return {"msg": "Test email sent successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send test email")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send test email: {str(e)}") 