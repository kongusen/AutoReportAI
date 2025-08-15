"""
TaskExecution CRUD操作
支持Agent编排的任务执行记录管理
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from app.crud.base import CRUDBase
from app.models.task import TaskExecution, TaskStatus, AgentWorkflowType
from app.schemas.task import TaskExecutionCreate, TaskExecutionUpdate


class CRUDTaskExecution(CRUDBase[TaskExecution, TaskExecutionCreate, TaskExecutionUpdate]):
    """TaskExecution CRUD操作类"""
    
    def create_execution(
        self,
        db: Session,
        *,
        task_id: int,
        workflow_type: AgentWorkflowType = AgentWorkflowType.SIMPLE_REPORT,
        execution_context: Optional[Dict[str, Any]] = None,
        celery_task_id: Optional[str] = None
    ) -> TaskExecution:
        """创建新的任务执行记录"""
        execution = TaskExecution(
            task_id=task_id,
            execution_status=TaskStatus.PENDING,
            workflow_type=workflow_type,
            execution_context=execution_context or {},
            celery_task_id=celery_task_id,
            started_at=datetime.utcnow(),
            progress_percentage=0
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)
        return execution
    
    def update_execution_status(
        self,
        db: Session,
        *,
        execution_id: int,
        status: TaskStatus,
        progress_percentage: Optional[int] = None,
        current_step: Optional[str] = None,
        error_details: Optional[str] = None
    ) -> Optional[TaskExecution]:
        """更新执行状态"""
        execution = db.query(TaskExecution).filter(TaskExecution.id == execution_id).first()
        if not execution:
            return None
        
        execution.execution_status = status
        if progress_percentage is not None:
            execution.progress_percentage = progress_percentage
        if current_step:
            execution.current_step = current_step
        if error_details:
            execution.error_details = error_details
        
        # 如果任务完成或失败，设置完成时间
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            execution.completed_at = datetime.utcnow()
            if execution.started_at:
                execution.total_duration = int(
                    (execution.completed_at - execution.started_at).total_seconds()
                )
        
        db.commit()
        db.refresh(execution)
        return execution
    
    def update_execution_result(
        self,
        db: Session,
        *,
        execution_id: int,
        execution_result: Dict[str, Any],
        output_artifacts: Optional[Dict[str, Any]] = None,
        agent_execution_times: Optional[Dict[str, Any]] = None
    ) -> Optional[TaskExecution]:
        """更新执行结果"""
        execution = db.query(TaskExecution).filter(TaskExecution.id == execution_id).first()
        if not execution:
            return None
        
        execution.execution_result = execution_result
        if output_artifacts:
            execution.output_artifacts = output_artifacts
        if agent_execution_times:
            execution.agent_execution_times = agent_execution_times
        
        db.commit()
        db.refresh(execution)
        return execution
    
    def get_by_task_id(
        self,
        db: Session,
        *,
        task_id: int,
        limit: int = 100,
        skip: int = 0
    ) -> List[TaskExecution]:
        """获取特定任务的执行记录"""
        return (
            db.query(TaskExecution)
            .filter(TaskExecution.task_id == task_id)
            .order_by(desc(TaskExecution.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_celery_task_id(
        self,
        db: Session,
        celery_task_id: str
    ) -> Optional[TaskExecution]:
        """根据Celery任务ID获取执行记录"""
        return (
            db.query(TaskExecution)
            .filter(TaskExecution.celery_task_id == celery_task_id)
            .first()
        )
    
    def get_running_executions(
        self,
        db: Session,
        limit: int = 100
    ) -> List[TaskExecution]:
        """获取正在运行的执行记录"""
        running_statuses = [
            TaskStatus.PENDING,
            TaskStatus.PROCESSING,
            TaskStatus.AGENT_ORCHESTRATING,
            TaskStatus.GENERATING
        ]
        return (
            db.query(TaskExecution)
            .filter(TaskExecution.execution_status.in_(running_statuses))
            .order_by(TaskExecution.created_at)
            .limit(limit)
            .all()
        )
    
    def get_execution_stats(
        self,
        db: Session,
        *,
        task_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取执行统计信息"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = db.query(TaskExecution).filter(TaskExecution.created_at >= cutoff_date)
        if task_id:
            query = query.filter(TaskExecution.task_id == task_id)
        
        executions = query.all()
        
        total_count = len(executions)
        success_count = len([e for e in executions if e.execution_status == TaskStatus.COMPLETED])
        failed_count = len([e for e in executions if e.execution_status == TaskStatus.FAILED])
        
        # 计算平均执行时间
        completed_executions = [e for e in executions if e.total_duration is not None]
        avg_duration = (
            sum(e.total_duration for e in completed_executions) / len(completed_executions)
            if completed_executions else 0
        )
        
        # 统计工作流类型使用情况
        workflow_stats = {}
        for execution in executions:
            workflow_type = execution.workflow_type.value if execution.workflow_type else "unknown"
            workflow_stats[workflow_type] = workflow_stats.get(workflow_type, 0) + 1
        
        return {
            "total_executions": total_count,
            "successful_executions": success_count,
            "failed_executions": failed_count,
            "success_rate": success_count / total_count if total_count > 0 else 0,
            "average_duration_seconds": avg_duration,
            "workflow_type_distribution": workflow_stats,
            "period_days": days
        }
    
    def cleanup_old_executions(
        self,
        db: Session,
        *,
        days_to_keep: int = 90,
        max_records_per_task: int = 100
    ) -> int:
        """清理旧的执行记录"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # 获取需要清理的记录（保留每个任务最新的max_records_per_task条记录）
        subquery = (
            db.query(TaskExecution.id)
            .filter(TaskExecution.created_at < cutoff_date)
            .order_by(desc(TaskExecution.created_at))
            .subquery()
        )
        
        # 删除旧记录
        deleted_count = (
            db.query(TaskExecution)
            .filter(TaskExecution.created_at < cutoff_date)
            .delete(synchronize_session=False)
        )
        
        db.commit()
        return deleted_count


# 创建全局实例
crud_task_execution = CRUDTaskExecution(TaskExecution)