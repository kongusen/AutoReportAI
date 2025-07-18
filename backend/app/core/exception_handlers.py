"""
全局异常处理中间件

提供统一的异常处理机制，将应用异常转换为标准的HTTP响应。
"""

import logging
import traceback
from typing import Union

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from app.core.exceptions import AppException, DatabaseError, ValidationError as AppValidationError

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """处理应用程序自定义异常"""
    logger.warning(
        f"Application exception occurred: {exc.code} - {exc.message}",
        extra={
            "exception_code": exc.code,
            "exception_message": exc.message,
            "exception_details": exc.details,
            "request_url": str(request.url),
            "request_method": request.method,
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.message,
            "code": exc.code,
            "details": exc.details,
            "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """处理HTTP异常"""
    logger.warning(
        f"HTTP exception occurred: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "request_url": str(request.url),
            "request_method": request.method,
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "code": f"HTTP_{exc.status_code}",
            "details": {},
            "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """处理请求验证异常"""
    logger.warning(
        f"Validation exception occurred: {exc.errors()}",
        extra={
            "validation_errors": exc.errors(),
            "request_url": str(request.url),
            "request_method": request.method,
        }
    )
    
    # 格式化验证错误信息
    formatted_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        formatted_errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": "请求数据验证失败",
            "code": "VALIDATION_ERROR",
            "details": {
                "validation_errors": formatted_errors
            },
            "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
        }
    )


async def pydantic_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """处理Pydantic验证异常"""
    logger.warning(
        f"Pydantic validation exception occurred: {exc.errors()}",
        extra={
            "validation_errors": exc.errors(),
            "request_url": str(request.url),
            "request_method": request.method,
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": "数据验证失败",
            "code": "PYDANTIC_VALIDATION_ERROR",
            "details": {
                "validation_errors": exc.errors()
            },
            "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
        }
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """处理SQLAlchemy数据库异常"""
    logger.error(
        f"Database exception occurred: {str(exc)}",
        extra={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "request_url": str(request.url),
            "request_method": request.method,
        }
    )
    
    # 将SQLAlchemy异常转换为应用异常
    db_error = DatabaseError(
        message="数据库操作失败",
        operation=request.method,
        details={
            "exception_type": type(exc).__name__,
            "original_message": str(exc)
        }
    )
    
    return JSONResponse(
        status_code=db_error.status_code,
        content={
            "error": True,
            "message": db_error.message,
            "code": db_error.code,
            "details": db_error.details,
            "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未捕获的通用异常"""
    logger.error(
        f"Unhandled exception occurred: {str(exc)}",
        extra={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": traceback.format_exc(),
            "request_url": str(request.url),
            "request_method": request.method,
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "服务器内部错误",
            "code": "INTERNAL_SERVER_ERROR",
            "details": {
                "exception_type": type(exc).__name__,
                # 在生产环境中可能不想暴露详细的错误信息
                "debug_message": str(exc) if logger.level <= logging.DEBUG else None
            },
            "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
        }
    )


def setup_exception_handlers(app):
    """设置异常处理器"""
    # 应用程序自定义异常
    app.add_exception_handler(AppException, app_exception_handler)
    
    # HTTP异常
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # 验证异常
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)
    
    # 数据库异常
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    
    # 通用异常（必须放在最后）
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Exception handlers have been set up")