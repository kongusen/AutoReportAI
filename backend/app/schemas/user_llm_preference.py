"""
用户LLM偏好设置Pydantic模式

用于API请求/响应的数据验证和序列化
"""

from datetime import datetime
from typing import Dict, Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field


# === 用户LLM偏好模式 ===

class UserLLMPreferenceBase(BaseModel):
    """用户LLM偏好基础模式"""
    default_llm_server_id: Optional[int] = Field(None, description="默认LLM服务器ID")
    default_provider_name: Optional[str] = Field(None, max_length=100, description="默认提供商名称")
    default_model_name: Optional[str] = Field(None, max_length=100, description="默认模型名称")
    preferred_temperature: float = Field(0.7, ge=0.0, le=2.0, description="默认温度参数")
    max_tokens_limit: int = Field(4000, ge=100, le=32000, description="单次请求最大Token数")
    daily_token_quota: int = Field(50000, ge=1000, le=1000000, description="每日Token配额")
    monthly_cost_limit: float = Field(100.0, ge=10.0, le=10000.0, description="每月成本限制")
    enable_caching: bool = Field(True, description="是否启用缓存")
    cache_ttl_hours: int = Field(24, ge=1, le=168, description="缓存时间(小时)")
    enable_learning: bool = Field(True, description="是否参与学习优化")


class UserLLMPreferenceCreate(UserLLMPreferenceBase):
    """创建用户LLM偏好"""
    user_id: UUID = Field(..., description="用户ID")
    personal_api_keys: Dict[str, str] = Field(default_factory=dict, description="个人API密钥")
    provider_priorities: Dict[str, int] = Field(default_factory=dict, description="提供商优先级")
    model_preferences: Dict[str, str] = Field(default_factory=dict, description="模型偏好映射")
    custom_settings: Dict[str, Any] = Field(default_factory=dict, description="自定义设置")


class UserLLMPreferenceUpdate(BaseModel):
    """更新用户LLM偏好"""
    default_llm_server_id: Optional[int] = None
    default_provider_name: Optional[str] = Field(None, max_length=100)
    default_model_name: Optional[str] = Field(None, max_length=100)
    preferred_temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens_limit: Optional[int] = Field(None, ge=100, le=32000)
    daily_token_quota: Optional[int] = Field(None, ge=1000, le=1000000)
    monthly_cost_limit: Optional[float] = Field(None, ge=10.0, le=10000.0)
    enable_caching: Optional[bool] = None
    cache_ttl_hours: Optional[int] = Field(None, ge=1, le=168)
    enable_learning: Optional[bool] = None
    personal_api_keys: Optional[Dict[str, str]] = None
    provider_priorities: Optional[Dict[str, int]] = None
    model_preferences: Optional[Dict[str, str]] = None
    custom_settings: Optional[Dict[str, Any]] = None


class UserLLMPreferenceResponse(UserLLMPreferenceBase):
    """用户LLM偏好响应"""
    id: int
    user_id: UUID
    personal_api_keys: Dict[str, str]  # 注意：实际返回时应过滤敏感信息
    provider_priorities: Dict[str, int]
    model_preferences: Dict[str, str]
    custom_settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# === 用户配额模式 ===

class UserLLMUsageQuotaBase(BaseModel):
    """用户LLM配额基础模式"""
    quota_period: str = Field("monthly", description="配额周期")
    period_start: datetime = Field(..., description="周期开始时间")
    period_end: datetime = Field(..., description="周期结束时间")
    token_limit: int = Field(..., ge=1000, description="Token限制")
    request_limit: int = Field(1000, ge=10, description="请求数限制")
    cost_limit: float = Field(..., ge=1.0, description="成本限制")


class UserLLMUsageQuotaCreate(UserLLMUsageQuotaBase):
    """创建用户配额"""
    user_id: UUID = Field(..., description="用户ID")


class UserLLMUsageQuotaResponse(UserLLMUsageQuotaBase):
    """用户配额响应"""
    id: int
    user_id: UUID
    tokens_used: int
    requests_made: int
    total_cost: float
    is_exceeded: bool
    warning_sent: bool
    created_at: datetime
    updated_at: datetime
    
    # 计算属性
    @property
    def token_usage_percentage(self) -> float:
        """Token使用百分比"""
        return (self.tokens_used / self.token_limit * 100) if self.token_limit > 0 else 0.0
    
    @property
    def cost_usage_percentage(self) -> float:
        """成本使用百分比"""
        return (self.total_cost / self.cost_limit * 100) if self.cost_limit > 0 else 0.0
    
    class Config:
        from_attributes = True


# === 安全版本（隐藏敏感信息）===

class UserLLMPreferenceSecureResponse(BaseModel):
    """用户LLM偏好安全响应（隐藏API密钥）"""
    id: int
    user_id: UUID
    default_llm_server_id: Optional[int]
    default_provider_name: Optional[str]
    default_model_name: Optional[str]
    preferred_temperature: float
    max_tokens_limit: int
    daily_token_quota: int
    monthly_cost_limit: float
    enable_caching: bool
    cache_ttl_hours: int
    enable_learning: bool
    
    # 只显示API密钥的提供商列表，不显示实际密钥
    configured_providers: list[str] = Field(default_factory=list, description="已配置API密钥的提供商")
    provider_priorities: Dict[str, int]
    model_preferences: Dict[str, str]
    custom_settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# === 智能模型推荐 ===

class ModelRecommendationRequest(BaseModel):
    """智能模型推荐请求"""
    task_type: str = Field(..., pattern="^(reasoning|coding|creative|analysis|translation|qa|summarization|general)$")
    complexity: str = Field(default="medium", pattern="^(simple|medium|complex|expert)$")
    estimated_tokens: int = Field(default=1000, ge=1, le=100000)
    cost_sensitive: bool = False
    speed_priority: bool = False
    accuracy_critical: bool = False
    creativity_required: bool = False
    language: str = "zh"
    domain: Optional[str] = None
    max_cost_per_request: Optional[float] = Field(None, ge=0.0)
    max_latency_ms: Optional[int] = Field(None, ge=100)
    min_capability_score: Optional[float] = Field(default=0.6, ge=0.0, le=1.0)
    preferred_providers: Optional[list[str]] = None
    excluded_models: Optional[list[str]] = None
    require_function_calling: bool = False
    require_vision: bool = False
    agent_id: Optional[str] = None


class ModelRecommendationResponse(BaseModel):
    """智能模型推荐响应"""
    model: str
    provider: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    expected_cost: float
    expected_latency: int
    capability_match_score: float = Field(..., ge=0.0, le=1.0)
    fallback_models: list[list[str]]
    recommendation_timestamp: datetime