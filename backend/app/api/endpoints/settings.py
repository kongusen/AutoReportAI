"""用户设置管理API端点"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.architecture import ApiResponse
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.ai_provider import AIProvider
from app.schemas.user_profile import UserProfile, UserProfileUpdate
from app.schemas.ai_provider import AIProviderResponse
from app.crud.crud_user_profile import user_profile

router = APIRouter()


@router.get("/profile", response_model=ApiResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户配置信息"""
    profile = user_profile.get_or_create(db, user_id=current_user.id)
    
    return ApiResponse(
        success=True,
        data=profile,
        message="获取用户配置成功"
    )


@router.put("/profile", response_model=ApiResponse)
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户配置"""
    profile = user_profile.get_or_create(db, user_id=current_user.id)
    updated_profile = user_profile.update(db, db_obj=profile, obj_in=profile_update)
    
    return ApiResponse(
        success=True,
        data=updated_profile,
        message="用户配置更新成功"
    )


@router.get("/ai-providers", response_model=ApiResponse)
async def get_user_ai_providers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户的AI提供商列表（用于设置页面选择）"""
    ai_providers = db.query(AIProvider).filter(
        AIProvider.user_id == current_user.id,
        AIProvider.is_active == True
    ).all()
    
    # 转换为响应模型
    response_items = []
    for provider in ai_providers:
        response_items.append(AIProviderResponse(
            id=provider.id,
            provider_name=provider.provider_name,
            provider_type=provider.provider_type,
            api_base_url=provider.api_base_url,
            default_model_name=provider.default_model_name,
            is_active=provider.is_active
        ))
    
    return ApiResponse(
        success=True,
        data=response_items,
        message="获取AI提供商列表成功"
    )


@router.get("/system-info", response_model=ApiResponse)
async def get_system_settings_info(
    current_user: User = Depends(get_current_user)
):
    """获取系统设置相关信息"""
    system_info = {
        "supported_languages": [
            {"code": "zh-CN", "name": "简体中文"},
            {"code": "en", "name": "English"},
            {"code": "zh-TW", "name": "繁體中文"}
        ],
        "supported_themes": [
            {"code": "light", "name": "浅色主题"},
            {"code": "dark", "name": "深色主题"},
            {"code": "auto", "name": "跟随系统"}
        ],
        "supported_report_formats": [
            {"code": "pdf", "name": "PDF"},
            {"code": "docx", "name": "Word文档"},
            {"code": "html", "name": "HTML"}
        ],
        "supported_timezones": [
            {"code": "Asia/Shanghai", "name": "北京时间 (UTC+8)"},
            {"code": "UTC", "name": "世界协调时间 (UTC)"},
            {"code": "America/New_York", "name": "美国东部时间"},
            {"code": "Europe/London", "name": "英国时间"}
        ],
        "supported_date_formats": [
            {"code": "YYYY-MM-DD", "name": "2024-01-01"},
            {"code": "MM/DD/YYYY", "name": "01/01/2024"},
            {"code": "DD/MM/YYYY", "name": "01/01/2024"},
            {"code": "DD-MM-YYYY", "name": "01-01-2024"}
        ]
    }
    
    return ApiResponse(
        success=True,
        data=system_info,
        message="获取系统设置信息成功"
    )


@router.post("/reset-to-defaults", response_model=ApiResponse)
async def reset_settings_to_defaults(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """重置设置为默认值"""
    profile = user_profile.get_or_create(db, user_id=current_user.id)
    
    # 重置为默认设置
    default_settings = UserProfileUpdate(
        language="zh-CN",
        theme="light",
        email_notifications=True,
        report_notifications=True,
        system_notifications=True,
        default_storage_days=90,
        auto_cleanup_enabled=True,
        default_report_format="pdf",
        default_ai_provider=None,
        custom_css=None,
        dashboard_layout=None,
        timezone="Asia/Shanghai",
        date_format="YYYY-MM-DD"
    )
    
    updated_profile = user_profile.update(db, db_obj=profile, obj_in=default_settings)
    
    return ApiResponse(
        success=True,
        data=updated_profile,
        message="设置已重置为默认值"
    )