from pydantic import BaseModel, HttpUrl
from typing import Optional
from app.models.ai_provider import AIProviderType

class AIProviderBase(BaseModel):
    provider_name: str
    provider_type: AIProviderType
    api_base_url: Optional[HttpUrl] = None
    default_model_name: Optional[str] = None
    is_active: Optional[int] = 0

class AIProviderCreate(AIProviderBase):
    api_key: Optional[str] = None

class AIProviderUpdate(AIProviderBase):
    api_key: Optional[str] = None

class AIProvider(AIProviderBase):
    id: int

    class Config:
        orm_mode = True

class AIProviderInDB(AIProvider):
    api_key: Optional[str] = None 