"""
用户LLM偏好管理API端点

提供用户个性化LLM配置、偏好设置、智能推荐等API接口
与数据库驱动的智能选择器完全集成
"""

from datetime import datetime
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.crud.crud_llm_server import crud_llm_server
from app.crud.crud_llm_model import crud_llm_model  
from app.models.user_llm_preference import UserLLMPreference, UserLLMUsageQuota
from app.models.llm_server import LLMServer, LLMModel
from app.schemas.user_llm_preference import (
    UserLLMPreferenceCreate,
    UserLLMPreferenceUpdate, 
    UserLLMPreferenceResponse,
    UserLLMUsageQuotaResponse,
    ModelRecommendationRequest,
    ModelRecommendationResponse
)

router = APIRouter()


# === 用户偏好管理 ===

@router.get("/preferences", response_model=UserLLMPreferenceResponse)
def get_user_preferences(
    *,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user)
):
    """获取当前用户的LLM偏好设置"""
    
    # 查找用户偏好
    preference = db.query(UserLLMPreference).filter(
        UserLLMPreference.user_id == current_user.id
    ).first()
    
    if not preference:
        # 创建默认偏好设置
        default_preference = UserLLMPreference(
            user_id=current_user.id,
            preferred_temperature=0.7,
            max_tokens_limit=4000,
            daily_token_quota=50000,
            monthly_cost_limit=100.0,
            enable_caching=True,
            cache_ttl_hours=24,
            enable_learning=True
        )
        
        db.add(default_preference)
        db.commit()
        db.refresh(default_preference)
        preference = default_preference
    
    # 获取默认服务器信息
    default_server = None
    if preference.default_llm_server_id:
        default_server = crud_llm_server.get(db, id=preference.default_llm_server_id)
    
    # 构建响应
    response_data = {
        **preference.__dict__,
        "default_server_name": default_server.name if default_server else None,
        "default_server_url": default_server.base_url if default_server else None,
    }
    
    return response_data


@router.put("/preferences", response_model=UserLLMPreferenceResponse)
def update_user_preferences(
    *,
    db: Session = Depends(deps.get_db),
    preference_in: UserLLMPreferenceUpdate,
    current_user = Depends(deps.get_current_active_user)
):
    """更新用户LLM偏好设置"""
    
    # 查找现有偏好
    preference = db.query(UserLLMPreference).filter(
        UserLLMPreference.user_id == current_user.id
    ).first()
    
    if not preference:
        # 创建新偏好
        preference_data = preference_in.dict(exclude_unset=True)
        preference_data["user_id"] = current_user.id
        preference = UserLLMPreference(**preference_data)
        db.add(preference)
    else:
        # 更新现有偏好
        update_data = preference_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(preference, field, value)
        
        preference.updated_at = datetime.utcnow()
    
    # 验证默认服务器是否存在
    if preference.default_llm_server_id:
        server = crud_llm_server.get(db, id=preference.default_llm_server_id)
        if not server or not server.is_active:
            raise HTTPException(
                status_code=400,
                detail="指定的默认LLM服务器不存在或未激活"
            )
    
    db.commit()
    db.refresh(preference)
    
    return preference


# === 用户配额管理 ===

@router.get("/usage-quota", response_model=UserLLMUsageQuotaResponse)
def get_user_usage_quota(
    *,
    db: Session = Depends(deps.get_db),
    period: str = Query(default="monthly", pattern="^(daily|weekly|monthly)$"),
    current_user = Depends(deps.get_current_active_user)
):
    """获取用户使用配额信息"""
    
    # 计算期间开始时间
    now = datetime.utcnow()
    if period == "daily":
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "weekly":
        days_since_monday = now.weekday()
        period_start = (now - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    else:  # monthly
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 查找或创建配额记录
    quota = db.query(UserLLMUsageQuota).filter(
        UserLLMUsageQuota.user_id == current_user.id,
        UserLLMUsageQuota.quota_period == period,
        UserLLMUsageQuota.period_start == period_start
    ).first()
    
    if not quota:
        # 获取用户偏好中的限制设置
        preference = db.query(UserLLMPreference).filter(
            UserLLMPreference.user_id == current_user.id
        ).first()
        
        if period == "daily":
            token_limit = preference.daily_token_quota if preference else 50000
            cost_limit = preference.monthly_cost_limit / 30 if preference else 3.33
        elif period == "monthly":
            token_limit = preference.daily_token_quota * 30 if preference else 1500000
            cost_limit = preference.monthly_cost_limit if preference else 100.0
        else:  # weekly
            token_limit = preference.daily_token_quota * 7 if preference else 350000
            cost_limit = preference.monthly_cost_limit / 4 if preference else 25.0
        
        # 计算期间结束时间
        if period == "daily":
            period_end = period_start + timedelta(days=1)
        elif period == "weekly":
            period_end = period_start + timedelta(days=7)
        else:  # monthly
            # 下个月的第一天
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1)
        
        quota = UserLLMUsageQuota(
            user_id=current_user.id,
            quota_period=period,
            period_start=period_start,
            period_end=period_end,
            tokens_used=0,
            requests_made=0,
            total_cost=0.0,
            token_limit=token_limit,
            cost_limit=cost_limit
        )
        
        db.add(quota)
        db.commit()
        db.refresh(quota)
    
    # 计算使用率
    token_usage_rate = quota.tokens_used / quota.token_limit if quota.token_limit > 0 else 0
    cost_usage_rate = quota.total_cost / quota.cost_limit if quota.cost_limit > 0 else 0
    
    response_data = {
        **quota.__dict__,
        "token_usage_rate": token_usage_rate,
        "cost_usage_rate": cost_usage_rate,
        "is_token_limit_exceeded": quota.tokens_used >= quota.token_limit,
        "is_cost_limit_exceeded": quota.total_cost >= quota.cost_limit
    }
    
    return response_data


# === 智能模型推荐 === 
# 注意：复杂的推荐逻辑已迁移至简化选择器
# 使用 /v1/simple-model-selection/select 获得更好的体验


# === 用户可用模型列表 ===

@router.get("/available-models")
def get_user_available_models(
    *,
    db: Session = Depends(deps.get_db),
    model_type: Optional[str] = None,
    provider_name: Optional[str] = None,
    supports_thinking: Optional[bool] = None,
    current_user = Depends(deps.get_current_active_user)
):
    """获取用户可用的模型列表"""
    
    # 获取活跃且健康的服务器
    active_servers = crud_llm_server.get_multi_by_filter(
        db, is_active=True, is_healthy=True
    )
    
    if not active_servers:
        return {
            "servers": [],
            "models": [],
            "total_servers": 0,
            "total_models": 0
        }
    
    server_ids = [server.id for server in active_servers]
    
    # 获取这些服务器上的活跃且健康的模型
    models_query = db.query(LLMModel).join(LLMServer).filter(
        LLMModel.server_id.in_(server_ids),
        LLMModel.is_active == True,
        LLMModel.is_healthy == True
    )
    
    # 应用过滤条件
    if model_type:
        models_query = models_query.filter(LLMModel.model_type == model_type)
    
    if provider_name:
        models_query = models_query.filter(LLMModel.provider_name == provider_name)
    
    if supports_thinking is not None:
        models_query = models_query.filter(LLMModel.supports_thinking == supports_thinking)
    
    models = models_query.all()
    
    # 构建服务器映射
    server_map = {server.id: server for server in active_servers}
    
    # 构建响应
    model_list = []
    for model in models:
        server = server_map[model.server_id]
        model_info = {
            "model_id": model.id,
            "model_name": model.name,
            "display_name": model.display_name,
            "model_type": model.model_type,
            "provider_name": model.provider_name,
            "supports_thinking": model.supports_thinking,
            "supports_function_calls": model.supports_function_calls,
            "max_tokens": model.max_tokens,
            "server_info": {
                "server_id": server.id,
                "server_name": server.name,
                "provider_type": server.provider_type,
                "base_url": server.base_url
            }
        }
        model_list.append(model_info)
    
    return {
        "servers": [
            {
                "server_id": server.id,
                "name": server.name,
                "provider_type": server.provider_type,
                "base_url": server.base_url,
                "model_count": sum(1 for model in models if model.server_id == server.id)
            }
            for server in active_servers
        ],
        "models": model_list,
        "total_servers": len(active_servers),
        "total_models": len(model_list)
    }


# === 使用反馈记录 ===
# 注意：反馈功能已简化，复杂的学习机制已移除
# 如需反馈功能，请使用简化的模型统计接口