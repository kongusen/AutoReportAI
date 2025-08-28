"""
用户LLM偏好设置模型

为每个用户提供个性化的LLM配置和偏好管理
"""

from sqlalchemy import Column, Integer, String, Boolean, JSON, Text, Float, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base_class import Base


class UserLLMPreference(Base):
    """用户LLM偏好配置"""
    __tablename__ = "user_llm_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # 默认服务器和提供商设置
    default_llm_server_id = Column(Integer, ForeignKey("llm_servers.id"), nullable=True)
    default_provider_name = Column(String(100), nullable=True)  # 在该服务器上的默认提供商
    default_model_name = Column(String(100), nullable=True)     # 默认模型
    
    # 个人API密钥 (可选，用于覆盖服务器密钥)
    personal_api_keys = Column(JSON, default=dict)  # {"openai": "sk-xxx", "anthropic": "sk-ant-xxx"}
    
    # 使用偏好
    preferred_temperature = Column(Float, default=0.7)  # 默认温度参数
    max_tokens_limit = Column(Integer, default=4000)    # 单次请求最大Token数
    
    # 配额管理
    daily_token_quota = Column(Integer, default=50000)  # 每日Token配额
    monthly_cost_limit = Column(Float, default=100.0)   # 每月成本限制
    
    # 高级设置
    enable_caching = Column(Boolean, default=True)      # 是否启用缓存
    cache_ttl_hours = Column(Integer, default=24)       # 缓存时间
    enable_learning = Column(Boolean, default=True)     # 是否参与学习优化
    
    # 提供商优先级 (JSON格式)
    provider_priorities = Column(JSON, default=dict)    # {"openai": 1, "anthropic": 2, "google": 3}
    
    # 模型偏好映射 (JSON格式) 
    model_preferences = Column(JSON, default=dict)      # {"text_generation": "gpt-4", "code_generation": "claude-3"}
    
    # 元数据
    custom_settings = Column(JSON, default=dict)        # 用户自定义设置
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="llm_preference")
    default_server = relationship("LLMServer", foreign_keys=[default_llm_server_id])


class UserLLMUsageQuota(Base):
    """用户LLM使用配额记录"""
    __tablename__ = "user_llm_usage_quotas"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # 配额周期
    quota_period = Column(String(20), default="monthly")  # daily, weekly, monthly
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # 使用统计
    tokens_used = Column(Integer, default=0)
    requests_made = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    
    # 限制设置
    token_limit = Column(Integer, nullable=False)
    request_limit = Column(Integer, default=1000)
    cost_limit = Column(Float, nullable=False)
    
    # 状态
    is_exceeded = Column(Boolean, default=False)
    warning_sent = Column(Boolean, default=False)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    user = relationship("User")