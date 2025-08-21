"""
Task Service Factory

任务服务工厂，负责创建和组装所有任务相关服务
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session

from ..services.task_application_service import TaskApplicationService
from ...domain.services.task_domain_service import TaskDomainService
from ...infrastructure.repositories.task_repository import TaskRepository
from ...infrastructure.services.task_execution_service import TaskExecutionService
from ...infrastructure.services.task_notification_service import TaskNotificationService
from ...infrastructure.services.task_scheduler_service import TaskSchedulerService

logger = logging.getLogger(__name__)


class TaskServiceFactory:
    """任务服务工厂"""
    
    @staticmethod
    def create_task_application_service(db_session: Optional[Session] = None) -> TaskApplicationService:
        """创建任务应用服务"""
        try:
            # 创建基础设施服务
            task_repository = TaskRepository(db_session)
            execution_service = TaskExecutionService()
            notification_service = TaskNotificationService()
            scheduler_service = TaskSchedulerService()
            
            # 创建领域服务
            domain_service = TaskDomainService()
            
            # 创建应用服务
            application_service = TaskApplicationService(
                task_repository=task_repository,
                execution_service=execution_service,
                notification_service=notification_service,
                scheduler_service=scheduler_service,
                domain_service=domain_service
            )
            
            # 设置调度器的任务执行回调
            async def execution_callback(task_id: str):
                """调度器任务执行回调"""
                return await application_service.execute_task(
                    task_id=task_id,
                    execution_mode=ExecutionMode.SCHEDULED,
                    triggered_by="scheduler"
                )
            
            scheduler_service.set_execution_callback(execution_callback)
            
            logger.info("Task application service created successfully")
            return application_service
            
        except Exception as e:
            logger.error(f"Failed to create task application service: {e}")
            raise
    
    @staticmethod
    def create_task_scheduler_service() -> TaskSchedulerService:
        """创建独立的任务调度服务"""
        return TaskSchedulerService()
    
    @staticmethod
    def create_task_repository(db_session: Optional[Session] = None) -> TaskRepository:
        """创建任务仓储"""
        return TaskRepository(db_session)
    
    @staticmethod
    def create_task_domain_service() -> TaskDomainService:
        """创建任务领域服务"""
        return TaskDomainService()


# 导入执行模式枚举以便在回调中使用
from ...domain.entities.task_entity import ExecutionMode