"""
统一异常处理系统

定义应用程序中使用的所有业务异常类型，提供统一的错误处理机制。
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class AppException(Exception):
    """应用程序基础异常类"""
    
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppException):
    """数据验证异常"""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details or {}
        )
        if field:
            self.details["field"] = field


class AuthenticationError(AppException):
    """认证异常"""
    
    def __init__(self, message: str = "认证失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class AuthorizationError(AppException):
    """授权异常"""
    
    def __init__(self, message: str = "权限不足", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class NotFoundError(AppException):
    """资源未找到异常"""
    
    def __init__(self, resource: str, identifier: Any = None, details: Optional[Dict[str, Any]] = None):
        message = f"{resource}未找到"
        if identifier:
            message += f": {identifier}"
        
        super().__init__(
            message=message,
            code="NOT_FOUND_ERROR",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details or {}
        )
        self.details["resource"] = resource
        if identifier:
            self.details["identifier"] = str(identifier)


class ConflictError(AppException):
    """资源冲突异常"""
    
    def __init__(self, message: str, resource: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CONFLICT_ERROR",
            status_code=status.HTTP_409_CONFLICT,
            details=details or {}
        )
        if resource:
            self.details["resource"] = resource


class DatabaseError(AppException):
    """数据库操作异常"""
    
    def __init__(self, message: str = "数据库操作失败", operation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {}
        )
        if operation:
            self.details["operation"] = operation


class ExternalServiceError(AppException):
    """外部服务异常"""
    
    def __init__(self, service: str, message: str = "外部服务调用失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"{service}: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details or {}
        )
        self.details["service"] = service


class ServiceException(AppException):
    """通用服务异常"""
    
    def __init__(self, message: str, service_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="SERVICE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {}
        )
        if service_name:
            self.details["service_name"] = service_name


# 智能占位符服务异常
class PlaceholderProcessingError(AppException):
    """占位符处理异常"""
    
    def __init__(self, message: str, placeholder_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="PLACEHOLDER_PROCESSING_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details or {}
        )
        if placeholder_type:
            self.details["placeholder_type"] = placeholder_type


class FieldMatchingError(AppException):
    """字段匹配异常"""
    
    def __init__(self, message: str, field_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="FIELD_MATCHING_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details or {}
        )
        if field_name:
            self.details["field_name"] = field_name


class PlaceholderAdapterError(AppException):
    """占位符适配器异常"""
    
    def __init__(self, message: str, adapter_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="PLACEHOLDER_ADAPTER_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {}
        )
        if adapter_type:
            self.details["adapter_type"] = adapter_type


# 报告生成服务异常
class ReportGenerationError(AppException):
    """报告生成异常"""
    
    def __init__(self, message: str, template_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="REPORT_GENERATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {}
        )
        if template_id:
            self.details["template_id"] = template_id


class ReportCompositionError(AppException):
    """报告组合异常"""
    
    def __init__(self, message: str, composition_step: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="REPORT_COMPOSITION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {}
        )
        if composition_step:
            self.details["composition_step"] = composition_step


class ReportQualityError(AppException):
    """报告质量检查异常"""
    
    def __init__(self, message: str, quality_issue: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="REPORT_QUALITY_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details or {}
        )
        if quality_issue:
            self.details["quality_issue"] = quality_issue


# 数据处理服务异常
class DataRetrievalError(AppException):
    """数据检索异常"""
    
    def __init__(self, message: str, data_source: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="DATA_RETRIEVAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {}
        )
        if data_source:
            self.details["data_source"] = data_source


class DataAnalysisError(AppException):
    """数据分析异常"""
    
    def __init__(self, message: str, analysis_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="DATA_ANALYSIS_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {}
        )
        if analysis_type:
            self.details["analysis_type"] = analysis_type


class ETLProcessingError(AppException):
    """ETL处理异常"""
    
    def __init__(self, message: str, etl_stage: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="ETL_PROCESSING_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {}
        )
        if etl_stage:
            self.details["etl_stage"] = etl_stage


# AI集成服务异常
class LLMServiceError(AppException):
    """LLM服务异常"""
    
    def __init__(self, message: str, provider: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="LLM_SERVICE_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details or {}
        )
        if provider:
            self.details["provider"] = provider


class ContentGenerationError(AppException):
    """内容生成异常"""
    
    def __init__(self, message: str, content_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CONTENT_GENERATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {}
        )
        if content_type:
            self.details["content_type"] = content_type


class ChartGenerationError(AppException):
    """图表生成异常"""
    
    def __init__(self, message: str, chart_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CHART_GENERATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {}
        )
        if chart_type:
            self.details["chart_type"] = chart_type


# 通知服务异常
class NotificationError(AppException):
    """通知服务异常"""
    
    def __init__(self, message: str, notification_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="NOTIFICATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {}
        )
        if notification_type:
            self.details["notification_type"] = notification_type


class EmailServiceError(AppException):
    """邮件服务异常"""
    
    def __init__(self, message: str, recipient: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="EMAIL_SERVICE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {}
        )
        if recipient:
            self.details["recipient"] = recipient


class WebSocketError(AppException):
    """WebSocket异常"""
    
    def __init__(self, message: str, connection_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="WEBSOCKET_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {}
        )
        if connection_id:
            self.details["connection_id"] = connection_id


# 工具函数
def create_http_exception(app_exception: AppException) -> HTTPException:
    """将应用异常转换为HTTP异常"""
    return HTTPException(
        status_code=app_exception.status_code,
        detail={
            "message": app_exception.message,
            "code": app_exception.code,
            "details": app_exception.details
        }
    )