"""用户设置管理API端点"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.architecture import ApiResponse
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.llm_server import LLMServer
from app.schemas.user_profile import UserProfile, UserProfileUpdate
from app.schemas.llm_server import LLMServerResponse
from app.schemas.user_llm_preference import (
    UserLLMPreferenceSecureResponse,
    UserLLMPreferenceUpdate,
    UserLLMUsageQuotaResponse
)
from app.crud.crud_user_profile import user_profile
from app.crud.crud_user_llm_preference import crud_user_llm_preference, crud_user_llm_usage_quota

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


@router.get("/llm-servers", response_model=ApiResponse)
async def get_available_llm_servers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取可用的LLM服务器列表（用于设置页面选择）"""
    # 获取所有活跃且健康的LLM服务器（系统级别，不绑定用户）
    llm_servers = db.query(LLMServer).filter(
        LLMServer.is_active == True,
        LLMServer.is_healthy == True
    ).all()
    
    # 转换为响应模型  
    response_items = []
    for server in llm_servers:
        # 获取服务器统计信息
        from app import crud
        stats = crud.llm_server.get_server_stats(db, server_id=server.id)
        
        # 创建响应对象
        server_response = {
            "id": server.id,
            "server_id": str(server.server_id),
            "name": server.name,
            "description": server.description,
            "base_url": server.base_url,
            "is_active": server.is_active,
            "is_healthy": server.is_healthy,
            "capabilities": server.capabilities,
            "providers_count": stats.get('providers_count', 0),
            "success_rate": stats.get('success_rate', 0.0)
        }
        response_items.append(server_response)
    
    return ApiResponse(
        success=True,
        data=response_items,
        message="获取LLM服务器列表成功"
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


# === LLM偏好设置API ===

@router.get("/llm-preferences", response_model=ApiResponse)
async def get_crud_user_llm_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户LLM偏好设置"""
    preference = crud_user_llm_preference.get_or_create(db, user_id=current_user.id)
    
    # 创建安全响应（隐藏API密钥）
    secure_response = {
        "id": preference.id,
        "user_id": preference.user_id,
        "default_llm_server_id": preference.default_llm_server_id,
        "default_provider_name": preference.default_provider_name,
        "default_model_name": preference.default_model_name,
        "preferred_temperature": preference.preferred_temperature,
        "max_tokens_limit": preference.max_tokens_limit,
        "daily_token_quota": preference.daily_token_quota,
        "monthly_cost_limit": preference.monthly_cost_limit,
        "enable_caching": preference.enable_caching,
        "cache_ttl_hours": preference.cache_ttl_hours,
        "enable_learning": preference.enable_learning,
        "configured_providers": list((preference.personal_api_keys or {}).keys()),
        "provider_priorities": preference.provider_priorities or {},
        "model_preferences": preference.model_preferences or {},
        "custom_settings": preference.custom_settings or {},
        "created_at": preference.created_at,
        "updated_at": preference.updated_at
    }
    
    return ApiResponse(
        success=True,
        data=secure_response,
        message="获取LLM偏好设置成功"
    )


@router.put("/llm-preferences", response_model=ApiResponse)
async def update_crud_user_llm_preferences(
    preference_update: UserLLMPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户LLM偏好设置"""
    updated_preference = crud_user_llm_preference.update_preference(
        db, user_id=current_user.id, preference_update=preference_update
    )
    
    if not updated_preference:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新LLM偏好设置失败"
        )
    
    return ApiResponse(
        success=True,
        data={"id": updated_preference.id, "updated_at": updated_preference.updated_at},
        message="LLM偏好设置更新成功"
    )


@router.post("/llm-preferences/api-keys", response_model=ApiResponse)
async def add_personal_api_key(
    provider_name: str,
    api_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """添加个人API密钥"""
    if not provider_name or not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="提供商名称和API密钥不能为空"
        )
    
    updated_preference = crud_user_llm_preference.add_personal_api_key(
        db, user_id=current_user.id, provider_name=provider_name, api_key=api_key
    )
    
    return ApiResponse(
        success=True,
        data={"provider": provider_name, "configured": True},
        message=f"{provider_name} API密钥已保存"
    )


@router.delete("/llm-preferences/api-keys/{provider_name}", response_model=ApiResponse)
async def remove_personal_api_key(
    provider_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除个人API密钥"""
    updated_preference = crud_user_llm_preference.remove_personal_api_key(
        db, user_id=current_user.id, provider_name=provider_name
    )
    
    return ApiResponse(
        success=True,
        data={"provider": provider_name, "removed": True},
        message=f"{provider_name} API密钥已删除"
    )


@router.get("/llm-preferences/usage-quota", response_model=ApiResponse)
async def get_user_usage_quota(
    period: str = "monthly",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户使用配额信息"""
    quota = crud_user_llm_usage_quota.get_current_quota(
        db, user_id=current_user.id, period=period
    )
    
    if not quota:
        return ApiResponse(
            success=True,
            data={"quota_exists": False},
            message="未找到配额信息"
        )
    
    quota_info = {
        "quota_period": quota.quota_period,
        "period_start": quota.period_start,
        "period_end": quota.period_end,
        "tokens_used": quota.tokens_used,
        "token_limit": quota.token_limit,
        "requests_made": quota.requests_made,
        "request_limit": quota.request_limit,
        "total_cost": quota.total_cost,
        "cost_limit": quota.cost_limit,
        "is_exceeded": quota.is_exceeded,
        "token_usage_percentage": (quota.tokens_used / quota.token_limit * 100) if quota.token_limit > 0 else 0,
        "cost_usage_percentage": (quota.total_cost / quota.cost_limit * 100) if quota.cost_limit > 0 else 0,
        "request_usage_percentage": (quota.requests_made / quota.request_limit * 100) if quota.request_limit > 0 else 0
    }
    
    return ApiResponse(
        success=True,
        data=quota_info,
        message="获取配额信息成功"
    )


@router.get("/llm-preferences/available-providers", response_model=ApiResponse)
async def get_available_llm_providers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取可用的LLM提供商列表（用于设置页面配置）"""
    # 获取所有活跃的LLM服务器及其提供商
    servers = db.query(LLMServer).filter(
        LLMServer.is_active == True,
        LLMServer.is_healthy == True
    ).all()
    
    providers_info = []
    for server in servers:
        # 获取该服务器的提供商
        for provider in server.providers:
            if provider.is_enabled:
                provider_info = {
                    "server_id": server.id,
                    "server_name": server.name,
                    "provider_name": provider.provider_name,
                    "provider_type": provider.provider_type,
                    "available_models": provider.available_models,
                    "default_model": provider.default_model,
                    "rate_limits": {
                        "requests_per_minute": provider.rate_limit_rpm,
                        "tokens_per_minute": provider.rate_limit_tpm
                    },
                    "priority": provider.priority,
                    "is_healthy": provider.is_healthy
                }
                providers_info.append(provider_info)
    
    return ApiResponse(
        success=True,
        data=providers_info,
        message="获取可用提供商列表成功"
    )


@router.post("/llm-preferences/test-connection", response_model=ApiResponse)
async def test_llm_connection(
    server_id: int,
    provider_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """测试LLM连接"""
    try:
        # 获取用户的API密钥
        api_key = crud_user_llm_preference.get_decrypted_api_key(
            db, user_id=current_user.id, provider_name=provider_name
        )
        
        if not api_key:
            return ApiResponse(
                success=False,
                data={"connected": False},
                message=f"未配置 {provider_name} 的API密钥"
            )
        
        # 实际测试连接
        try:
            # 使用React Agent系统的LLM服务适配器
            from datetime import datetime
            
            # 使用React Agent LLM选择器测试连接
            from app.services.infrastructure.ai.llm.intelligent_selector import IntelligentLLMSelector
            llm_service = IntelligentLLMSelector(db, current_user.id)
            
            # 执行健康检查
            health_result = await llm_service.health_check()
            
            if health_result.get("status") == "healthy":
                return ApiResponse(
                    success=True,
                    data={
                        "connected": True,
                        "provider": provider_name,
                        "server_id": server_id,
                        "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "server_url": llm_service.llm_server_url,
                        "health_info": health_result
                    },
                    message="连接测试成功"
                )
            else:
                return ApiResponse(
                    success=False,
                    data={
                        "connected": False,
                        "error": health_result.get("error", "服务器不健康"),
                        "server_url": llm_service.llm_server_url
                    },
                    message="连接测试失败"
                )
                
        except Exception as test_e:
            logger.error(f"LLM连接测试失败: {test_e}")
            return ApiResponse(
                success=False,
                data={"connected": False, "error": str(test_e)},
                message="连接测试失败"
            )
        
    except Exception as e:
        return ApiResponse(
            success=False,
            data={"connected": False, "error": str(e)},
            message="连接测试失败"
        )