"""
用户LLM偏好CRUD操作
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.crud.base import CRUDBase
from app.models.user_llm_preference import UserLLMPreference, UserLLMUsageQuota
from app.schemas.user_llm_preference import UserLLMPreferenceCreate, UserLLMPreferenceUpdate


class CRUDUserLLMPreference(CRUDBase[UserLLMPreference, UserLLMPreferenceCreate, UserLLMPreferenceUpdate]):
    """用户LLM偏好CRUD操作"""
    
    def get_by_user_id(self, db: Session, user_id: str) -> Optional[UserLLMPreference]:
        """通过用户ID获取偏好设置"""
        return db.query(self.model).filter(self.model.user_id == user_id).first()
    
    def get_or_create(
        self, 
        db: Session, 
        user_id: str, 
        defaults: Optional[dict] = None
    ) -> UserLLMPreference:
        """获取或创建用户的偏好设置"""
        preference = self.get_by_user_id(db, user_id)
        if not preference:
            create_data = {"user_id": user_id}
            if defaults:
                create_data.update(defaults)
            preference = self.create(db, obj_in=create_data)
        return preference
    
    def update_personal_api_key(
        self,
        db: Session,
        user_id: str,
        provider: str,
        api_key: str
    ) -> Optional[UserLLMPreference]:
        """更新用户的个人API密钥"""
        preference = self.get_by_user_id(db, user_id)
        if preference:
            personal_api_keys = preference.personal_api_keys or {}
            personal_api_keys[provider] = api_key
            preference.personal_api_keys = personal_api_keys
            db.commit()
            db.refresh(preference)
        return preference
    
    def remove_personal_api_key(
        self,
        db: Session,
        user_id: str,
        provider: str
    ) -> Optional[UserLLMPreference]:
        """移除用户的个人API密钥"""
        preference = self.get_by_user_id(db, user_id)
        if preference and preference.personal_api_keys:
            personal_api_keys = preference.personal_api_keys.copy()
            personal_api_keys.pop(provider, None)
            preference.personal_api_keys = personal_api_keys
            db.commit()
            db.refresh(preference)
        return preference
    
    def update_provider_priority(
        self,
        db: Session,
        user_id: str,
        provider: str,
        priority: int
    ) -> Optional[UserLLMPreference]:
        """更新提供商优先级"""
        preference = self.get_by_user_id(db, user_id)
        if preference:
            provider_priorities = preference.provider_priorities or {}
            provider_priorities[provider] = priority
            preference.provider_priorities = provider_priorities
            db.commit()
            db.refresh(preference)
        return preference
    
    def update_model_preference(
        self,
        db: Session,
        user_id: str,
        task_type: str,
        model_name: str
    ) -> Optional[UserLLMPreference]:
        """更新模型偏好"""
        preference = self.get_by_user_id(db, user_id)
        if preference:
            model_preferences = preference.model_preferences or {}
            model_preferences[task_type] = model_name
            preference.model_preferences = model_preferences
            db.commit()
            db.refresh(preference)
        return preference


class CRUDUserLLMUsageQuota(CRUDBase[UserLLMUsageQuota, None, None]):
    """用户LLM使用配额CRUD操作"""
    
    def get_current_quota(
        self, 
        db: Session, 
        user_id: str, 
        period: str = "monthly"
    ) -> Optional[UserLLMUsageQuota]:
        """获取用户当前周期的配额"""
        now = datetime.utcnow()
        return db.query(self.model).filter(
            and_(
                self.model.user_id == user_id,
                self.model.quota_period == period,
                self.model.period_start <= now,
                self.model.period_end >= now
            )
        ).first()
    
    def create_or_update_quota(
        self,
        db: Session,
        user_id: str,
        period: str,
        period_start: str,
        period_end: str,
        token_limit: int,
        cost_limit: float,
        request_limit: int = 1000
    ) -> UserLLMUsageQuota:
        """创建或更新用户配额"""
        quota = self.get_current_quota(db, user_id, period)
        if quota:
            # 更新现有配额
            quota.token_limit = token_limit
            quota.cost_limit = cost_limit
            quota.request_limit = request_limit
        else:
            # 创建新配额
            quota_data = {
                "user_id": user_id,
                "quota_period": period,
                "period_start": period_start,
                "period_end": period_end,
                "token_limit": token_limit,
                "cost_limit": cost_limit,
                "request_limit": request_limit
            }
            quota = self.create(db, obj_in=quota_data)
        
        db.commit()
        db.refresh(quota)
        return quota
    
    def increment_usage(
        self,
        db: Session,
        user_id: str,
        tokens: int = 0,
        cost: float = 0.0
    ) -> Optional[UserLLMUsageQuota]:
        """增加用户使用量"""
        quota = self.get_current_quota(db, user_id)
        if quota:
            quota.tokens_used += tokens
            quota.requests_made += 1
            quota.total_cost += cost
            
            # 检查是否超出限制
            if (quota.tokens_used > quota.token_limit or 
                quota.total_cost > quota.cost_limit or
                quota.requests_made > quota.request_limit):
                quota.is_exceeded = True
            
            db.commit()
            db.refresh(quota)
        return quota
    
    def reset_quota(
        self,
        db: Session,
        user_id: str,
        period: str
    ) -> Optional[UserLLMUsageQuota]:
        """重置用户配额"""
        quota = self.get_current_quota(db, user_id, period)
        if quota:
            quota.tokens_used = 0
            quota.requests_made = 0
            quota.total_cost = 0.0
            quota.is_exceeded = False
            quota.warning_sent = False
            db.commit()
            db.refresh(quota)
        return quota
    
    def get_usage_stats(
        self,
        db: Session,
        user_id: str,
        period: str
    ) -> dict:
        """获取用户使用统计"""
        from sqlalchemy import func
        
        quotas = db.query(self.model).filter(
            and_(
                self.model.user_id == user_id,
                self.model.quota_period == period
            )
        ).all()
        
        total_tokens = sum(q.tokens_used for q in quotas)
        total_requests = sum(q.requests_made for q in quotas)
        total_cost = sum(q.total_cost for q in quotas)
        
        return {
            "total_tokens": total_tokens,
            "total_requests": total_requests,
            "total_cost": total_cost,
            "quota_count": len(quotas)
        }


# 创建CRUD实例
crud_user_llm_preference = CRUDUserLLMPreference(UserLLMPreference)
crud_user_llm_usage_quota = CRUDUserLLMUsageQuota(UserLLMUsageQuota)