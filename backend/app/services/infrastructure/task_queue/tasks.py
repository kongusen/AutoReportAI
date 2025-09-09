"""
Infrastructure层 - Celery任务定义

基于DDD架构的Celery任务定义，使用新的TaskExecutionService能力
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from celery import Task as CeleryTask
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.task import Task, TaskExecution, TaskStatus
from app.services.application.tasks.task_execution_service import TaskExecutionService
from app.services.infrastructure.task_queue.celery_config import celery_app
from app.services.infrastructure.notification.notification_service import NotificationService
from celery.schedules import crontab

logger = logging.getLogger(__name__)

class DatabaseTask(CeleryTask):
    """带数据库会话的基础任务类"""
    
    def __call__(self, *args, **kwargs):
        """执行任务时自动管理数据库会话"""
        with SessionLocal() as db:
            return self.run_with_db(db, *args, **kwargs)
    
    def run_with_db(self, db: Session, *args, **kwargs):
        """子类需要实现的方法"""
        return self.run(*args, **kwargs)

@celery_app.task(bind=True, base=DatabaseTask, name='tasks.infrastructure.execute_report_task')
def execute_report_task(self, db: Session, task_id: int, execution_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    执行报告生成任务 - 使用新的TaskExecutionService
    
    Args:
        task_id: 任务ID
        execution_context: 执行上下文（可选）
    
    Returns:
        Dict: 执行结果
    """
    task_execution_id = None
    notification_service = NotificationService()
    
    try:
        # 1. 获取任务信息
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        if not task.is_active:
            logger.info(f"Task {task_id} is not active, skipping execution")
            return {"status": "skipped", "reason": "task_inactive"}
        
        # 2. 创建任务执行记录
        task_execution = TaskExecution(
            task_id=task_id,
            execution_status=TaskStatus.PROCESSING,
            workflow_type=task.workflow_type,
            started_at=datetime.utcnow(),
            celery_task_id=self.request.id,
            execution_context=execution_context or {},
            progress_percentage=0
        )
        db.add(task_execution)
        db.commit()
        task_execution_id = task_execution.id
        
        # 3. 更新任务状态
        task.status = TaskStatus.PROCESSING
        task.execution_count += 1
        task.last_execution_at = datetime.utcnow()
        db.commit()
        
        # 4. 初始化TaskExecutionService
        task_execution_service = TaskExecutionService()
        
        # 5. 准备执行参数
        execution_params = {
            "task_id": task_id,
            "template_id": str(task.template_id),
            "data_source_id": str(task.data_source_id),
            "report_period": task.report_period.value if task.report_period else "monthly",
            "user_id": str(task.owner_id),
            "execution_id": str(task_execution.execution_id),
            "recipients": task.recipients or [],
            "schedule": task.schedule
        }
        
        # 6. 使用新的TaskExecutionService执行完整流程
        logger.info(f"Starting task execution for task {task_id} with TaskExecutionService")
        
        def progress_callback(progress: int, message: str, current_step: str = None):
            """进度回调函数"""
            task_execution.progress_percentage = progress
            task_execution.current_step = current_step or message
            task_execution.updated_at = datetime.utcnow()
            db.commit()
            
            # 发送WebSocket进度更新
            self.update_state(
                state='PROGRESS',
                meta={
                    'progress': progress,
                    'status': 'processing',
                    'message': message,
                    'current_step': current_step,
                    'task_id': task_id
                }
            )
        
        # 执行完整的任务流程
        execution_result = task_execution_service.execute_complete_task_flow(
            execution_params,
            progress_callback=progress_callback
        )
        
        # 7. 更新执行结果
        task_execution.execution_status = TaskStatus.COMPLETED
        task_execution.completed_at = datetime.utcnow()
        task_execution.total_duration = int((task_execution.completed_at - task_execution.started_at).total_seconds())
        task_execution.execution_result = execution_result
        task_execution.progress_percentage = 100
        
        # 更新任务统计
        task.status = TaskStatus.COMPLETED
        task.success_count += 1
        task.last_execution_duration = task_execution.total_duration
        
        # 更新平均执行时间
        if task.average_execution_time == 0:
            task.average_execution_time = task_execution.total_duration
        else:
            task.average_execution_time = (task.average_execution_time + task_execution.total_duration) / 2
        
        db.commit()
        
        # 8. 发送成功通知
        if task.recipients:
            try:
                notification_service.send_task_completion_notification(
                    task_id=task_id,
                    task_name=task.name,
                    recipients=task.recipients,
                    execution_result=execution_result,
                    success=True
                )
            except Exception as e:
                logger.error(f"Failed to send success notification for task {task_id}: {e}")
        
        logger.info(f"Task {task_id} completed successfully in {task_execution.total_duration}s")
        
        return {
            "status": "completed",
            "task_id": task_id,
            "execution_id": str(task_execution.execution_id),
            "execution_time": task_execution.total_duration,
            "result": execution_result
        }
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}", exc_info=True)
        
        # 更新失败状态
        if task_execution_id:
            task_execution = db.query(TaskExecution).filter(TaskExecution.id == task_execution_id).first()
            if task_execution:
                task_execution.execution_status = TaskStatus.FAILED
                task_execution.completed_at = datetime.utcnow()
                task_execution.error_details = str(e)
                task_execution.total_duration = int((task_execution.completed_at - task_execution.started_at).total_seconds()) if task_execution.started_at else 0
        
        # 更新任务统计
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = TaskStatus.FAILED
            task.failure_count += 1
            
        db.commit()
        
        # 发送失败通知
        if task and task.recipients:
            try:
                notification_service.send_task_completion_notification(
                    task_id=task_id,
                    task_name=task.name,
                    recipients=task.recipients,
                    execution_result={"error": str(e)},
                    success=False
                )
            except Exception as notification_error:
                logger.error(f"Failed to send failure notification for task {task_id}: {notification_error}")
        
        # 重新抛出异常让Celery处理重试
        raise

@celery_app.task(bind=True, name='tasks.infrastructure.validate_placeholders_task')
def validate_placeholders_task(self, template_id: str, data_source_id: str, user_id: str) -> Dict[str, Any]:
    """
    验证模板占位符任务
    
    Args:
        template_id: 模板ID
        data_source_id: 数据源ID
        user_id: 用户ID
    
    Returns:
        Dict: 验证结果
    """
    try:
        task_execution_service = TaskExecutionService()
        
        logger.info(f"Starting placeholder validation for template {template_id}")
        
        # 使用TaskExecutionService进行占位符验证
        validation_result = task_execution_service.validate_all_placeholders(
            template_id=template_id,
            data_source_id=data_source_id,
            user_id=user_id
        )
        
        logger.info(f"Placeholder validation completed for template {template_id}")
        
        return {
            "status": "completed",
            "template_id": template_id,
            "validation_result": validation_result
        }
        
    except Exception as e:
        logger.error(f"Placeholder validation failed for template {template_id}: {str(e)}", exc_info=True)
        raise

@celery_app.task(bind=True, base=DatabaseTask, name='tasks.infrastructure.scheduled_task_runner')
def scheduled_task_runner(self, db: Session, task_id: int) -> Dict[str, Any]:
    """
    定时任务执行器 - 由调度器触发
    
    Args:
        task_id: 任务ID
    
    Returns:
        Dict: 执行结果
    """
    try:
        # 检查任务是否应该执行
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task or not task.is_active:
            return {"status": "skipped", "reason": "task_inactive_or_not_found"}
        
        # 检查是否有正在进行的执行
        ongoing_execution = db.query(TaskExecution).filter(
            TaskExecution.task_id == task_id,
            TaskExecution.execution_status.in_([TaskStatus.PENDING, TaskStatus.PROCESSING])
        ).first()
        
        if ongoing_execution:
            logger.warning(f"Task {task_id} has ongoing execution, skipping")
            return {"status": "skipped", "reason": "execution_in_progress"}
        
        # 构建执行上下文（包含调度信息）
        execution_context = {
            "trigger": "scheduled",
            "schedule": task.schedule,
            "triggered_at": datetime.utcnow().isoformat()
        }
        
        # 委托给主执行任务
        result = execute_report_task.delay(task_id, execution_context)
        
        logger.info(f"Scheduled task {task_id} delegated to execution task {result.id}")
        
        return {
            "status": "delegated",
            "task_id": task_id,
            "execution_task_id": result.id
        }
        
    except Exception as e:
        logger.error(f"Scheduled task runner failed for task {task_id}: {str(e)}", exc_info=True)
        raise

@celery_app.task(name='tasks.infrastructure.cleanup_old_executions')
def cleanup_old_executions(days_to_keep: int = 30) -> Dict[str, Any]:
    """
    清理旧的任务执行记录
    
    Args:
        days_to_keep: 保留天数，默认30天
    
    Returns:
        Dict: 清理结果
    """
    try:
        with SessionLocal() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # 删除旧的执行记录
            deleted_count = db.query(TaskExecution).filter(
                TaskExecution.created_at < cutoff_date,
                TaskExecution.execution_status.in_([TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED])
            ).delete()
            
            db.commit()
            
            logger.info(f"Cleaned up {deleted_count} old task executions")
            
            return {
                "status": "completed",
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date.isoformat()
            }
            
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}", exc_info=True)
        raise

# 注册周期性任务
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """设置周期性任务"""
    
    # 每天凌晨2点清理旧的执行记录
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        cleanup_old_executions.s(),
        name='cleanup_old_executions_daily',
    )
    
    logger.info("✅ Periodic tasks configured")

logger.info("✅ Task infrastructure layer loaded")