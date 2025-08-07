from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, constr

from app.models.ai_provider import AIProviderType


class AIProviderBase(BaseModel):
    provider_name: constr(strip_whitespace=True, min_length=1, max_length=100)
    provider_type: AIProviderType
    api_base_url: Optional[str] = None
    default_model_name: Optional[str] = None
    is_active: Optional[bool] = False


class AIProviderCreate(AIProviderBase):
    api_key: constr(strip_whitespace=True, min_length=10)


class AIProviderUpdate(AIProviderBase):
    api_key: Optional[constr(strip_whitespace=True, min_length=10)] = None


class AIProvider(AIProviderBase):
    id: int
    user_id: UUID

    class Config:
        from_attributes = True


class AIProviderInDB(AIProvider):
    api_key: str  # Include the encrypted key in the DB model


class AIProviderResponse(AIProviderBase):
    id: int
    # Note: api_key is excluded from the response for security


class AIProviderTestResponse(BaseModel):
    """AI提供商测试响应模型"""
    success: bool
    message: str
    response_time: Optional[float] = None
    test_response: Optional[str] = None
    model_info: Optional[Dict[str, Any]] = None
