"""
现代FastAPI架构核心组件
定义了整个系统的架构模式和最佳实践
"""

from enum import Enum
from typing import Dict, Any, Optional, List, Generic, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

# 定义泛型类型变量
T = TypeVar('T')


class ArchitectureLayer(str, Enum):
    """架构分层枚举"""
    API = "api"
    SERVICE = "service"
    REPOSITORY = "repository"
    DOMAIN = "domain"
    INFRASTRUCTURE = "infrastructure"


class ApiVersion(str, Enum):
    """API版本管理"""
    V1 = "v1"
    V2 = "v2"


class PermissionLevel(str, Enum):
    """权限级别"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    OWNER = "owner"


class ResourceType(str, Enum):
    """资源类型"""
    USER = "user"
    TEMPLATE = "template"
    DATASOURCE = "datasource"
    REPORT = "report"
    TASK = "task"
    ETLJOB = "etljob"


class UserRole(str, Enum):
    """用户角色"""
    SUPERUSER = "superuser"
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class ApiResponse(BaseModel, Generic[T]):
    """统一的API响应格式"""
    success: bool = Field(..., description="请求是否成功")
    data: Optional[T] = Field(None, description="响应数据")
    message: Optional[str] = Field(None, description="响应消息")
    error: Optional[str] = Field(None, description="错误信息")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version: str = Field(default="v1")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应格式"""
    items: List[T] = Field(..., description="数据列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")


class ErrorResponse(BaseModel):
    """错误响应格式"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    detail: Optional[str] = Field(None, description="详细错误信息")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    path: Optional[str] = Field(None, description="请求路径")
    method: Optional[str] = Field(None, description="请求方法")
    
    @classmethod
    def create(cls, error: str, message: str, detail=None, path: str = None, method: str = None):
        """创建错误响应，自动处理detail类型转换"""
        if detail is not None and not isinstance(detail, str):
            # 将非字符串detail转换为JSON字符串
            import json
            detail = json.dumps(detail, ensure_ascii=False, default=str)
        
        return cls(
            error=error,
            message=message,
            detail=detail,
            path=path,
            method=method
        )


class HealthStatus(BaseModel):
    """系统健康状态"""
    status: str = Field(..., description="系统状态")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    version: str = Field(..., description="系统版本")
    uptime: float = Field(..., description="运行时间(秒)")
    services: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="服务状态")


class AuditLog(BaseModel):
    """审计日志"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = Field(None, description="用户ID")
    action: str = Field(..., description="操作类型")
    resource_type: ResourceType = Field(..., description="资源类型")
    resource_id: Optional[str] = Field(None, description="资源ID")
    details: Dict[str, Any] = Field(default_factory=dict, description="操作详情")
    ip_address: Optional[str] = Field(None, description="IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    success: bool = Field(..., description="操作是否成功")
    error_message: Optional[str] = Field(None, description="错误消息")


class RateLimitConfig(BaseModel):
    """限流配置"""
    requests_per_minute: int = Field(default=60, description="每分钟请求数")
    requests_per_hour: int = Field(default=1000, description="每小时请求数")
    burst_limit: int = Field(default=10, description="突发请求限制")
    window_size: int = Field(default=60, description="时间窗口(秒)")


class CacheConfig(BaseModel):
    """缓存配置"""
    ttl: int = Field(default=3600, description="缓存过期时间(秒)")
    max_size: int = Field(default=1000, description="最大缓存大小")
    strategy: str = Field(default="lru", description="缓存策略")
    enabled: bool = Field(default=True, description="是否启用缓存")


class SecurityConfig(BaseModel):
    """安全配置"""
    jwt_secret: str = Field(..., description="JWT密钥")
    jwt_algorithm: str = Field(default="HS256", description="JWT算法")
    access_token_expire_minutes: int = Field(default=30, description="访问令牌过期时间")
    refresh_token_expire_days: int = Field(default=7, description="刷新令牌过期时间")
    password_min_length: int = Field(default=8, description="密码最小长度")
    max_login_attempts: int = Field(default=5, description="最大登录尝试次数")
    lockout_duration: int = Field(default=900, description="锁定持续时间(秒)")


class DatabaseConfig(BaseModel):
    """数据库配置"""
    url: str = Field(..., description="数据库连接URL")
    pool_size: int = Field(default=10, description="连接池大小")
    max_overflow: int = Field(default=20, description="最大溢出连接数")
    pool_timeout: int = Field(default=30, description="连接超时时间")
    pool_recycle: int = Field(default=3600, description="连接回收时间")
    echo: bool = Field(default=False, description="是否打印SQL日志")


class SystemConfig(BaseModel):
    """系统配置"""
    project_name: str = Field(default="AutoReportAI", description="项目名称")
    debug: bool = Field(default=False, description="调试模式")
    cors_origins: List[str] = Field(default_factory=list, description="CORS源")
    api_version: str = Field(default="v1", description="API版本")
    docs_url: str = Field(default="/docs", description="文档URL")
    redoc_url: str = Field(default="/redoc", description="ReDoc URL")
    openapi_url: str = Field(default="/openapi.json", description="OpenAPI URL")
