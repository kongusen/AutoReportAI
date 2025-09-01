"""
统一API规范定义
定义前后端通信的标准格式、类型和约定
"""

from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

T = TypeVar('T')

# ============================================================================
# API版本和元数据
# ============================================================================

class APIVersion(str, Enum):
    """API版本枚举"""
    V1 = "v1"
    V2 = "v2"


class APIStatus(str, Enum):
    """API状态枚举"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# ============================================================================
# 统一响应格式
# ============================================================================

class APIResponse(BaseModel, Generic[T]):
    """统一API响应格式"""
    success: bool = Field(..., description="请求是否成功")
    status: APIStatus = Field(default=APIStatus.SUCCESS, description="响应状态")
    data: Optional[T] = Field(None, description="响应数据")
    message: Optional[str] = Field(None, description="响应消息")
    error: Optional[str] = Field(None, description="错误信息")
    
    # 元数据
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="响应时间戳")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="请求追踪ID")
    version: str = Field(default="v1", description="API版本")
    
    # 性能指标
    execution_time_ms: Optional[float] = Field(None, description="执行时间（毫秒）")
    cached: Optional[bool] = Field(False, description="是否来自缓存")


class PaginatedAPIResponse(BaseModel, Generic[T]):
    """分页API响应格式"""
    success: bool = Field(True, description="请求是否成功")
    data: List[T] = Field(..., description="数据列表")
    
    # 分页元数据
    pagination: Dict[str, Any] = Field(..., description="分页信息")
    
    # 标准元数据
    message: Optional[str] = Field(None, description="响应消息")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version: str = Field(default="v1")
    execution_time_ms: Optional[float] = Field(None, description="执行时间（毫秒）")
    cached: Optional[bool] = Field(False, description="是否来自缓存")

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        size: int,
        message: Optional[str] = None,
        **metadata
    ) -> "PaginatedAPIResponse[T]":
        """创建分页响应"""
        has_next = page * size < total
        has_prev = page > 1
        total_pages = (total + size - 1) // size if size > 0 else 0
        
        pagination = {
            "total": total,
            "page": page,
            "size": size,
            "pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev,
            "total_pages": total_pages
        }
        
        return cls(
            data=items,
            pagination=pagination,
            message=message,
            **metadata
        )


class ErrorAPIResponse(BaseModel):
    """错误API响应格式"""
    success: bool = Field(False, description="请求失败")
    status: APIStatus = Field(APIStatus.ERROR, description="错误状态")
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    detail: Optional[Dict[str, Any]] = Field(None, description="详细错误信息")
    
    # 调试信息
    path: Optional[str] = Field(None, description="请求路径")
    method: Optional[str] = Field(None, description="请求方法")
    
    # 元数据
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version: str = Field(default="v1")


# ============================================================================
# WebSocket消息格式
# ============================================================================

class WebSocketMessageType(str, Enum):
    """WebSocket消息类型"""
    # 连接管理
    AUTH = "auth"
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PING = "ping"
    PONG = "pong"
    
    # 通知消息
    NOTIFICATION = "notification"
    SYSTEM_ALERT = "system_alert"
    
    # 业务消息
    TASK_UPDATE = "task_update"
    REPORT_UPDATE = "report_update"
    DATA_SYNC = "data_sync"
    
    # 实时状态
    USER_STATUS = "user_status"
    SYSTEM_STATUS = "system_status"
    
    # 错误消息
    ERROR = "error"
    WARNING = "warning"


class WebSocketMessage(BaseModel):
    """WebSocket消息基类"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="消息ID")
    type: WebSocketMessageType = Field(..., description="消息类型")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="消息时间戳")
    user_id: Optional[str] = Field(None, description="目标用户ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    
    # 消息内容
    data: Dict[str, Any] = Field(default_factory=dict, description="消息数据")
    message: Optional[str] = Field(None, description="消息内容")
    
    # 元数据
    priority: int = Field(default=1, description="消息优先级 1-5")
    expires_at: Optional[datetime] = Field(None, description="消息过期时间")
    retry_count: int = Field(default=0, description="重试次数")


class NotificationMessage(WebSocketMessage):
    """通知消息"""
    type: WebSocketMessageType = Field(WebSocketMessageType.NOTIFICATION, const=True)
    title: str = Field(..., description="通知标题")
    message: str = Field(..., description="通知内容")
    category: Optional[str] = Field(None, description="通知分类")
    action_url: Optional[str] = Field(None, description="操作链接")
    
    # 通知样式
    notification_type: str = Field(default="info", description="通知类型: info/success/warning/error")
    auto_dismiss: bool = Field(True, description="是否自动消失")
    dismiss_timeout: int = Field(5000, description="消失延时（毫秒）")


class TaskUpdateMessage(WebSocketMessage):
    """任务更新消息"""
    type: WebSocketMessageType = Field(WebSocketMessageType.TASK_UPDATE, const=True)
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    progress: Optional[float] = Field(None, description="任务进度 0-100")
    stage: Optional[str] = Field(None, description="当前阶段")
    estimated_remaining: Optional[int] = Field(None, description="预计剩余时间（秒）")


class ReportUpdateMessage(WebSocketMessage):
    """报告更新消息"""
    type: WebSocketMessageType = Field(WebSocketMessageType.REPORT_UPDATE, const=True)
    report_id: str = Field(..., description="报告ID")
    status: str = Field(..., description="报告状态")
    file_url: Optional[str] = Field(None, description="报告文件URL")
    preview_url: Optional[str] = Field(None, description="预览URL")


# ============================================================================
# API请求格式
# ============================================================================

class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1, description="页码，从1开始")
    size: int = Field(default=20, ge=1, le=100, description="每页大小，最大100")
    
    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.size


class SortParams(BaseModel):
    """排序参数"""
    sort_by: Optional[str] = Field(None, description="排序字段")
    sort_order: str = Field(default="desc", regex="^(asc|desc)$", description="排序顺序")


class FilterParams(BaseModel):
    """筛选参数基类"""
    search: Optional[str] = Field(None, description="搜索关键词")
    created_after: Optional[datetime] = Field(None, description="创建时间起始")
    created_before: Optional[datetime] = Field(None, description="创建时间结束")
    is_active: Optional[bool] = Field(None, description="是否激活")


class APIRequestParams(BaseModel):
    """API请求参数基类"""
    pagination: PaginationParams = Field(default_factory=PaginationParams)
    sorting: SortParams = Field(default_factory=SortParams)
    filters: FilterParams = Field(default_factory=FilterParams)


# ============================================================================
# 资源标识符
# ============================================================================

class ResourceType(str, Enum):
    """资源类型"""
    USER = "user"
    TASK = "task"
    REPORT = "report"
    TEMPLATE = "template"
    DATA_SOURCE = "data_source"
    ETL_JOB = "etl_job"
    LLM_SERVER = "llm_server"
    FILE = "file"


class ResourceReference(BaseModel):
    """资源引用"""
    id: str = Field(..., description="资源ID")
    type: ResourceType = Field(..., description="资源类型")
    name: Optional[str] = Field(None, description="资源名称")
    url: Optional[str] = Field(None, description="资源URL")


# ============================================================================
# 批量操作
# ============================================================================

class BatchOperation(BaseModel):
    """批量操作"""
    action: str = Field(..., description="操作类型")
    resource_ids: List[str] = Field(..., description="资源ID列表")
    params: Optional[Dict[str, Any]] = Field(None, description="操作参数")


class BatchOperationResult(BaseModel):
    """批量操作结果"""
    total: int = Field(..., description="总数")
    success_count: int = Field(..., description="成功数量")
    failed_count: int = Field(..., description="失败数量")
    success_ids: List[str] = Field(default_factory=list, description="成功的ID列表")
    failed_items: List[Dict[str, Any]] = Field(default_factory=list, description="失败的项目详情")


# ============================================================================
# 系统状态和监控
# ============================================================================

class SystemHealth(BaseModel):
    """系统健康状态"""
    status: str = Field(..., description="系统状态: healthy/degraded/unhealthy")
    uptime_seconds: int = Field(..., description="运行时间（秒）")
    version: str = Field(..., description="系统版本")
    
    # 组件状态
    components: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="组件状态")
    
    # 性能指标
    metrics: Dict[str, float] = Field(default_factory=dict, description="性能指标")
    
    # 时间戳
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# 帮助函数
# ============================================================================

def create_success_response(
    data: Any = None,
    message: Optional[str] = None,
    **metadata
) -> APIResponse:
    """创建成功响应"""
    return APIResponse(
        success=True,
        status=APIStatus.SUCCESS,
        data=data,
        message=message,
        **metadata
    )


def create_error_response(
    error: str,
    message: str,
    detail: Optional[Dict[str, Any]] = None,
    **metadata
) -> ErrorAPIResponse:
    """创建错误响应"""
    return ErrorAPIResponse(
        error=error,
        message=message,
        detail=detail,
        **metadata
    )


def create_pagination_response(
    items: List[Any],
    total: int,
    page: int,
    size: int,
    message: Optional[str] = None,
    **metadata
) -> PaginatedAPIResponse:
    """创建分页响应"""
    return PaginatedAPIResponse.create(
        items=items,
        total=total,
        page=page,
        size=size,
        message=message,
        **metadata
    )