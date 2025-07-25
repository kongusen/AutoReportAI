"""
优化的API路由基类
提供统一的API端点功能和错误处理
"""

from typing import Any, Dict, List, Optional, Type, Union
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.deps import get_current_user, get_db
from app.models.optimized.user import User
from app.services.optimized.base_service import BaseService, ServiceException, ValidationError, NotFoundError, PermissionError


class APIResponse(BaseModel):
    """标准API响应格式"""
    success: bool = True
    message: str = "操作成功"
    data: Any = None
    meta: Optional[Dict[str, Any]] = None


class PaginatedResponse(APIResponse):
    """分页响应格式"""
    data: List[Any]
    meta: Dict[str, Any]  # 包含 total, page, size, pages 等分页信息


class BaseRouter:
    """API路由基类"""
    
    def __init__(
        self, 
        service: BaseService,
        prefix: str,
        tags: List[str],
        response_model: Type[BaseModel] = None,
        create_schema: Type[BaseModel] = None,
        update_schema: Type[BaseModel] = None
    ):
        self.service = service
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.response_model = response_model
        self.create_schema = create_schema
        self.update_schema = update_schema
        
        # 注册通用路由
        self._register_routes()
    
    def _register_routes(self):
        """注册通用路由"""
        
        @self.router.get("", response_model=PaginatedResponse)
        async def get_list(
            skip: int = Query(0, ge=0, description="跳过的记录数"),
            limit: int = Query(100, ge=1, le=1000, description="返回的记录数"),
            search: Optional[str] = Query(None, description="搜索关键词"),
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """获取资源列表"""
            try:
                if search:
                    items = self.service.search(
                        db, query=search, skip=skip, limit=limit, user_id=current_user.id
                    )
                    total = len(items)  # 简化处理
                else:
                    items = self.service.get_list(
                        db, skip=skip, limit=limit, user_id=current_user.id
                    )
                    total = self.service.count(db, user_id=current_user.id)
                
                return PaginatedResponse(
                    data=items,
                    meta={
                        "total": total,
                        "page": skip // limit + 1,
                        "size": limit,
                        "pages": (total + limit - 1) // limit
                    }
                )
                
            except ServiceException as e:
                raise HTTPException(
                    status_code=self._map_service_error_to_http_status(e),
                    detail={"message": e.message, "code": e.code, "details": e.details}
                )
        
        @self.router.get("/{id}", response_model=APIResponse)
        async def get_by_id(
            id: UUID,
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """根据ID获取资源"""
            try:
                item = self.service.get_by_id(db, id=id, user_id=current_user.id)
                return APIResponse(data=item)
                
            except ServiceException as e:
                raise HTTPException(
                    status_code=self._map_service_error_to_http_status(e),
                    detail={"message": e.message, "code": e.code, "details": e.details}
                )
        
        if self.create_schema:
            @self.router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
            async def create_item(
                item_data: self.create_schema,
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)
            ):
                """创建资源"""
                try:
                    item = self.service.create(db, obj_in=item_data, user_id=current_user.id)
                    return APIResponse(
                        message="创建成功",
                        data=item
                    )
                    
                except ServiceException as e:
                    raise HTTPException(
                        status_code=self._map_service_error_to_http_status(e),
                        detail={"message": e.message, "code": e.code, "details": e.details}
                    )
        
        if self.update_schema:
            @self.router.put("/{id}", response_model=APIResponse)
            async def update_item(
                id: UUID,
                item_data: self.update_schema,
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)
            ):
                """更新资源"""
                try:
                    item = self.service.update(
                        db, id=id, obj_in=item_data, user_id=current_user.id
                    )
                    return APIResponse(
                        message="更新成功",
                        data=item
                    )
                    
                except ServiceException as e:
                    raise HTTPException(
                        status_code=self._map_service_error_to_http_status(e),
                        detail={"message": e.message, "code": e.code, "details": e.details}
                    )
        
        @self.router.delete("/{id}", response_model=APIResponse)
        async def delete_item(
            id: UUID,
            soft: bool = Query(True, description="是否软删除"),
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """删除资源"""
            try:
                item = self.service.delete(
                    db, id=id, user_id=current_user.id, soft=soft
                )
                return APIResponse(
                    message="删除成功",
                    data={"id": str(id), "deleted": True, "soft_delete": soft}
                )
                
            except ServiceException as e:
                raise HTTPException(
                    status_code=self._map_service_error_to_http_status(e),
                    detail={"message": e.message, "code": e.code, "details": e.details}
                )
    
    def _map_service_error_to_http_status(self, error: ServiceException) -> int:
        """映射服务错误到HTTP状态码"""
        error_mapping = {
            "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
            "NOT_FOUND": status.HTTP_404_NOT_FOUND,
            "PERMISSION_DENIED": status.HTTP_403_FORBIDDEN,
            "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "NOT_SUPPORTED": status.HTTP_501_NOT_IMPLEMENTED,
        }
        
        return error_mapping.get(error.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def add_custom_route(
        self,
        path: str,
        methods: List[str],
        endpoint_func,
        **kwargs
    ):
        """添加自定义路由"""
        for method in methods:
            if method.upper() == "GET":
                self.router.get(path, **kwargs)(endpoint_func)
            elif method.upper() == "POST":
                self.router.post(path, **kwargs)(endpoint_func)
            elif method.upper() == "PUT":
                self.router.put(path, **kwargs)(endpoint_func)
            elif method.upper() == "DELETE":
                self.router.delete(path, **kwargs)(endpoint_func)
            elif method.upper() == "PATCH":
                self.router.patch(path, **kwargs)(endpoint_func)
    
    def get_router(self) -> APIRouter:
        """获取路由器"""
        return self.router


class AsyncBaseRouter(BaseRouter):
    """异步API路由基类"""
    
    def add_async_route(
        self,
        path: str,
        methods: List[str],
        endpoint_func,
        **kwargs
    ):
        """添加异步路由"""
        for method in methods:
            if method.upper() == "GET":
                self.router.get(path, **kwargs)(endpoint_func)
            elif method.upper() == "POST":
                self.router.post(path, **kwargs)(endpoint_func)
            # 其他方法类似...