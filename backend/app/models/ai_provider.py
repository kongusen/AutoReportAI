import enum

from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base


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
    is_active = Column(Boolean, default=False)  # 使用布尔类型

    # Foreign key to link this AI provider to the user who created it
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    user = relationship("User", back_populates="ai_providers")
