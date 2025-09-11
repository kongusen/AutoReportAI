"""
Application层 - 任务应用服务

重构后的任务应用服务，集成新的TaskExecutionService和Celery任务系统
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from celery.result import AsyncResult

from app.models.task import Task, TaskExecution, TaskStatus, ReportPeriod, ProcessingMode, AgentWorkflowType
from app.models.user import User
from app.models.data_source import DataSource  
from app.models.template import Template
from app.services.application.tasks.task_execution_service import TaskExecutionService
from app.services.infrastructure.task_queue.tasks import execute_report_task, validate_placeholders_task, scheduled_task_runner
from app.services.infrastructure.task_queue.celery_config import celery_app
from app.core.exceptions import ValidationError, NotFoundError
from app.utils.time_context import TimeContextManager

logger = logging.getLogger(__name__)

class TaskApplicationService:
    """任务应用服务 - 重构版本，集成新的执行能力"""
    
    def __init__(self):
        self.task_execution_service = TaskExecutionService()
        self.time_context_manager = TimeContextManager()
    
    def create_task(
        self, 
        db: Session,
        user_id: str,
        name: str,
        template_id: str,
        data_source_id: str,
        report_period: ReportPeriod = ReportPeriod.MONTHLY,
        description: Optional[str] = None,
        schedule: Optional[str] = None,
        recipients: Optional[List[str]] = None,
        is_active: bool = True,
        processing_mode: ProcessingMode = ProcessingMode.INTELLIGENT,
        workflow_type: AgentWorkflowType = AgentWorkflowType.SIMPLE_REPORT,
        max_context_tokens: int = 32000,
        enable_compression: bool = True
    ) -> Task:
        """
        创建新任务
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            name: 任务名称
            template_id: 模板ID
            data_source_id: 数据源ID
            report_period: 报告周期
            description: 任务描述
            schedule: 调度表达式
            recipients: 通知邮箱列表
            is_active: 是否启用
            processing_mode: 处理模式
            workflow_type: Agent工作流类型
            max_context_tokens: 最大上下文令牌数
            enable_compression: 是否启用压缩
            
        Returns:
            Task: 创建的任务对象
        """
        try:
            # 验证用户存在
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise NotFoundError(f"User {user_id} not found")
            
            # 验证模板存在
            template = db.query(Template).filter(Template.id == template_id).first()
            if not template:
                raise NotFoundError(f"Template {template_id} not found")
                
            # 验证数据源存在
            data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
            if not data_source:
                raise NotFoundError(f"DataSource {data_source_id} not found")
            
            # 验证调度表达式（如果提供）
            if schedule:
                try:
                    from croniter import croniter
                    if not croniter.is_valid(schedule):
                        raise ValidationError(f"Invalid cron expression: {schedule}")
                except ImportError:
                    logger.warning("croniter not available, skipping cron validation")
            
            # 创建任务
            task = Task(
                name=name,
                description=description,
                owner_id=user_id,
                template_id=template_id,
                data_source_id=data_source_id,
                report_period=report_period,
                schedule=schedule,
                recipients=recipients or [],
                is_active=is_active,
                status=TaskStatus.PENDING,
                processing_mode=processing_mode,
                workflow_type=workflow_type,
                max_context_tokens=max_context_tokens,
                enable_compression=enable_compression
            )
            
            db.add(task)
            db.commit()
            db.refresh(task)
            
            logger.info(f"Task created successfully: {task.id}")
            
            # 异步验证模板占位符（可选）
            if is_active:
                try:
                    validate_placeholders_task.delay(
                        template_id=template_id,
                        data_source_id=data_source_id,
                        user_id=user_id
                    )
                    logger.info(f"Placeholder validation task queued for task {task.id}")
                except Exception as e:
                    logger.error(f"Failed to queue placeholder validation for task {task.id}: {e}")
            
            return task
            
        except Exception as e:
            logger.error(f"Failed to create task: {str(e)}")
            db.rollback()
            raise
    
    def execute_task_immediately(
        self, 
        db: Session, 
        task_id: int,
        user_id: str,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        立即执行任务
        
        Args:
            db: 数据库会话
            task_id: 任务ID
            user_id: 执行用户ID
            execution_context: 执行上下文
            
        Returns:
            Dict: 执行结果信息
        """
        try:
            # 验证任务存在和权限
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            if not task:
                raise NotFoundError(f"Task {task_id} not found or access denied")
            
            if not task.is_active:
                raise ValidationError(f"Task {task_id} is not active")
            
            # 检查是否有正在进行的执行
            ongoing_execution = db.query(TaskExecution).filter(
                TaskExecution.task_id == task_id,
                TaskExecution.execution_status.in_([TaskStatus.PENDING, TaskStatus.PROCESSING])
            ).first()
            
            if ongoing_execution:
                return {
                    "status": "already_running",
                    "message": f"Task {task_id} is already being executed",
                    "execution_id": str(ongoing_execution.execution_id)
                }
            
            # 构建执行上下文
            context = execution_context or {}
            context.update({
                "trigger": "manual",
                "triggered_by": user_id,
                "triggered_at": datetime.utcnow().isoformat()
            })
            
            # 提交Celery任务
            celery_result = execute_report_task.delay(task_id, context)
            
            logger.info(f"Task {task_id} execution queued with Celery task ID: {celery_result.id}")
            
            return {
                "status": "queued",
                "message": f"Task {task_id} has been queued for execution",
                "celery_task_id": celery_result.id,
                "task_id": task_id
            }
            
        except Exception as e:
            logger.error(f"Failed to execute task {task_id}: {str(e)}")
            raise
    
    def get_task_status(
        self, 
        db: Session, 
        task_id: int, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        获取任务执行状态
        
        Args:
            db: 数据库会话
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            Dict: 任务状态信息
        """
        try:
            # 验证任务存在和权限
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            if not task:
                raise NotFoundError(f"Task {task_id} not found or access denied")
            
            # 获取最新的执行记录
            latest_execution = db.query(TaskExecution).filter(
                TaskExecution.task_id == task_id
            ).order_by(TaskExecution.created_at.desc()).first()
            
            if not latest_execution:
                return {
                    "task_id": task_id,
                    "status": task.status.value,
                    "message": "No executions found",
                    "progress": 0
                }
            
            # 获取Celery任务状态（如果存在）
            celery_status = None
            celery_info = {}
            if latest_execution.celery_task_id:
                try:
                    celery_result = AsyncResult(latest_execution.celery_task_id, app=celery_app)
                    celery_status = celery_result.status
                    if celery_result.info:
                        celery_info = celery_result.info
                except Exception as e:
                    logger.warning(f"Failed to get Celery status for task {latest_execution.celery_task_id}: {e}")
            
            return {
                "task_id": task_id,
                "execution_id": str(latest_execution.execution_id),
                "status": latest_execution.execution_status.value,
                "progress": latest_execution.progress_percentage,
                "current_step": latest_execution.current_step,
                "started_at": latest_execution.started_at.isoformat() if latest_execution.started_at else None,
                "completed_at": latest_execution.completed_at.isoformat() if latest_execution.completed_at else None,
                "duration": latest_execution.total_duration,
                "error_details": latest_execution.error_details,
                "celery_status": celery_status,
                "celery_info": celery_info,
                "execution_result": latest_execution.execution_result
            }
            
        except Exception as e:
            logger.error(f"Failed to get task status for task {task_id}: {str(e)}")
            raise
    
    def get_task_executions(
        self,
        db: Session,
        task_id: int,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取任务执行历史
        
        Args:
            db: 数据库会话
            task_id: 任务ID
            user_id: 用户ID
            limit: 返回记录数量限制
            
        Returns:
            List[Dict]: 执行历史列表
        """
        try:
            # 验证任务存在和权限
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            if not task:
                raise NotFoundError(f"Task {task_id} not found or access denied")
            
            # 获取执行历史
            executions = db.query(TaskExecution).filter(
                TaskExecution.task_id == task_id
            ).order_by(TaskExecution.created_at.desc()).limit(limit).all()
            
            return [
                {
                    "execution_id": str(execution.execution_id),
                    "status": execution.execution_status.value,
                    "progress": execution.progress_percentage,
                    "started_at": execution.started_at.isoformat() if execution.started_at else None,
                    "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                    "duration": execution.total_duration,
                    "error_details": execution.error_details,
                    "current_step": execution.current_step,
                    "workflow_type": execution.workflow_type.value if execution.workflow_type else None,
                    "created_at": execution.created_at.isoformat()
                }
                for execution in executions
            ]
            
        except Exception as e:
            logger.error(f"Failed to get task executions for task {task_id}: {str(e)}")
            raise
    
    def update_task(
        self,
        db: Session,
        task_id: int,
        user_id: str,
        **update_data
    ) -> Task:
        """
        更新任务
        
        Args:
            db: 数据库会话
            task_id: 任务ID
            user_id: 用户ID
            **update_data: 更新数据
            
        Returns:
            Task: 更新后的任务对象
        """
        try:
            # 验证任务存在和权限
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            if not task:
                raise NotFoundError(f"Task {task_id} not found or access denied")
            
            # 过滤允许更新的字段
            allowed_fields = {
                'name', 'description', 'schedule', 'report_period', 
                'recipients', 'is_active'
            }
            
            for field, value in update_data.items():
                if field in allowed_fields:
                    setattr(task, field, value)
            
            task.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(task)
            
            logger.info(f"Task {task_id} updated successfully")
            return task
            
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {str(e)}")
            db.rollback()
            raise
    
    def delete_task(
        self,
        db: Session,
        task_id: int,
        user_id: str
    ) -> bool:
        """
        删除任务
        
        Args:
            db: 数据库会话
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            # 验证任务存在和权限
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            if not task:
                raise NotFoundError(f"Task {task_id} not found or access denied")
            
            # 取消正在进行的执行
            ongoing_executions = db.query(TaskExecution).filter(
                TaskExecution.task_id == task_id,
                TaskExecution.execution_status.in_([TaskStatus.PENDING, TaskStatus.PROCESSING])
            ).all()
            
            for execution in ongoing_executions:
                if execution.celery_task_id:
                    try:
                        celery_app.control.revoke(execution.celery_task_id, terminate=True)
                        logger.info(f"Revoked Celery task {execution.celery_task_id}")
                    except Exception as e:
                        logger.warning(f"Failed to revoke Celery task {execution.celery_task_id}: {e}")
                
                execution.execution_status = TaskStatus.CANCELLED
                execution.completed_at = datetime.utcnow()
            
            # 删除任务（级联删除执行记录）
            db.delete(task)
            db.commit()
            
            logger.info(f"Task {task_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {str(e)}")
            db.rollback()
            raise
    
    def schedule_task(
        self,
        db: Session,
        task_id: int,
        schedule: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        设置任务调度
        
        Args:
            db: 数据库会话
            task_id: 任务ID
            schedule: Cron表达式
            user_id: 用户ID
            
        Returns:
            Dict: 调度结果
        """
        try:
            # 验证任务存在和权限
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            if not task:
                raise NotFoundError(f"Task {task_id} not found or access denied")
            
            # 验证Cron表达式
            try:
                from croniter import croniter
                if not croniter.is_valid(schedule):
                    raise ValidationError(f"Invalid cron expression: {schedule}")
            except ImportError:
                logger.warning("croniter not available, skipping cron validation")
            
            # 更新调度
            task.schedule = schedule
            task.updated_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Task {task_id} schedule updated to: {schedule}")
            
            return {
                "task_id": task_id,
                "schedule": schedule,
                "status": "scheduled",
                "message": "Task schedule updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to schedule task {task_id}: {str(e)}")
            db.rollback()
            raise
    
    def validate_task_configuration(
        self,
        db: Session,
        task_id: int,
        user_id: str
    ) -> Dict[str, Any]:
        """
        验证任务配置（包括占位符）
        
        Args:
            db: 数据库会话
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            Dict: 验证结果
        """
        try:
            # 验证任务存在和权限
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            if not task:
                raise NotFoundError(f"Task {task_id} not found or access denied")
            
            # 异步验证占位符
            validation_result = validate_placeholders_task.delay(
                template_id=str(task.template_id),
                data_source_id=str(task.data_source_id),
                user_id=user_id
            )
            
            logger.info(f"Validation task queued for task {task_id}: {validation_result.id}")
            
            return {
                "task_id": task_id,
                "validation_task_id": validation_result.id,
                "status": "validation_queued",
                "message": "Task validation has been queued"
            }
            
        except Exception as e:
            logger.error(f"Failed to validate task {task_id}: {str(e)}")
            raise

logger.info("✅ Task Application Service loaded")