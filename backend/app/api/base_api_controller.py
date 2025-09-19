"""
Base API Controller - 统一API架构基类

为所有API端点提供统一的响应格式、错误处理和请求验证
"""

import logging
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic
from datetime import datetime
from abc import ABC

from fastapi import HTTPException, status
from pydantic import BaseModel

from app.services.application.base_application_service import ApplicationResult, OperationResult

logger = logging.getLogger(__name__)

T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """统一API响应格式"""
    success: bool
    data: Optional[T] = None
    message: str = ""
    errors: List[str] = []
    warnings: List[str] = []
    metadata: Dict[str, Any] = {}
    timestamp: str = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
        super().__init__(**data)
    
    @classmethod
    def success_response(cls, data: T = None, message: str = "操作成功") -> 'APIResponse[T]':
        """创建成功响应"""
        return cls(
            success=True,
            data=data,
            message=message
        )
    
    @classmethod
    def error_response(cls, message: str = "操作失败", errors: List[str] = None) -> 'APIResponse[None]':
        """创建错误响应"""
        return cls(
            success=False,
            message=message,
            errors=errors or []
        )
    
    @classmethod
    def from_application_result(cls, app_result: ApplicationResult[T]) -> 'APIResponse[T]':
        """从应用服务结果创建API响应"""
        return cls(
            success=app_result.success,
            data=app_result.data,
            message=app_result.message,
            errors=app_result.errors or [],
            warnings=app_result.warnings or [],
            metadata=app_result.metadata or {}
        )


class PaginatedAPIResponse(BaseModel, Generic[T]):
    """分页API响应格式"""
    success: bool
    data: List[T] = []
    pagination: Dict[str, Any] = {}
    message: str = ""
    errors: List[str] = []
    timestamp: str = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
        super().__init__(**data)
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, size: int, 
               message: str = "获取数据成功") -> 'PaginatedAPIResponse[T]':
        """创建分页响应"""
        pages = (total + size - 1) // size
        return cls(
            success=True,
            data=items,
            pagination={
                "total": total,
                "page": page,
                "size": size,
                "pages": pages,
                "has_next": page < pages,
                "has_prev": page > 1
            },
            message=message
        )


class BaseAPIController(ABC):
    """基础API控制器
    
    所有API端点控制器都应该继承此类，确保统一的错误处理和响应格式
    """
    
    def __init__(self, controller_name: str = None):
        self.controller_name = controller_name or self.__class__.__name__
        self.logger = logging.getLogger(f"api.{self.controller_name}")
    
    def handle_application_result(self, app_result: ApplicationResult[T]) -> APIResponse[T]:
        """处理应用服务结果"""
        api_response = APIResponse.from_application_result(app_result)
        
        # 根据应用服务结果类型决定HTTP状态码
        if not app_result.success:
            self._raise_http_exception_from_result(app_result)
        
        return api_response
    
    def handle_paginated_result(self, items: List[T], total: int, page: int, 
                              size: int, message: str = "获取数据成功") -> PaginatedAPIResponse[T]:
        """处理分页结果"""
        return PaginatedAPIResponse.create(items, total, page, size, message)
    
    def _raise_http_exception_from_result(self, app_result: ApplicationResult):
        """根据应用服务结果抛出相应的HTTP异常"""
        status_code_map = {
            OperationResult.VALIDATION_ERROR: status.HTTP_400_BAD_REQUEST,
            OperationResult.NOT_FOUND: status.HTTP_404_NOT_FOUND,
            OperationResult.PERMISSION_DENIED: status.HTTP_403_FORBIDDEN,
            OperationResult.FAILURE: status.HTTP_500_INTERNAL_SERVER_ERROR
        }
        
        status_code = status_code_map.get(app_result.result, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        raise HTTPException(
            status_code=status_code,
            detail={
                "message": app_result.message,
                "errors": app_result.errors,
                "warnings": app_result.warnings
            }
        )
    
    def validate_pagination_params(self, page: int = 1, size: int = 20, 
                                 max_size: int = 100) -> Dict[str, int]:
        """验证分页参数"""
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="页码必须大于0"
            )
        
        if size < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="页面大小必须大于0"
            )
        
        if size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"页面大小不能超过 {max_size}"
            )
        
        skip = (page - 1) * size
        return {"page": page, "size": size, "skip": skip}
    
    def validate_required_fields(self, **fields) -> None:
        """验证必需字段"""
        missing_fields = []
        for field_name, field_value in fields.items():
            if field_value is None or field_value == "":
                missing_fields.append(field_name)
        
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"缺少必需字段: {', '.join(missing_fields)}"
            )
    
    def log_api_request(self, endpoint: str, user_id: str = None, **params):
        """记录API请求"""
        extra = {"user_id": user_id, "endpoint": endpoint}
        extra.update(params)
        self.logger.info(f"API请求: {endpoint}", extra=extra)
    
    def log_api_response(self, endpoint: str, success: bool, duration_ms: float = None, **params):
        """记录API响应"""
        extra = {"endpoint": endpoint, "success": success}
        if duration_ms:
            extra["duration_ms"] = duration_ms
        extra.update(params)
        
        if success:
            self.logger.info(f"API成功: {endpoint}", extra=extra)
        else:
            self.logger.warning(f"API失败: {endpoint}", extra=extra)


class CRUDAPIController(BaseAPIController):
    """CRUD API控制器基类
    
    为标准CRUD操作提供通用的处理模式
    """
    
    def __init__(self, resource_name: str, controller_name: str = None):
        super().__init__(controller_name)
        self.resource_name = resource_name
    
    def handle_create_operation(self, app_result: ApplicationResult[T]) -> APIResponse[T]:
        """处理创建操作"""
        if app_result.success:
            self.logger.info(f"{self.resource_name}创建成功")
        else:
            self.logger.error(f"{self.resource_name}创建失败: {app_result.message}")
        
        return self.handle_application_result(app_result)
    
    def handle_update_operation(self, resource_id: str, app_result: ApplicationResult[T]) -> APIResponse[T]:
        """处理更新操作"""
        if app_result.success:
            self.logger.info(f"{self.resource_name} {resource_id} 更新成功")
        else:
            self.logger.error(f"{self.resource_name} {resource_id} 更新失败: {app_result.message}")
        
        return self.handle_application_result(app_result)
    
    def handle_delete_operation(self, resource_id: str, app_result: ApplicationResult[bool]) -> APIResponse[bool]:
        """处理删除操作"""
        if app_result.success:
            self.logger.info(f"{self.resource_name} {resource_id} 删除成功")
        else:
            self.logger.error(f"{self.resource_name} {resource_id} 删除失败: {app_result.message}")
        
        return self.handle_application_result(app_result)
    
    def handle_get_operation(self, resource_id: str, app_result: ApplicationResult[T]) -> APIResponse[T]:
        """处理获取单个资源操作"""
        if app_result.success:
            self.logger.debug(f"{self.resource_name} {resource_id} 获取成功")
        else:
            self.logger.warning(f"{self.resource_name} {resource_id} 获取失败: {app_result.message}")
        
        return self.handle_application_result(app_result)
    
    def handle_list_operation(self, app_result: ApplicationResult[List[T]], 
                            pagination_params: Dict[str, int]) -> PaginatedAPIResponse[T]:
        """处理列表操作"""
        if app_result.success and hasattr(app_result.data, '__len__'):
            total = len(app_result.data)  # 这里可以根据实际情况调整
            return self.handle_paginated_result(
                items=app_result.data,
                total=total,
                page=pagination_params["page"],
                size=pagination_params["size"]
            )
        else:
            # 如果获取失败，转换为标准错误处理
            api_response = self.handle_application_result(app_result)
            # 这里不会执行到，因为handle_application_result会抛出异常
            return PaginatedAPIResponse(success=False, errors=[app_result.message])


# 全局异常处理函数
def create_error_response(exception: Exception) -> APIResponse[None]:
    """创建异常响应"""
    if isinstance(exception, HTTPException):
        return APIResponse.error_response(
            message=str(exception.detail),
            errors=[str(exception.detail)]
        )
    else:
        logger.error(f"未处理的异常: {exception}", exc_info=True)
        return APIResponse.error_response(
            message="服务器内部错误",
            errors=[str(exception)]
        )


logger.info("✅ Base API Controller架构组件加载完成")