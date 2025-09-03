"""
LLM服务器相关数据模型

用于管理独立LLM服务器的配置、状态和模型管理
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, JSON, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.db.base_class import Base


class ProviderType(str, enum.Enum):
    """LLM提供商类型枚举"""
    OPENAI = "openai"        # OpenAI格式 (GPT, ChatGPT等)
    ANTHROPIC = "anthropic"  # Anthropic格式 (Claude)
    GOOGLE = "google"        # Google格式 (Gemini, PaLM等)
    COHERE = "cohere"        # Cohere格式
    HUGGINGFACE = "huggingface"  # HuggingFace格式
    CUSTOM = "custom"        # 自定义格式


class ModelType(str, enum.Enum):
    """模型类型枚举"""
    DEFAULT = "default"  # 默认模型
    THINK = "think"      # 思考模型，支持CoT推理


class LLMServer(Base):
    """LLM服务器实例"""
    __tablename__ = "llm_servers"
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # 用户绑定
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    
    # 基本信息
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    base_url = Column(String(512), nullable=False)
    
    # 提供商类型
    provider_type = Column(
        Enum(
            ProviderType,
            values_callable=lambda obj: [e.value for e in obj]
        ),
        nullable=False,
        default=ProviderType.OPENAI.value,
        index=True
    )
    
    # 认证信息
    api_key = Column(Text, nullable=True)
    auth_enabled = Column(Boolean, default=True)
    
    # 状态信息
    is_active = Column(Boolean, default=True)
    is_healthy = Column(Boolean, default=False)
    last_health_check = Column(DateTime, nullable=True)
    
    # 配置信息
    timeout_seconds = Column(Integer, default=60)
    max_retries = Column(Integer, default=3)
    
    # 版本和元数据
    server_version = Column(String(50), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    models = relationship("LLMModel", back_populates="server", cascade="all, delete-orphan")


class LLMModel(Base):
    """LLM模型配置"""
    __tablename__ = "llm_models"
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("llm_servers.id"), nullable=False)
    
    # 基本信息
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # 模型类型和能力
    # 使用枚举的值（default/think）持久化到数据库，避免写入枚举名（DEFAULT/THINK/...）
    model_type = Column(
        Enum(
            ModelType,
            values_callable=lambda obj: [e.value for e in obj]
        ),
        nullable=False,
        index=True,
    )
    provider_name = Column(String(100), nullable=False, index=True)  # openai, anthropic, etc.
    
    # 配置信息  
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=50)  # 优先级，数字越小优先级越高
    
    # 健康状态
    is_healthy = Column(Boolean, default=False)
    last_health_check = Column(DateTime, nullable=True)
    health_check_message = Column(Text, nullable=True)
    
    # 配置参数
    max_tokens = Column(Integer, nullable=True)
    temperature_default = Column(Float, default=0.7)
    supports_system_messages = Column(Boolean, default=True)
    supports_function_calls = Column(Boolean, default=False)
    supports_thinking = Column(Boolean, default=False)  # 是否支持思考模式
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    server = relationship("LLMServer", back_populates="models")
    
    def __repr__(self):
        return f"<LLMModel(name='{self.name}', type='{self.model_type}', server='{self.server_id}')>"

