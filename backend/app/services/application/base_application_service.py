"""
Base Application Service - DDD架构基础应用服务

提供统一的应用服务基类，确保所有应用服务遵循一致的架构模式
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

T = TypeVar('T')  # 泛型类型变量


class OperationResult(Enum):
    """操作结果状态"""
    SUCCESS = "success"
    FAILURE = "failure" 
    PARTIAL_SUCCESS = "partial_success"
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"


@dataclass
class ApplicationResult(Generic[T]):
    """统一的应用服务返回结果"""
    success: bool
    result: OperationResult
    data: Optional[T] = None
    message: str = ""
    errors: List[str] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None
    execution_time_ms: Optional[float] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}
    
    @classmethod
    def success_result(cls, data: T = None, message: str = "操作成功") -> 'ApplicationResult[T]':
        """创建成功结果"""
        return cls(
            success=True,
            result=OperationResult.SUCCESS,
            data=data,
            message=message
        )
    
    @classmethod
    def failure_result(cls, message: str = "操作失败", errors: List[str] = None) -> 'ApplicationResult[T]':
        """创建失败结果"""
        return cls(
            success=False,
            result=OperationResult.FAILURE,
            message=message,
            errors=errors or []
        )
    
    @classmethod
    def validation_error_result(cls, message: str = "验证失败", errors: List[str] = None) -> 'ApplicationResult[T]':
        """创建验证错误结果"""
        return cls(
            success=False,
            result=OperationResult.VALIDATION_ERROR,
            message=message,
            errors=errors or []
        )
    
    @classmethod
    def not_found_result(cls, message: str = "资源不存在") -> 'ApplicationResult[T]':
        """创建未找到结果"""
        return cls(
            success=False,
            result=OperationResult.NOT_FOUND,
            message=message
        )


@dataclass
class PaginationRequest:
    """分页请求"""
    page: int = 1
    size: int = 20
    skip: Optional[int] = None
    
    def __post_init__(self):
        if self.skip is None:
            self.skip = (self.page - 1) * self.size


@dataclass
class PaginationResult(Generic[T]):
    """分页结果"""
    items: List[T]
    total: int
    page: int
    size: int
    pages: int
    has_next: bool
    has_prev: bool
    
    @classmethod
    def create(cls, items: List[T], total: int, pagination: PaginationRequest) -> 'PaginationResult[T]':
        """创建分页结果"""
        pages = (total + pagination.size - 1) // pagination.size
        return cls(
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=pages,
            has_next=pagination.page < pages,
            has_prev=pagination.page > 1
        )


class BaseApplicationService(ABC):
    """基础应用服务抽象类
    
    所有应用服务都应该继承此类，确保架构一致性
    """
    
    def __init__(self, service_name: str = None):
        self.service_name = service_name or self.__class__.__name__
        self.logger = logging.getLogger(f"application.{self.service_name}")
        
    def log_operation_start(self, operation: str, **kwargs):
        """记录操作开始"""
        self.logger.info(f"开始执行操作: {operation}", extra=kwargs)
    
    def log_operation_success(self, operation: str, duration_ms: float = None, **kwargs):
        """记录操作成功"""
        extra = {"duration_ms": duration_ms} if duration_ms else {}
        extra.update(kwargs)
        self.logger.info(f"操作成功完成: {operation}", extra=extra)
    
    def log_operation_failure(self, operation: str, error: Exception, **kwargs):
        """记录操作失败"""
        self.logger.error(f"操作失败: {operation} - {str(error)}", extra=kwargs, exc_info=True)
    
    def validate_required_params(self, **params) -> ApplicationResult[None]:
        """验证必需参数"""
        missing_params = []
        for param_name, param_value in params.items():
            if param_value is None or param_value == "":
                missing_params.append(param_name)
        
        if missing_params:
            return ApplicationResult.validation_error_result(
                message=f"缺少必需参数: {', '.join(missing_params)}",
                errors=[f"参数 '{param}' 不能为空" for param in missing_params]
            )
        
        return ApplicationResult.success_result()
    
    def handle_domain_exceptions(self, operation: str, func, *args, **kwargs) -> ApplicationResult:
        """统一处理领域异常"""
        try:
            self.log_operation_start(operation)
            start_time = datetime.now()
            
            result = func(*args, **kwargs)
            
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            self.log_operation_success(operation, duration_ms)
            
            if isinstance(result, ApplicationResult):
                result.execution_time_ms = duration_ms
                return result
            else:
                return ApplicationResult.success_result(
                    data=result,
                    message=f"{operation} 执行成功"
                )
                
        except ValueError as e:
            self.log_operation_failure(operation, e)
            return ApplicationResult.validation_error_result(
                message=f"{operation} 验证失败",
                errors=[str(e)]
            )
        except FileNotFoundError as e:
            self.log_operation_failure(operation, e)
            return ApplicationResult.not_found_result(
                message=f"{operation} 未找到资源: {str(e)}"
            )
        except PermissionError as e:
            self.log_operation_failure(operation, e)
            return ApplicationResult(
                success=False,
                result=OperationResult.PERMISSION_DENIED,
                message=f"{operation} 权限不足",
                errors=[str(e)]
            )
        except Exception as e:
            self.log_operation_failure(operation, e)
            return ApplicationResult.failure_result(
                message=f"{operation} 执行失败",
                errors=[str(e)]
            )
    
    async def handle_domain_exceptions_async(self, operation: str, func, *args, **kwargs) -> ApplicationResult:
        """统一处理领域异常 - 异步版本"""
        try:
            self.log_operation_start(operation)
            start_time = datetime.now()
            
            result = await func(*args, **kwargs)
            
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            self.log_operation_success(operation, duration_ms)
            
            if isinstance(result, ApplicationResult):
                return result
            else:
                return ApplicationResult.success_result(result)
                
        except ValidationError as e:
            self.log_operation_failure(operation, e)
            return ApplicationResult.validation_error_result(
                message=f"{operation} 验证失败",
                errors=[str(e)]
            )
        except FileNotFoundError as e:
            self.log_operation_failure(operation, e)
            return ApplicationResult.not_found_result(
                message=f"{operation} 未找到资源: {str(e)}"
            )
        except PermissionError as e:
            self.log_operation_failure(operation, e)
            return ApplicationResult(
                success=False,
                result=OperationResult.PERMISSION_DENIED,
                message=f"{operation} 权限不足",
                errors=[str(e)]
            )
        except Exception as e:
            self.log_operation_failure(operation, e)
            return ApplicationResult.failure_result(
                message=f"{operation} 执行失败",
                errors=[str(e)]
            )


class DomainEventPublisher:
    """领域事件发布器"""
    
    def __init__(self):
        self._handlers: Dict[str, List[callable]] = {}
    
    def subscribe(self, event_type: str, handler: callable):
        """订阅事件"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def publish(self, event_type: str, event_data: Dict[str, Any]):
        """发布事件"""
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    handler(event_data)
                except Exception as e:
                    logger.error(f"事件处理器执行失败: {event_type} - {e}")


# 全局事件发布器实例
event_publisher = DomainEventPublisher()


class TransactionalApplicationService(BaseApplicationService):
    """事务性应用服务基类
    
    需要数据库事务支持的应用服务应继承此类
    """
    
    def __init__(self, service_name: str = None):
        super().__init__(service_name)
        self.event_publisher = event_publisher
    
    def execute_in_transaction(self, db_session, operation: str, func, *args, **kwargs):
        """在事务中执行操作"""
        try:
            result = self.handle_domain_exceptions(operation, func, *args, **kwargs)

            if result.success:
                # 在 commit 之前准备事件数据，避免会话脱离问题
                event_data = self._prepare_event_data(result.data)

                db_session.commit()
                # 发布领域事件
                self.event_publisher.publish(f"{self.service_name}.{operation}.success", {
                    "service": self.service_name,
                    "operation": operation,
                    "result": event_data,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                db_session.rollback()
                self.event_publisher.publish(f"{self.service_name}.{operation}.failure", {
                    "service": self.service_name,
                    "operation": operation,
                    "errors": result.errors,
                    "timestamp": datetime.now().isoformat()
                })
            
            return result
            
        except Exception as e:
            db_session.rollback()
            self.logger.error(f"事务执行失败: {operation} - {str(e)}")
            return ApplicationResult.failure_result(
                message=f"事务执行失败: {operation}",
                errors=[str(e)]
            )

    def _prepare_event_data(self, data):
        """准备事件数据，避免 SQLAlchemy 会话脱离问题"""
        if data is None:
            return None

        # 如果是 SQLAlchemy 模型对象，提取基本属性
        if hasattr(data, '__table__'):
            # 获取所有列的值，避免关系字段的延迟加载
            result = {}
            for column in data.__table__.columns:
                try:
                    value = getattr(data, column.name, None)
                    # 处理特殊类型
                    if hasattr(value, 'isoformat'):  # datetime 对象
                        value = value.isoformat()
                    result[column.name] = value
                except:
                    result[column.name] = None
            return result

        # 对于其他类型，直接返回
        return data


# 应用服务注册表
_application_services: Dict[str, BaseApplicationService] = {}


def register_application_service(service_name: str, service_instance: BaseApplicationService):
    """注册应用服务"""
    _application_services[service_name] = service_instance
    logger.info(f"已注册应用服务: {service_name}")


def get_application_service(service_name: str) -> Optional[BaseApplicationService]:
    """获取应用服务"""
    return _application_services.get(service_name)


def list_application_services() -> List[str]:
    """列出所有已注册的应用服务"""
    return list(_application_services.keys())


logger.info("✅ Base Application Service架构组件加载完成")