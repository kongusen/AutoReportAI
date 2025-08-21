"""
Task Application Service

任务应用服务，协调领域服务和基础设施服务
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ...domain.entities.task_entity import TaskEntity, ExecutionMode, TaskStatus
from ...domain.services.task_domain_service import TaskDomainService
from ..interfaces.task_repository_interface import TaskRepositoryInterface
from ..interfaces.task_execution_interface import TaskExecutionInterface
from ..interfaces.task_notification_interface import TaskNotificationInterface
from ..interfaces.task_scheduler_interface import TaskSchedulerInterface

logger = logging.getLogger(__name__)


class TaskApplicationService:
    """任务应用服务"""
    
    def __init__(self, 
                 task_repository: TaskRepositoryInterface,
                 execution_service: TaskExecutionInterface,
                 notification_service: TaskNotificationInterface,
                 scheduler_service: TaskSchedulerInterface,
                 domain_service: TaskDomainService = None):
        self.task_repository = task_repository
        self.execution_service = execution_service
        self.notification_service = notification_service
        self.scheduler_service = scheduler_service
        self.domain_service = domain_service or TaskDomainService()
    
    async def create_task(self, task_data: Dict[str, Any], 
                         owner_id: str) -> TaskEntity:
        """创建任务"""
        try:
            # 生成任务ID
            task_id = await self.task_repository.generate_task_id()
            
            # 使用领域服务创建任务
            task = self.domain_service.create_task(
                task_id=task_id,
                name=task_data.get("name", "新任务"),
                task_type=task_data.get("task_type", "report_generation"),
                configuration=task_data.get("configuration", {}),
                owner_id=owner_id
            )
            
            # 设置额外属性
            if "description" in task_data:
                task.description = task_data["description"]
            
            if "template_id" in task_data:
                task.template_id = task_data["template_id"]
            
            if "data_source_id" in task_data:
                task.data_source_id = task_data["data_source_id"]
            
            if "parameters" in task_data:
                task.update_parameters(task_data["parameters"])
            
            # 保存到数据库
            saved_task = await self.task_repository.save(task)
            
            # 设置调度（如果有）
            if task_data.get("schedule_config"):
                await self._setup_schedule(saved_task, task_data["schedule_config"])
            
            # 发送创建通知
            await self.notification_service.send_task_created(
                task_id=saved_task.id,
                task_name=saved_task.name,
                owner_id=owner_id
            )
            
            logger.info(f"Task created successfully: {saved_task.id}")
            return saved_task
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise
    
    async def update_task(self, task_id: str, 
                         update_data: Dict[str, Any]) -> Optional[TaskEntity]:
        """更新任务"""
        try:
            task = await self.task_repository.get_by_id(task_id)
            if not task:
                return None
            
            # 更新基本属性
            if "name" in update_data:
                task.name = update_data["name"]
            
            if "description" in update_data:
                task.description = update_data["description"]
            
            if "configuration" in update_data:
                task.update_configuration(update_data["configuration"])
            
            if "parameters" in update_data:
                task.update_parameters(update_data["parameters"])
            
            # 验证更新后的任务
            validation_errors = self.domain_service.validate_task(task)
            if validation_errors:
                raise ValueError(f"Task validation failed: {validation_errors}")
            
            # 保存更新
            updated_task = await self.task_repository.save(task)
            
            # 更新调度（如果有变化）
            if "schedule_config" in update_data:
                if update_data["schedule_config"]:
                    await self._setup_schedule(updated_task, update_data["schedule_config"])
                else:
                    await self._remove_schedule(updated_task)
            
            logger.info(f"Task updated successfully: {task_id}")
            return updated_task
            
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            raise
    
    async def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        try:
            task = await self.task_repository.get_by_id(task_id)
            if not task:
                return False
            
            # 取消正在运行的执行
            if task.is_running():
                await self.cancel_execution(task_id)
            
            # 移除调度
            await self._remove_schedule(task)
            
            # 软删除任务
            task.delete()
            await self.task_repository.save(task)
            
            # 发送删除通知
            await self.notification_service.send_task_deleted(
                task_id=task_id,
                task_name=task.name,
                owner_id=task.owner_id
            )
            
            logger.info(f"Task deleted successfully: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            return False
    
    async def execute_task(self, task_id: str, 
                          execution_mode: ExecutionMode = ExecutionMode.MANUAL,
                          context: Dict[str, Any] = None,
                          triggered_by: Optional[str] = None) -> Dict[str, Any]:
        """执行任务"""
        try:
            task = await self.task_repository.get_by_id(task_id)
            if not task:
                return {"success": False, "error": "Task not found"}
            
            # 规划执行
            execution_plan = self.domain_service.plan_execution(
                task, execution_mode, context
            )
            
            # 检查前置条件
            if execution_plan["prerequisites"]:
                return {
                    "success": False,
                    "error": f"Prerequisites not met: {execution_plan['prerequisites']}"
                }
            
            # 开始执行
            execution = task.start_execution(
                execution_mode=execution_mode,
                triggered_by=triggered_by,
                context=context or {}
            )
            
            # 保存任务状态
            await self.task_repository.save(task)
            
            # 发送开始通知
            await self.notification_service.send_execution_started(
                task_id=task_id,
                execution_id=execution.execution_id,
                owner_id=task.owner_id
            )
            
            # 提交给执行服务
            execution_result = await self.execution_service.execute(
                task=task,
                execution=execution,
                context=context or {}
            )
            
            # 处理执行结果
            if execution_result["success"]:
                task.complete_execution(execution_result.get("data", {}))
                
                # 发送完成通知
                await self.notification_service.send_execution_completed(
                    task_id=task_id,
                    execution_id=execution.execution_id,
                    result_data=execution_result.get("data", {}),
                    owner_id=task.owner_id
                )
            else:
                task.fail_execution(execution_result.get("error", "Unknown error"))
                
                # 发送失败通知
                await self.notification_service.send_execution_failed(
                    task_id=task_id,
                    execution_id=execution.execution_id,
                    error_message=execution_result.get("error", "Unknown error"),
                    owner_id=task.owner_id
                )
            
            # 保存最终状态
            await self.task_repository.save(task)
            
            logger.info(f"Task execution completed: {task_id}")
            return {
                "success": execution_result["success"],
                "execution_id": execution.execution_id,
                "data": execution_result.get("data"),
                "error": execution_result.get("error")
            }
            
        except Exception as e:
            logger.error(f"Failed to execute task {task_id}: {e}")
            
            # 尝试更新任务状态为失败
            try:
                task = await self.task_repository.get_by_id(task_id)
                if task and task.current_execution:
                    task.fail_execution(str(e))
                    await self.task_repository.save(task)
            except:
                pass
            
            return {"success": False, "error": str(e)}
    
    async def cancel_execution(self, task_id: str) -> bool:
        """取消执行"""
        try:
            task = await self.task_repository.get_by_id(task_id)
            if not task or not task.is_running():
                return False
            
            # 取消执行服务中的任务
            cancelled = await self.execution_service.cancel_execution(
                task.current_execution.execution_id
            )
            
            if cancelled:
                task.cancel_execution()
                await self.task_repository.save(task)
                
                # 发送取消通知
                await self.notification_service.send_execution_cancelled(
                    task_id=task_id,
                    execution_id=task.current_execution.execution_id,
                    owner_id=task.owner_id
                )
            
            return cancelled
            
        except Exception as e:
            logger.error(f"Failed to cancel execution for task {task_id}: {e}")
            return False
    
    async def get_task(self, task_id: str) -> Optional[TaskEntity]:
        """获取任务"""
        return await self.task_repository.get_by_id(task_id)
    
    async def get_user_tasks(self, user_id: str, 
                           filters: Dict[str, Any] = None,
                           pagination: Dict[str, Any] = None) -> List[TaskEntity]:
        """获取用户任务列表"""
        return await self.task_repository.get_by_user(
            user_id=user_id,
            filters=filters or {},
            pagination=pagination or {}
        )
    
    async def activate_task(self, task_id: str) -> bool:
        """激活任务"""
        try:
            task = await self.task_repository.get_by_id(task_id)
            if not task:
                return False
            
            task.activate()
            await self.task_repository.save(task)
            
            # 重新设置调度（如果有）
            if task.schedule_config:
                await self._setup_schedule(task, task.schedule_config.__dict__)
            
            # 发送激活通知
            await self.notification_service.send_task_activated(
                task_id=task_id,
                task_name=task.name,
                owner_id=task.owner_id
            )
            
            logger.info(f"Task activated: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to activate task {task_id}: {e}")
            return False
    
    async def deactivate_task(self, task_id: str) -> bool:
        """停用任务"""
        try:
            task = await self.task_repository.get_by_id(task_id)
            if not task:
                return False
            
            # 取消正在运行的执行
            if task.is_running():
                await self.cancel_execution(task_id)
            
            task.deactivate()
            await self.task_repository.save(task)
            
            # 移除调度
            await self._remove_schedule(task)
            
            # 发送停用通知
            await self.notification_service.send_task_deactivated(
                task_id=task_id,
                task_name=task.name,
                owner_id=task.owner_id
            )
            
            logger.info(f"Task deactivated: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deactivate task {task_id}: {e}")
            return False
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        try:
            # 先从执行服务获取实时状态
            execution_status = await self.execution_service.get_execution_status(task_id)
            if execution_status:
                return execution_status
            
            # 从数据库获取任务状态
            task = await self.task_repository.get_by_id(task_id)
            if not task:
                return {"status": "not_found"}
            
            return {
                "status": task.status.value,
                "is_running": task.is_running(),
                "last_execution": (
                    task.get_latest_execution().to_dict() 
                    if task.get_latest_execution() else None
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to get task status {task_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_task_performance(self, task_id: str) -> Dict[str, Any]:
        """获取任务性能分析"""
        try:
            task = await self.task_repository.get_by_id(task_id)
            if not task:
                return {"error": "Task not found"}
            
            return self.domain_service.analyze_task_performance(task)
            
        except Exception as e:
            logger.error(f"Failed to get task performance {task_id}: {e}")
            return {"error": str(e)}
    
    async def _setup_schedule(self, task: TaskEntity, schedule_config: Dict[str, Any]):
        """设置任务调度"""
        try:
            # 使用领域服务配置调度
            self.domain_service.configure_schedule(
                task=task,
                cron_expression=schedule_config["cron_expression"],
                timezone=schedule_config.get("timezone", "UTC"),
                max_retries=schedule_config.get("max_retries", 3)
            )
            
            # 在调度器中注册
            await self.scheduler_service.schedule_task(
                task_id=task.id,
                schedule_config=task.schedule_config
            )
            
        except Exception as e:
            logger.error(f"Failed to setup schedule for task {task.id}: {e}")
            raise
    
    async def _remove_schedule(self, task: TaskEntity):
        """移除任务调度"""
        try:
            if task.schedule_config:
                await self.scheduler_service.unschedule_task(task.id)
                task.remove_schedule()
                
        except Exception as e:
            logger.error(f"Failed to remove schedule for task {task.id}: {e}")
            # 不抛出异常，因为这不应该阻止其他操作