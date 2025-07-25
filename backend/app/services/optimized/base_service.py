"""
优化的服务基类
提供统一的服务层功能和错误处理
"""

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from uuid import UUID
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.crud.base_optimized import CRUDBase
from app.db.base_class_optimized import BaseModel as DBBaseModel

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=DBBaseModel)
CRUDType = TypeVar("CRUDType", bound=CRUDBase)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class ServiceException(Exception):
    """服务层异常基类"""
    
    def __init__(self, message: str, code: str = "SERVICE_ERROR", details: Dict[str, Any] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(ServiceException):
    """验证错误"""
    
    def __init__(self, message: str, field: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field


class NotFoundError(ServiceException):
    """资源未找到错误"""
    
    def __init__(self, resource: str, identifier: Union[str, UUID], details: Dict[str, Any] = None):
        message = f"{resource} with id '{identifier}' not found"
        super().__init__(message, "NOT_FOUND", details)
        self.resource = resource
        self.identifier = identifier


class PermissionError(ServiceException):
    """权限错误"""
    
    def __init__(self, message: str, required_permission: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "PERMISSION_DENIED", details)
        self.required_permission = required_permission


class BaseService(ABC):
    """服务基类"""
    
    def __init__(self, crud: CRUDType, model_name: str):
        self.crud = crud
        self.model_name = model_name
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    def _log_operation(self, operation: str, details: Dict[str, Any] = None):
        """记录操作日志"""
        log_data = {
            "service": self.__class__.__name__,
            "operation": operation,
            "model": self.model_name,
            **(details or {})
        }
        self.logger.info(f"Service operation: {operation}", extra=log_data)
    
    def _handle_error(self, operation: str, error: Exception, context: Dict[str, Any] = None):
        """统一错误处理"""
        error_data = {
            "service": self.__class__.__name__,
            "operation": operation,
            "model": self.model_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            **(context or {})
        }
        
        self.logger.error(f"Service error in {operation}: {str(error)}", extra=error_data)
        
        if isinstance(error, ServiceException):
            raise error
        else:
            raise ServiceException(
                message=f"Internal error in {operation}: {str(error)}",
                code="INTERNAL_ERROR",
                details=error_data
            )
    
    def get_by_id(
        self,
        db: Session,
        *,
        id: Union[UUID, str],
        user_id: Union[UUID, str] = None
    ) -> Optional[ModelType]:
        """根据ID获取资源"""
        try:
            self._log_operation("get_by_id", {"id": str(id), "user_id": str(user_id) if user_id else None})
            
            obj = self.crud.get(db, id=id)
            if not obj:
                raise NotFoundError(self.model_name, id)
            
            # 如果需要用户权限检查
            if user_id and hasattr(obj, 'user_id'):
                if str(obj.user_id) != str(user_id):
                    raise PermissionError(f"Access denied to {self.model_name}")
            
            return obj
            
        except Exception as e:
            self._handle_error("get_by_id", e, {"id": str(id)})
    
    def get_list(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        user_id: Union[UUID, str] = None,
        include_deleted: bool = False
    ) -> List[ModelType]:
        """获取资源列表"""
        try:
            self._log_operation("get_list", {
                "skip": skip, 
                "limit": limit, 
                "user_id": str(user_id) if user_id else None
            })
            
            if user_id and hasattr(self.crud, 'get_by_user'):
                return self.crud.get_by_user(db, user_id=user_id, skip=skip, limit=limit)
            else:
                return self.crud.get_multi(db, skip=skip, limit=limit, include_deleted=include_deleted)
                
        except Exception as e:
            self._handle_error("get_list", e, {"skip": skip, "limit": limit})
    
    def create(
        self,
        db: Session,
        *,
        obj_in: CreateSchemaType,
        user_id: Union[UUID, str] = None
    ) -> ModelType:
        """创建资源"""
        try:
            self._log_operation("create", {"user_id": str(user_id) if user_id else None})
            
            # 执行创建前验证
            self._validate_create(obj_in, user_id)
            
            if user_id and hasattr(self.crud, 'create_with_user'):
                obj = self.crud.create_with_user(db, obj_in=obj_in, user_id=user_id)
            else:
                obj = self.crud.create(db, obj_in=obj_in)
            
            # 执行创建后处理
            self._after_create(db, obj, user_id)
            
            return obj
            
        except Exception as e:
            self._handle_error("create", e, {"obj_in": str(obj_in)})
    
    def update(
        self,
        db: Session,
        *,
        id: Union[UUID, str],
        obj_in: UpdateSchemaType,
        user_id: Union[UUID, str] = None
    ) -> Optional[ModelType]:
        """更新资源"""
        try:
            self._log_operation("update", {"id": str(id), "user_id": str(user_id) if user_id else None})
            
            # 获取现有对象
            db_obj = self.get_by_id(db, id=id, user_id=user_id)
            
            # 执行更新前验证
            self._validate_update(db_obj, obj_in, user_id)
            
            # 更新对象
            updated_obj = self.crud.update(db, db_obj=db_obj, obj_in=obj_in)
            
            # 执行更新后处理
            self._after_update(db, updated_obj, user_id)
            
            return updated_obj
            
        except Exception as e:
            self._handle_error("update", e, {"id": str(id), "obj_in": str(obj_in)})
    
    def delete(
        self,
        db: Session,
        *,
        id: Union[UUID, str],
        user_id: Union[UUID, str] = None,
        soft: bool = True
    ) -> ModelType:
        """删除资源"""
        try:
            self._log_operation("delete", {"id": str(id), "soft": soft, "user_id": str(user_id) if user_id else None})
            
            # 获取现有对象
            db_obj = self.get_by_id(db, id=id, user_id=user_id)
            
            # 执行删除前验证
            self._validate_delete(db_obj, user_id)
            
            # 删除对象
            deleted_obj = self.crud.remove(db, id=id, soft=soft)
            
            # 执行删除后处理
            self._after_delete(db, deleted_obj, user_id)
            
            return deleted_obj
            
        except Exception as e:
            self._handle_error("delete", e, {"id": str(id)})
    
    def search(
        self,
        db: Session,
        *,
        query: str,
        skip: int = 0,
        limit: int = 100,
        user_id: Union[UUID, str] = None
    ) -> List[ModelType]:
        """搜索资源"""
        try:
            self._log_operation("search", {
                "query": query, 
                "skip": skip, 
                "limit": limit,
                "user_id": str(user_id) if user_id else None
            })
            
            if hasattr(self.crud, 'search'):
                return self.crud.search(db, query=query, skip=skip, limit=limit)
            else:
                raise ServiceException("Search not supported for this resource", "NOT_SUPPORTED")
                
        except Exception as e:
            self._handle_error("search", e, {"query": query})
    
    def count(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None,
        include_deleted: bool = False
    ) -> int:
        """计算资源数量"""
        try:
            self._log_operation("count", {"user_id": str(user_id) if user_id else None})
            
            if user_id and hasattr(self.crud, 'count_by_user'):
                return self.crud.count_by_user(db, user_id=user_id)
            else:
                return self.crud.count(db, include_deleted=include_deleted)
                
        except Exception as e:
            self._handle_error("count", e)
    
    # 钩子方法，子类可以重写
    def _validate_create(self, obj_in: CreateSchemaType, user_id: Union[UUID, str] = None):
        """创建前验证（子类可重写）"""
        pass
    
    def _validate_update(self, db_obj: ModelType, obj_in: UpdateSchemaType, user_id: Union[UUID, str] = None):
        """更新前验证（子类可重写）"""
        pass
    
    def _validate_delete(self, db_obj: ModelType, user_id: Union[UUID, str] = None):
        """删除前验证（子类可重写）"""
        pass
    
    def _after_create(self, db: Session, obj: ModelType, user_id: Union[UUID, str] = None):
        """创建后处理（子类可重写）"""
        pass
    
    def _after_update(self, db: Session, obj: ModelType, user_id: Union[UUID, str] = None):
        """更新后处理（子类可重写）"""
        pass
    
    def _after_delete(self, db: Session, obj: ModelType, user_id: Union[UUID, str] = None):
        """删除后处理（子类可重写）"""
        pass


class AsyncBaseService(BaseService):
    """异步服务基类"""
    
    async def async_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """异步操作包装器"""
        try:
            self._log_operation(f"async_{operation_name}", {"args": str(args), "kwargs": str(kwargs)})
            return await operation_func(*args, **kwargs)
        except Exception as e:
            self._handle_error(f"async_{operation_name}", e)
    
    async def background_task(self, task_name: str, task_func, *args, **kwargs):
        """后台任务执行"""
        try:
            self._log_operation(f"background_{task_name}", {"args": str(args), "kwargs": str(kwargs)})
            # 这里可以集成Celery或其他任务队列
            return await task_func(*args, **kwargs)
        except Exception as e:
            self._handle_error(f"background_{task_name}", e)