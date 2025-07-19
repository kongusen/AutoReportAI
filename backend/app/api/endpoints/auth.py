from datetime import timedelta
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.core import security
from app.core.config import settings
from app.core.security_logging import get_client_ip, get_user_agent, security_logger
from app.services.email_service import email_service

router = APIRouter(tags=["认证"])


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    username: str
    terms_accepted: bool = False


class PasswordReset(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class EmailVerification(BaseModel):
    token: str


@router.post(
    "/login",
    response_model=schemas.Token,
    summary="用户登录",
    description="""
    用户登录接口，使用用户名/邮箱和密码进行身份验证。
    
    ## 请求参数
    - **username**: 用户名或邮箱地址
    - **password**: 用户密码
    
    ## 返回值
    - **access_token**: JWT访问令牌
    - **token_type**: 令牌类型（Bearer）
    - **expires_in**: 令牌过期时间（秒）
    
    ## 错误码
    - **400**: 请求参数错误
    - **401**: 用户名或密码错误
    - **429**: 请求过于频繁
    """,
    responses={
        200: {
            "description": "登录成功",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "expires_in": 3600
                    }
                }
            }
        },
        400: {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "example": {"detail": "用户名不能为空"}
                }
            }
        },
        401: {
            "description": "认证失败",
            "content": {
                "application/json": {
                    "example": {"detail": "用户名或密码错误"}
                }
            }
        }
    }
)
def login_for_access_token(
    request: Request,
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Dict[str, Any]:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    user = crud.user.authenticate(
        db, email=form_data.username, password=form_data.password
    )

    if not user:
        # 记录失败的登录尝试
        security_logger.log_authentication_attempt(
            username=form_data.username,
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
            failure_reason="invalid_credentials",
        )
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    elif not user.is_active:
        # 记录未激活用户的登录尝试
        security_logger.log_authentication_attempt(
            username=form_data.username,
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
            failure_reason="inactive_user",
        )
        raise HTTPException(
            status_code=400, detail="Inactive user. Please verify your email."
        )

    # 记录成功的登录
    security_logger.log_authentication_attempt(
        username=form_data.username,
        success=True,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.post(
    "/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
    description="""
    新用户注册接口。
    
    ## 请求参数
    - **username**: 用户名（3-20个字符，只能包含字母、数字、下划线）
    - **email**: 邮箱地址（必须是有效的邮箱格式）
    - **password**: 密码（至少8个字符，包含字母和数字）
    - **full_name**: 用户全名（可选）
    
    ## 返回值
    - 新创建的用户信息
    
    ## 错误码
    - **400**: 请求参数错误或用户已存在
    - **422**: 数据验证失败
    """,
    responses={
        201: {
            "description": "注册成功",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "username": "john_doe",
                        "email": "john@example.com",
                        "full_name": "John Doe",
                        "is_active": True,
                        "is_superuser": False,
                        "created_at": "2023-12-01T10:00:00Z"
                    }
                }
            }
        },
        400: {
            "description": "用户已存在",
            "content": {
                "application/json": {
                    "example": {"detail": "用户名或邮箱已存在"}
                }
            }
        }
    }
)
def register_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserRegister,
    background_tasks: BackgroundTasks,
    request: Request,
) -> Any:
    """
    Register new user.
    """
    # 检查用户名是否已存在
    user = crud.user.get_by_username(db, username=user_in.username)
    if user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # 检查邮箱是否已存在
    user = crud.user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 检查是否接受条款
    if not user_in.terms_accepted:
        raise HTTPException(
            status_code=400, detail="Terms and conditions must be accepted"
        )

    # 创建用户
    user_create = schemas.UserCreate(
        email=user_in.email,
        password=user_in.password,
        full_name=user_in.full_name,
        username=user_in.username,
        is_active=False,  # 需要邮箱验证
        is_superuser=False,
    )

    user = crud.user.create(db, obj_in=user_create)

    # 生成邮箱验证令牌
    verification_token = security.generate_verification_token(user.email)

    # 发送验证邮件
    background_tasks.add_task(
        send_verification_email, user.email, user.full_name, verification_token
    )

    # 记录注册日志
    security_logger.log_authentication_attempt(
        username=user_in.username,
        success=True,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        action="register",
    )

    return user


@router.post("/verify-email", response_model=schemas.Msg)
def verify_email(
    *,
    db: Session = Depends(deps.get_db),
    verification: EmailVerification,
    request: Request,
) -> Any:
    """
    Verify user email address.
    """
    try:
        email = security.verify_verification_token(verification.token)
        if not email:
            raise HTTPException(
                status_code=400, detail="Invalid or expired verification token"
            )

        user = crud.user.get_by_email(db, email=email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.is_active:
            raise HTTPException(status_code=400, detail="Email already verified")

        # 激活用户
        user_update = schemas.UserUpdate(is_active=True)
        crud.user.update(db, db_obj=user, obj_in=user_update)

        # 记录验证日志
        security_logger.log_authentication_attempt(
            username=user.username,
            success=True,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            action="email_verification",
        )

        return {"msg": "Email verified successfully"}

    except Exception as e:
        raise HTTPException(status_code=400, detail="Email verification failed")


@router.post("/resend-verification", response_model=schemas.Msg)
def resend_verification_email(
    *,
    db: Session = Depends(deps.get_db),
    email_data: PasswordReset,
    background_tasks: BackgroundTasks,
) -> Any:
    """
    Resend email verification.
    """
    user = crud.user.get_by_email(db, email=email_data.email)
    if not user:
        # 不透露用户是否存在
        return {"msg": "If the email exists, a verification email has been sent"}

    if user.is_active:
        raise HTTPException(status_code=400, detail="Email already verified")

    # 生成新的验证令牌
    verification_token = security.generate_verification_token(user.email)

    # 发送验证邮件
    background_tasks.add_task(
        send_verification_email, user.email, user.full_name, verification_token
    )

    return {"msg": "Verification email sent"}


@router.post("/forgot-password", response_model=schemas.Msg)
def forgot_password(
    *,
    db: Session = Depends(deps.get_db),
    password_reset: PasswordReset,
    background_tasks: BackgroundTasks,
) -> Any:
    """
    Send password reset email.
    """
    user = crud.user.get_by_email(db, email=password_reset.email)
    if not user:
        # 不透露用户是否存在
        return {"msg": "If the email exists, a password reset email has been sent"}

    # 生成密码重置令牌
    reset_token = security.generate_password_reset_token(user.email)

    # 发送密码重置邮件
    background_tasks.add_task(
        send_password_reset_email, user.email, user.full_name, reset_token
    )

    return {"msg": "Password reset email sent"}


@router.post("/reset-password", response_model=schemas.Msg)
def reset_password(
    *,
    db: Session = Depends(deps.get_db),
    password_reset: PasswordResetConfirm,
    request: Request,
) -> Any:
    """
    Reset password with token.
    """
    try:
        email = security.verify_password_reset_token(password_reset.token)
        if not email:
            raise HTTPException(
                status_code=400, detail="Invalid or expired reset token"
            )

        user = crud.user.get_by_email(db, email=email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 更新密码
        hashed_password = security.get_password_hash(password_reset.new_password)
        user_update = schemas.UserUpdate(hashed_password=hashed_password)
        crud.user.update(db, db_obj=user, obj_in=user_update)

        # 记录密码重置日志
        security_logger.log_authentication_attempt(
            username=user.username,
            success=True,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            action="password_reset",
        )

        return {"msg": "Password reset successfully"}

    except Exception as e:
        raise HTTPException(status_code=400, detail="Password reset failed")


async def send_verification_email(email: str, full_name: str, token: str):
    """发送邮箱验证邮件"""
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    subject = "Verify your email address - AutoReportAI"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Email Verification</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4f46e5; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #4f46e5; color: white; text-decoration: none; border-radius: 4px; }}
            .footer {{ padding: 20px; text-align: center; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to AutoReportAI!</h1>
            </div>
            <div class="content">
                <p>Hello {full_name},</p>
                <p>Thank you for registering with AutoReportAI. To complete your registration, please verify your email address by clicking the button below:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" class="button">Verify Email Address</a>
                </p>
                <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666;">{verification_url}</p>
                <p>This verification link will expire in 24 hours.</p>
            </div>
            <div class="footer">
                <p>If you didn't create an account with AutoReportAI, please ignore this email.</p>
                <p>Best regards,<br>The AutoReportAI Team</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Welcome to AutoReportAI!
    
    Hello {full_name},
    
    Thank you for registering with AutoReportAI. To complete your registration, please verify your email address by visiting this link:
    
    {verification_url}
    
    This verification link will expire in 24 hours.
    
    If you didn't create an account with AutoReportAI, please ignore this email.
    
    Best regards,
    The AutoReportAI Team
    """

    email_service.send_email(
        to_emails=[email], subject=subject, body=text_body, html_body=html_body
    )


async def send_password_reset_email(email: str, full_name: str, token: str):
    """发送密码重置邮件"""
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    subject = "Reset your password - AutoReportAI"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Password Reset</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #dc2626; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #dc2626; color: white; text-decoration: none; border-radius: 4px; }}
            .footer {{ padding: 20px; text-align: center; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Password Reset Request</h1>
            </div>
            <div class="content">
                <p>Hello {full_name},</p>
                <p>We received a request to reset your password for your AutoReportAI account. Click the button below to reset your password:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" class="button">Reset Password</a>
                </p>
                <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666;">{reset_url}</p>
                <p>This password reset link will expire in 1 hour.</p>
                <p><strong>If you didn't request a password reset, please ignore this email and your password will remain unchanged.</strong></p>
            </div>
            <div class="footer">
                <p>Best regards,<br>The AutoReportAI Team</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Password Reset Request
    
    Hello {full_name},
    
    We received a request to reset your password for your AutoReportAI account. Visit this link to reset your password:
    
    {reset_url}
    
    This password reset link will expire in 1 hour.
    
    If you didn't request a password reset, please ignore this email and your password will remain unchanged.
    
    Best regards,
    The AutoReportAI Team
    """

    email_service.send_email(
        to_emails=[email], subject=subject, body=text_body, html_body=html_body
    )
