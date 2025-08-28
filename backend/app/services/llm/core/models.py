"""
数据模型定义 - 独立LLM服务器的所有数据结构

定义统一的请求/响应格式，兼容多种LLM提供商
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    """支持的LLM提供商类型"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google" 
    OLLAMA = "ollama"
    AZURE_OPENAI = "azure_openai"
    HUGGINGFACE = "huggingface"


class MessageRole(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class ResponseFormat(str, Enum):
    """响应格式"""
    TEXT = "text"
    JSON = "json_object"


# === 基础数据结构 ===

class ChatMessage(BaseModel):
    """聊天消息"""
    role: MessageRole
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class UsageInfo(BaseModel):
    """Token使用信息"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ProviderConfig(BaseModel):
    """提供商配置"""
    type: ProviderType
    api_key: str
    api_base: Optional[str] = None
    organization: Optional[str] = None
    default_model: Optional[str] = None
    max_requests_per_minute: int = 60
    max_tokens_per_minute: int = 40000
    timeout: int = 60
    enabled: bool = True
    priority: int = 50  # 优先级，数字越小优先级越高
    
    # 特定提供商的额外配置
    extra_config: Optional[Dict[str, Any]] = None


# === 请求和响应模型 ===

class LLMRequest(BaseModel):
    """统一的LLM请求格式"""
    
    # 核心参数
    messages: List[ChatMessage]
    model: Optional[str] = None
    
    # 生成参数
    max_tokens: Optional[int] = Field(None, ge=1, le=32000)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    
    # 输出控制
    response_format: Optional[ResponseFormat] = ResponseFormat.TEXT
    stop: Optional[Union[str, List[str]]] = None
    stream: bool = False
    
    # 函数调用
    functions: Optional[List[Dict[str, Any]]] = None
    function_call: Optional[Union[str, Dict[str, Any]]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    
    # LLM服务器特定参数
    provider_preference: Optional[List[str]] = None  # 提供商偏好顺序
    cache_enabled: bool = True  # 是否启用缓存
    cache_ttl: int = 3600  # 缓存生存时间(秒)
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LLMResponse(BaseModel):
    """统一的LLM响应格式"""
    
    # 响应内容
    content: str
    finish_reason: Optional[str] = None
    
    # 模型信息
    model: str
    provider: str
    
    # Token使用统计
    usage: UsageInfo
    
    # 成本和性能
    cost_estimate: Optional[float] = None
    response_time: float
    
    # 元数据
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None
    
    # 函数调用结果
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    
    # LLM服务器信息
    llm_server_info: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# === 提供商和系统状态 ===

class LLMProvider(BaseModel):
    """LLM提供商信息"""
    name: str
    type: ProviderType
    status: str  # healthy, unhealthy, unknown
    models: List[str] = []
    capabilities: List[str] = []
    cost_info: Dict[str, Any] = {}
    rate_limits: Dict[str, Any] = {}
    metadata: Optional[Dict[str, Any]] = None


class HealthStatus(BaseModel):
    """系统健康状态"""
    status: str  # healthy, partial, unhealthy, not_initialized
    message: str
    providers: Dict[str, Dict[str, Any]]
    uptime: float
    total_requests: int
    success_rate: float
    metadata: Optional[Dict[str, Any]] = None


# === 统计和监控 ===

class UsageStats(BaseModel):
    """使用统计信息"""
    user_id: str
    period_hours: int
    
    # 请求统计
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    
    # Token统计
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    
    # 成本统计
    estimated_cost: float
    
    # 性能统计
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    
    # 提供商使用分布
    provider_usage: Dict[str, Dict[str, Any]]
    
    # 模型使用分布
    model_usage: Dict[str, Dict[str, Any]]
    
    # 时间分布
    hourly_breakdown: List[Dict[str, Any]]


class MetricsSnapshot(BaseModel):
    """指标快照"""
    timestamp: datetime
    
    # 系统指标
    active_providers: int
    total_providers: int
    
    # 实时指标
    requests_per_second: float
    avg_response_time: float
    cache_hit_rate: float
    
    # 错误率
    error_rate: float
    timeout_rate: float
    
    # 资源使用
    memory_usage: Optional[Dict[str, Any]] = None
    cpu_usage: Optional[float] = None


# === 缓存相关 ===

class CacheEntry(BaseModel):
    """缓存条目"""
    key: str
    response: LLMResponse
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    user_id: str
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CacheStats(BaseModel):
    """缓存统计"""
    total_entries: int
    total_size_bytes: int
    hit_count: int
    miss_count: int
    hit_rate: float
    eviction_count: int
    
    # 用户缓存分布
    user_distribution: Dict[str, int]
    
    # TTL分布
    ttl_distribution: Dict[str, int]


# === 错误处理 ===

class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    error_type: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProviderError(BaseModel):
    """提供商错误信息"""
    provider: str
    error_type: str
    error_message: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    recovery_suggestion: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# === 负载均衡 ===

class LoadBalanceStrategy(str, Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted" 
    LEAST_CONNECTIONS = "least_connections"
    RESPONSE_TIME = "response_time"
    COST_OPTIMIZED = "cost_optimized"


class ProviderStats(BaseModel):
    """提供商统计信息"""
    name: str
    
    # 请求统计
    total_requests: int
    successful_requests: int
    failed_requests: int
    
    # 性能统计
    avg_response_time: float
    current_load: int  # 当前并发请求数
    
    # 可用性
    availability_score: float  # 0-1
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    
    # 成本效益
    avg_cost_per_request: float
    total_cost: float
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# === 配置管理 ===

class ServerConfig(BaseModel):
    """服务器配置"""
    
    # 基本配置
    host: str = "0.0.0.0"
    port: int = 8001
    workers: int = 1
    
    # 认证配置
    auth_enabled: bool = True
    auth_secret_key: str
    token_expire_hours: int = 24
    
    # 缓存配置
    cache_enabled: bool = True
    cache_backend: str = "memory"  # memory, redis
    cache_max_size: int = 1000
    cache_default_ttl: int = 3600
    
    # 监控配置
    metrics_enabled: bool = True
    metrics_retention_hours: int = 24
    
    # 负载均衡配置
    load_balance_strategy: LoadBalanceStrategy = LoadBalanceStrategy.RESPONSE_TIME
    health_check_interval: int = 30
    
    # 提供商配置
    providers: Dict[str, ProviderConfig] = {}
    
    # 限制配置
    max_concurrent_requests: int = 100
    request_timeout: int = 60
    
    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = None