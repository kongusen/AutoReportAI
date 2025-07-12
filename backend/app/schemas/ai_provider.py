from typing import Optional

from pydantic import BaseModel, HttpUrl, constr

from app.models.ai_provider import AIProviderType


class AIProviderBase(BaseModel):
    provider_name: constr(strip_whitespace=True, min_length=1, max_length=100)
    provider_type: AIProviderType
    api_base_url: Optional[HttpUrl] = None
    default_model_name: Optional[str] = None
    is_active: Optional[int] = 0


class AIProviderCreate(AIProviderBase):
    api_key: constr(strip_whitespace=True, min_length=10)


class AIProviderUpdate(AIProviderBase):
    api_key: Optional[constr(strip_whitespace=True, min_length=10)] = None


class AIProvider(AIProviderBase):
    id: int

    class Config:
        orm_mode = True


class AIProviderInDB(AIProvider):
    api_key: Optional[str] = None
