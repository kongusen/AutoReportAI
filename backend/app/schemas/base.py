"""
基础响应模式

定义统一的API响应格式和基础模式。
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field

DataType = TypeVar('DataType')


class APIResponse(BaseModel, Generic[DataType]):
    """统一的API响应格式"""
    
    success: bool = Field(..., description="请求是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[DataType] = Field(None, description="响应数据")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="错误信息列表")
    meta: Optional[Dict[str, Any]] = Field(None, description="元数据信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaginatedResponse(BaseModel, Generic[DataType]):
    """分页响应格式"""
    
    items: List[DataType] = Field(..., description="数据项列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")


class APIListResponse(APIResponse[PaginatedResponse[DataType]]):
    """列表响应格式"""
    pass


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="API版本")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")
    services: Dict[str, str] = Field(default_factory=dict, description="服务状态")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorDetail(BaseModel):
    """错误详情"""
    
    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    field: Optional[str] = Field(None, description="相关字段")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")


class ValidationErrorResponse(BaseModel):
    """验证错误响应"""
    
    success: bool = Field(False, description="请求是否成功")
    message: str = Field("数据验证失败", description="响应消息")
    errors: List[ErrorDetail] = Field(..., description="验证错误列表")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# 响应工具函数
def create_success_response(
    data: Any = None,
    message: str = "操作成功",
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """创建成功响应"""
    return {
        "success": True,
        "message": message,
        "data": data,
        "errors": None,
        "meta": meta,
        "timestamp": datetime.now().isoformat()
    }


def create_error_response(
    message: str = "操作失败",
    errors: Optional[List[Dict[str, Any]]] = None,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """创建错误响应"""
    return {
        "success": False,
        "message": message,
        "data": None,
        "errors": errors or [],
        "meta": meta,
        "timestamp": datetime.now().isoformat()
    }


def create_paginated_response(
    items: List[Any],
    total: int,
    page: int,
    size: int,
    message: str = "查询成功"
) -> Dict[str, Any]:
    """创建分页响应"""
    pages = (total + size - 1) // size  # 向上取整
    
    paginated_data = {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1
    }
    
    return create_success_response(
        data=paginated_data,
        message=message,
        meta={
            "pagination": {
                "total": total,
                "page": page,
                "size": size,
                "pages": pages
            }
        }
    )