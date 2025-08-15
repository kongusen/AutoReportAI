from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.crud.base import CRUDBase
from app.models.task import Task, TaskStatus, ProcessingMode, AgentWorkflowType
from app.schemas.task import TaskCreate, TaskUpdate


class CRUDTask(CRUDBase[Task, TaskCreate, TaskUpdate]):
    def get_multi_by_owner(
        self, db: Session, *, owner_id: int, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        return (
            db.query(self.model)
            .filter(self.model.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_active(self, db: Session) -> int:
        """Get count of active tasks."""
        return db.query(self.model).filter(self.model.status == "active").count()

    def count_completed(self, db: Session) -> int:
        """Get count of completed tasks."""
        return db.query(self.model).filter(self.model.status == "completed").count()

    def create_with_owner(self, db: Session, *, obj_in: TaskCreate, owner_id) -> Task:
        obj_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
        obj_data['owner_id'] = owner_id
        db_obj = Task(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_with_user(self, db: Session, *, obj_in: TaskCreate, user_id) -> Task:
        """创建任务，关联用户"""
        return self.create_with_owner(db, obj_in=obj_in, owner_id=user_id)
    
    def update_execution_stats(
        self,
        db: Session,
        *,
        task_id: int,
        success: bool,
        execution_time: Optional[float] = None
    ) -> Optional[Task]:
        """更新任务执行统计"""
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return None
        
        # 更新执行计数
        task.execution_count = (task.execution_count or 0) + 1
        if success:
            task.success_count = (task.success_count or 0) + 1
        else:
            task.failure_count = (task.failure_count or 0) + 1
        
        # 更新执行时间
        task.last_execution_at = datetime.utcnow()
        if execution_time is not None:
            task.last_execution_duration = execution_time
            # 更新平均执行时间
            if task.execution_count > 1:
                current_avg = task.average_execution_time or 0
                task.average_execution_time = (
                    (current_avg * (task.execution_count - 1) + execution_time) / task.execution_count
                )
            else:
                task.average_execution_time = execution_time
        
        db.commit()
        db.refresh(task)
        return task
    
    def update_status(
        self,
        db: Session,
        *,
        task_id: int,
        status: TaskStatus
    ) -> Optional[Task]:
        """更新任务状态"""
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return None
        
        task.status = status
        db.commit()
        db.refresh(task)
        return task
    
    def get_by_status(
        self,
        db: Session,
        *,
        status: TaskStatus,
        owner_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Task]:
        """根据状态获取任务"""
        query = db.query(Task).filter(Task.status == status)
        if owner_id:
            query = query.filter(Task.owner_id == owner_id)
        
        return query.offset(skip).limit(limit).all()
    
    def get_active_tasks(
        self,
        db: Session,
        *,
        owner_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Task]:
        """获取活跃的任务"""
        query = db.query(Task).filter(Task.is_active == True)
        if owner_id:
            query = query.filter(Task.owner_id == owner_id)
        
        return query.offset(skip).limit(limit).all()
    
    def get_tasks_for_scheduling(
        self,
        db: Session,
        limit: int = 100
    ) -> List[Task]:
        """获取需要调度的任务"""
        return (
            db.query(Task)
            .filter(
                and_(
                    Task.is_active == True,
                    Task.schedule.isnot(None),
                    Task.status.in_([TaskStatus.PENDING, TaskStatus.COMPLETED])
                )
            )
            .limit(limit)
            .all()
        )
    
    def get_task_performance_summary(
        self,
        db: Session,
        *,
        owner_id: Optional[UUID] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取任务性能摘要"""
        query = db.query(Task)
        if owner_id:
            query = query.filter(Task.owner_id == owner_id)
        
        # 只获取最近有执行记录的任务
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        tasks = query.filter(
            Task.last_execution_at >= cutoff_date
        ).all()
        
        if not tasks:
            return {
                "total_tasks": 0,
                "active_tasks": 0,
                "average_success_rate": 0.0,
                "average_execution_time": 0.0,
                "processing_mode_distribution": {},
                "workflow_type_distribution": {}
            }
        
        active_tasks = [t for t in tasks if t.is_active]
        total_executions = sum(t.execution_count or 0 for t in tasks)
        total_success = sum(t.success_count or 0 for t in tasks)
        
        # 处理模式分布
        processing_mode_dist = {}
        workflow_type_dist = {}
        
        for task in tasks:
            mode = task.processing_mode.value if task.processing_mode else "unknown"
            processing_mode_dist[mode] = processing_mode_dist.get(mode, 0) + 1
            
            workflow = task.workflow_type.value if task.workflow_type else "unknown"
            workflow_type_dist[workflow] = workflow_type_dist.get(workflow, 0) + 1
        
        # 平均执行时间
        execution_times = [t.average_execution_time for t in tasks if t.average_execution_time]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        return {
            "total_tasks": len(tasks),
            "active_tasks": len(active_tasks),
            "total_executions": total_executions,
            "average_success_rate": total_success / total_executions if total_executions > 0 else 0,
            "average_execution_time": avg_execution_time,
            "processing_mode_distribution": processing_mode_dist,
            "workflow_type_distribution": workflow_type_dist,
            "period_days": days
        }


crud_task = CRUDTask(Task)
