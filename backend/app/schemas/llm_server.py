"""
LLM服务器相关Pydantic模式

用于API请求/响应的数据验证和序列化
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum


class ProviderType(str, Enum):
    """LLM提供商类型枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"


class ModelType(str, Enum):
    """模型类型枚举"""
    CHAT = "chat"
    THINK = "think"
    EMBED = "embed"
    IMAGE = "image"


# === LLM服务器模式 ===

class LLMServerBase(BaseModel):
    """LLM服务器基础模式"""
    name: str = Field(..., min_length=1, max_length=255, description="服务器名称")
    description: Optional[str] = Field(None, description="服务器描述")
    base_url: str = Field(..., description="服务器基础URL")
    provider_type: ProviderType = Field(ProviderType.OPENAI, description="提供商类型")
    auth_enabled: bool = Field(True, description="是否启用认证")
    timeout_seconds: int = Field(60, ge=1, le=600, description="超时时间（秒）")
    max_retries: int = Field(3, ge=0, le=10, description="最大重试次数")


class LLMServerCreate(LLMServerBase):
    """创建LLM服务器"""
    api_key: Optional[str] = Field(None, description="API密钥")
    user_id: Optional[UUID] = Field(None, description="所属用户ID（系统自动设置）")


class LLMServerUpdate(BaseModel):
    """更新LLM服务器"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    base_url: Optional[str] = None
    provider_type: Optional[ProviderType] = None
    api_key: Optional[str] = None
    auth_enabled: Optional[bool] = None
    is_active: Optional[bool] = None
    timeout_seconds: Optional[int] = Field(None, ge=1, le=600)
    max_retries: Optional[int] = Field(None, ge=0, le=10)


class LLMServerResponse(LLMServerBase):
    """LLM服务器响应"""
    id: int
    server_id: UUID
    is_active: bool
    is_healthy: bool
    last_health_check: Optional[datetime]
    server_version: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # 模型统计
    models_count: Optional[int] = None
    healthy_models_count: Optional[int] = None
    
    class Config:
        from_attributes = True


# === LLM模型模式 ===

class LLMModelBase(BaseModel):
    """LLM模型基础模式"""
    name: str = Field(..., max_length=255, description="模型名称")
    display_name: str = Field(..., max_length=255, description="显示名称")
    description: Optional[str] = Field(None, description="模型描述")
    model_type: ModelType = Field(..., description="模型类型")
    provider_name: str = Field(..., max_length=100, description="提供商名称")
    priority: int = Field(50, ge=1, le=100, description="优先级")
    max_tokens: Optional[int] = Field(None, ge=1, description="最大Token数")
    temperature_default: float = Field(0.7, ge=0.0, le=2.0, description="默认温度")
    supports_system_messages: bool = Field(True, description="是否支持系统消息")
    supports_function_calls: bool = Field(False, description="是否支持函数调用")
    supports_thinking: bool = Field(False, description="是否支持思考模式")


class LLMModelCreate(LLMModelBase):
    """创建LLM模型"""
    server_id: int = Field(..., description="关联的服务器ID")

    # 入参容错：允许传入大写名称，转换为值（Pydantic v2 钩子）
    def __pydantic_post_init__(self, __context) -> None:  # type: ignore[override]
        try:
            if isinstance(self.model_type, str):
                lowered = self.model_type.lower()
                self.model_type = ModelType(lowered)  # type: ignore
        except Exception:
            # 保底不抛出，交给后续校验
            pass


class LLMModelUpdate(BaseModel):
    """更新LLM模型"""
    display_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=1, le=100)
    max_tokens: Optional[int] = Field(None, ge=1)
    temperature_default: Optional[float] = Field(None, ge=0.0, le=2.0)
    supports_system_messages: Optional[bool] = None
    supports_function_calls: Optional[bool] = None
    supports_thinking: Optional[bool] = None


class LLMModelResponse(LLMModelBase):
    """LLM模型响应"""
    id: int
    server_id: int
    is_active: bool
    is_healthy: bool
    last_health_check: Optional[datetime]
    health_check_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LLMModelHealthCheck(BaseModel):
    """模型健康检查请求"""
    model_id: Optional[int] = None
    test_message: str = Field(default="你好", description="测试消息")


# === 批量操作模式 ===

class LLMServerBatchOperation(BaseModel):
    """LLM服务器批量操作"""
    operation: str = Field(..., description="操作类型: activate, deactivate, health_check")
    server_ids: List[int] = Field(..., description="服务器ID列表")


class LLMModelBatchOperation(BaseModel):
    """LLM模型批量操作"""
    operation: str = Field(..., description="操作类型: activate, deactivate, health_check")
    model_ids: List[int] = Field(..., description="模型ID列表")


# === 健康检查响应模式 ===

class LLMModelHealthResponse(BaseModel):
    """模型健康检查响应"""
    model_id: int
    model_name: str
    server_id: int
    is_healthy: bool
    response_time: float
    error_message: Optional[str] = None
    test_response: Optional[str] = None
    checked_at: str


class LLMServerHealthResponse(BaseModel):
    """服务器健康检查响应"""
    server_id: int
    server_name: str
    is_healthy: bool
    response_time: float
    total_models: int
    healthy_models: int
    health_rate: float
    average_model_response_time: float
    model_results: List[LLMModelHealthResponse] = Field(default_factory=list)
    checked_at: str
    error_message: Optional[str] = None