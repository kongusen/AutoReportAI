"""
统一错误处理中间件
为所有API端点提供用户友好的错误响应格式
"""

import logging
import traceback
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.schemas.base import APIResponse
from app.schemas.frontend_adapters import (
    adapt_error_for_frontend, ErrorDisplayInfo
)

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """统一错误处理中间件"""

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            response = await call_next(request)
            return response

        except HTTPException as http_exc:
            # HTTP异常使用前端错误适配器
            error_info = self._create_error_display_info(
                http_exc.detail,
                "http_error",
                f"HTTP_{http_exc.status_code}",
                {"status_code": http_exc.status_code, "url": str(request.url)}
            )

            logger.warning(f"HTTP Exception: {http_exc.status_code} - {http_exc.detail}")

            return JSONResponse(
                status_code=http_exc.status_code,
                content=APIResponse(
                    success=False,
                    data=error_info.dict(),
                    message=error_info.user_friendly_message
                ).dict()
            )

        except Exception as exc:
            # 系统异常处理
            error_code = self._classify_exception(exc)
            error_info = self._create_error_display_info(
                str(exc),
                "system",
                error_code,
                {
                    "exception_type": type(exc).__name__,
                    "url": str(request.url),
                    "method": request.method
                }
            )

            logger.error(f"Unhandled exception: {exc}\n{traceback.format_exc()}")

            return JSONResponse(
                status_code=500,
                content=APIResponse(
                    success=False,
                    data=error_info.dict(),
                    message=error_info.user_friendly_message
                ).dict()
            )

    def _create_error_display_info(
        self,
        error_message: str,
        error_type: str,
        error_code: str,
        details: Optional[Dict[str, Any]] = None
    ) -> ErrorDisplayInfo:
        """创建错误显示信息"""
        return adapt_error_for_frontend(
            error_message=error_message,
            error_type=error_type,
            error_code=error_code,
            details=details
        )

    def _classify_exception(self, exc: Exception) -> str:
        """根据异常类型分类错误代码"""
        exception_map = {
            "ConnectionError": "database_connection_error",
            "TimeoutError": "request_timeout",
            "PermissionError": "permission_denied",
            "FileNotFoundError": "resource_not_found",
            "ValueError": "validation_error",
            "KeyError": "missing_parameter",
            "AttributeError": "configuration_error",
            "ImportError": "dependency_error",
            "SQLAlchemyError": "database_error",
            "ValidationError": "validation_error"
        }

        exception_name = type(exc).__name__
        return exception_map.get(exception_name, "unknown_system_error")


class APIErrorHandler:
    """API错误处理工具类"""

    @staticmethod
    def handle_database_error(error: Exception, context: str = "") -> JSONResponse:
        """处理数据库错误"""
        error_info = adapt_error_for_frontend(
            error_message=str(error),
            error_type="database",
            error_code="database_operation_failed",
            details={"context": context, "error_type": type(error).__name__}
        )

        logger.error(f"Database error in {context}: {error}")

        return JSONResponse(
            status_code=500,
            content=APIResponse(
                success=False,
                data=error_info.dict(),
                message=error_info.user_friendly_message
            ).dict()
        )

    @staticmethod
    def handle_validation_error(error: Exception, field_name: str = "") -> JSONResponse:
        """处理验证错误"""
        error_info = adapt_error_for_frontend(
            error_message=str(error),
            error_type="validation",
            error_code="validation_failed",
            details={"field_name": field_name, "error_type": type(error).__name__}
        )

        logger.warning(f"Validation error for field {field_name}: {error}")

        return JSONResponse(
            status_code=400,
            content=APIResponse(
                success=False,
                data=error_info.dict(),
                message=error_info.user_friendly_message
            ).dict()
        )

    @staticmethod
    def handle_permission_error(user_id: str, resource: str, action: str) -> JSONResponse:
        """处理权限错误"""
        error_info = adapt_error_for_frontend(
            error_message=f"用户 {user_id} 无权限执行 {action} 操作",
            error_type="permission",
            error_code="permission_denied",
            details={
                "user_id": user_id,
                "resource": resource,
                "action": action
            }
        )

        logger.warning(f"Permission denied: user {user_id} tried to {action} on {resource}")

        return JSONResponse(
            status_code=403,
            content=APIResponse(
                success=False,
                data=error_info.dict(),
                message=error_info.user_friendly_message
            ).dict()
        )

    @staticmethod
    def handle_rate_limit_error(user_id: str, limit_type: str) -> JSONResponse:
        """处理频率限制错误"""
        error_info = adapt_error_for_frontend(
            error_message="请求过于频繁，请稍后重试",
            error_type="rate_limit",
            error_code="rate_limit_exceeded",
            details={
                "user_id": user_id,
                "limit_type": limit_type,
                "retry_after": 60
            }
        )

        logger.warning(f"Rate limit exceeded for user {user_id}: {limit_type}")

        return JSONResponse(
            status_code=429,
            content=APIResponse(
                success=False,
                data=error_info.dict(),
                message=error_info.user_friendly_message
            ).dict()
        )

    @staticmethod
    def handle_agent_error(error: Exception, agent_context: Dict[str, Any] = None) -> JSONResponse:
        """处理Agent相关错误"""
        error_info = adapt_error_for_frontend(
            error_message=str(error),
            error_type="agent_service",
            error_code="agent_service_unavailable",
            details={
                "agent_context": agent_context or {},
                "error_type": type(error).__name__
            }
        )

        logger.error(f"Agent error: {error}")

        return JSONResponse(
            status_code=503,
            content=APIResponse(
                success=False,
                data=error_info.dict(),
                message=error_info.user_friendly_message
            ).dict()
        )


def create_error_response(
    error_message: str,
    error_type: str = "system",
    error_code: str = "unknown_error",
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """创建标准化错误响应"""
    error_info = adapt_error_for_frontend(
        error_message=error_message,
        error_type=error_type,
        error_code=error_code,
        details=details
    )

    return JSONResponse(
        status_code=status_code,
        content=APIResponse(
            success=False,
            data=error_info.dict(),
            message=error_info.user_friendly_message
        ).dict()
    )