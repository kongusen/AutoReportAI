import enum

from sqlalchemy import Column, Enum, Integer, String

from app.db.base import Base


class AIProviderType(str, enum.Enum):
    openai = "openai"
    azure_openai = "azure_openai"
    mock = "mock"


class AIProvider(Base):
    __tablename__ = "ai_providers"

    id = Column(Integer, primary_key=True, index=True)
    provider_name = Column(String, index=True, unique=True, nullable=False)
    provider_type = Column(Enum(AIProviderType), nullable=False)
    api_base_url = Column(String)
    api_key = Column(String)  # In a real production system, this should be encrypted
    default_model_name = Column(String)
    is_active = Column(Integer, default=0)  # 0 for false, 1 for true
