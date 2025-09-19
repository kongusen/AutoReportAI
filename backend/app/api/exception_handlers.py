"""
统一异常处理器 - DDD架构v2.0

为整个应用提供统一的异常处理和错误响应格式
"""

import logging
from typing import Union, Dict, Any
from datetime import datetime

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError as FastAPIValidationError
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.base_api_controller import APIResponse
from app.services.application.base_application_service import OperationResult

logger = logging.getLogger("exception_handler")


class ApplicationException(Exception):
    """应用异常基类"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code or "APPLICATION_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class DomainException(ApplicationException):
    """领域异常"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message, error_code or "DOMAIN_ERROR", details)


class InfrastructureException(ApplicationException):
    """基础设施异常"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message, error_code or "INFRASTRUCTURE_ERROR", details)


async def application_exception_handler(request: Request, exc: ApplicationException) -> JSONResponse:
    """应用异常处理器"""
    logger.error(f"应用异常: {exc.message}", extra={
        "error_code": exc.error_code,
        "details": exc.details,
        "path": request.url.path,
        "method": request.method
    })
    
    response = APIResponse.error_response(
        message=exc.message,
        errors=[exc.message]
    )
    
    response.metadata = {
        "error_code": exc.error_code,
        "details": exc.details,
        "timestamp": datetime.now().isoformat()
    }
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=response.model_dump()
    )


async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
    """领域异常处理器"""
    logger.error(f"领域异常: {exc.message}", extra={
        "error_code": exc.error_code,
        "details": exc.details,
        "path": request.url.path,
        "method": request.method
    })
    
    response = APIResponse.error_response(
        message=f"业务规则违反: {exc.message}",
        errors=[exc.message]
    )
    
    response.metadata = {
        "error_code": exc.error_code,
        "error_type": "domain_error",
        "details": exc.details
    }
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response.model_dump()
    )


async def infrastructure_exception_handler(request: Request, exc: InfrastructureException) -> JSONResponse:
    """基础设施异常处理器"""
    logger.error(f"基础设施异常: {exc.message}", extra={
        "error_code": exc.error_code,
        "details": exc.details,
        "path": request.url.path,
        "method": request.method
    })
    
    response = APIResponse.error_response(
        message="系统服务暂时不可用，请稍后重试",
        errors=["服务异常"]
    )
    
    response.metadata = {
        "error_code": exc.error_code,
        "error_type": "infrastructure_error",
        "internal_message": exc.message  # 内部错误信息，不直接暴露给用户
    }
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response.model_dump()
    )


async def http_exception_handler(request: Request, exc: Union[HTTPException, StarletteHTTPException]) -> JSONResponse:
    """HTTP异常处理器"""
    logger.warning(f"HTTP异常: {exc.detail}", extra={
        "status_code": exc.status_code,
        "path": request.url.path,
        "method": request.method
    })
    
    # 处理结构化的错误详情
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message", "请求处理失败")
        errors = detail.get("errors", [])
        warnings = detail.get("warnings", [])
    else:
        message = str(detail)
        errors = [message]
        warnings = []
    
    response = APIResponse.error_response(
        message=message,
        errors=errors
    )
    response.warnings = warnings
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump()
    )


async def validation_exception_handler(request: Request, exc: Union[FastAPIValidationError, PydanticValidationError]) -> JSONResponse:
    """验证异常处理器"""
    logger.warning(f"验证异常: {exc}", extra={
        "path": request.url.path,
        "method": request.method
    })
    
    # 提取验证错误详情
    errors = []
    if hasattr(exc, 'errors'):
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error.get("loc", []))
            message = error.get("msg", "验证失败")
            errors.append(f"{field}: {message}")
    else:
        errors = [str(exc)]
    
    response = APIResponse.error_response(
        message="请求参数验证失败",
        errors=errors
    )
    
    response.metadata = {
        "error_type": "validation_error",
        "field_errors": errors
    }
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response.model_dump()
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """SQLAlchemy异常处理器"""
    logger.error(f"数据库异常: {exc}", extra={
        "path": request.url.path,
        "method": request.method
    }, exc_info=True)
    
    # 根据异常类型返回不同的错误信息
    if isinstance(exc, IntegrityError):
        message = "数据完整性约束违反，请检查输入数据"
        errors = ["数据约束冲突"]
    else:
        message = "数据库操作失败，请稍后重试"
        errors = ["数据库错误"]
    
    response = APIResponse.error_response(
        message=message,
        errors=errors
    )
    
    response.metadata = {
        "error_type": "database_error",
        "error_code": "DB_OPERATION_FAILED"
    }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response.model_dump()
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用异常处理器"""
    logger.error(f"未处理的异常: {exc}", extra={
        "exception_type": type(exc).__name__,
        "path": request.url.path,
        "method": request.method
    }, exc_info=True)
    
    # 在生产环境中不暴露内部错误详情
    response = APIResponse.error_response(
        message="服务器内部错误，请联系管理员",
        errors=["内部服务错误"]
    )
    
    response.metadata = {
        "error_type": "internal_error",
        "error_code": "INTERNAL_SERVER_ERROR",
        "exception_type": type(exc).__name__
    }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response.model_dump()
    )


def setup_exception_handlers(app):
    """设置异常处理器"""
    
    # 应用层异常
    app.add_exception_handler(ApplicationException, application_exception_handler)
    app.add_exception_handler(DomainException, domain_exception_handler)
    app.add_exception_handler(InfrastructureException, infrastructure_exception_handler)
    
    # HTTP相关异常
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # 验证异常
    app.add_exception_handler(FastAPIValidationError, validation_exception_handler)
    app.add_exception_handler(PydanticValidationError, validation_exception_handler)
    
    # 数据库异常
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    
    # 通用异常（最后的捕获网）
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("✅ 异常处理器设置完成")


# 异常工厂函数
def create_domain_exception(message: str, error_code: str = None, **details) -> DomainException:
    """创建领域异常"""
    return DomainException(message, error_code, details)


def create_infrastructure_exception(message: str, error_code: str = None, **details) -> InfrastructureException:
    """创建基础设施异常"""
    return InfrastructureException(message, error_code, details)


def create_validation_exception(message: str, field_errors: list = None) -> ApplicationException:
    """创建验证异常"""
    return ApplicationException(
        message=message,
        error_code="VALIDATION_ERROR",
        details={"field_errors": field_errors or []}
    )


logger.info("✅ 统一异常处理组件加载完成")