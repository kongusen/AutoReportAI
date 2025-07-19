from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.services.notification.email_service import EmailService

router = APIRouter()


@router.get("/email-settings")
def get_email_settings(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get user email settings.
    """
    # 这里可以从用户配置或系统配置中获取邮件设置
    # 为了安全，不返回密码
    return {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_username": "",
        "smtp_use_tls": True,
        "sender_email": "noreply@autoreportai.com",
        "sender_name": "AutoReportAI",
    }


@router.put("/email-settings")
def update_email_settings(
    *,
    db: Session = Depends(deps.get_db),
    email_settings: dict,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update user email settings.
    """
    # 这里应该将邮件设置保存到数据库
    # 为了演示，我们只返回成功消息
    return {"msg": "Email settings updated successfully"}


@router.post("/test-email")
def test_email_connection(
    *,
    db: Session = Depends(deps.get_db),
    email_settings: dict,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Test email connection with provided settings.
    """
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
        raise HTTPException(
            status_code=400, detail=f"Email connection test failed: {str(e)}"
        )


@router.post("/send-test-email")
def send_test_email(
    *,
    db: Session = Depends(deps.get_db),
    test_data: dict,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Send a test email.
    """
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
        raise HTTPException(
            status_code=500, detail=f"Failed to send test email: {str(e)}"
        )
