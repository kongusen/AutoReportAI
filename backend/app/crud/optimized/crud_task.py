"""
优化的任务CRUD操作
"""

from typing import List, Optional, Union
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.crud.base_optimized import CRUDComplete
from app.models.optimized.task import Task, TaskType, TaskStatus, TaskPriority
from app.schemas.task import TaskCreate, TaskUpdate


class CRUDTask(CRUDComplete[Task, TaskCreate, TaskUpdate]):
    """任务CRUD操作类"""
    
    def __init__(self):
        super().__init__(Task, search_fields=["name", "description"])
    
    def get_by_status(
        self,
        db: Session,
        *,
        status: TaskStatus,
        user_id: Union[UUID, str] = None
    ) -> List[Task]:
        """根据状态获取任务"""
        query = db.query(self.model).filter(
            self.model.status == status,
            self.model.is_deleted == False
        )
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        return query.order_by(desc(self.model.created_at)).all()
    
    def get_active_tasks(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None
    ) -> List[Task]:
        """获取活跃任务"""
        active_statuses = [
            TaskStatus.PENDING,
            TaskStatus.QUEUED,
            TaskStatus.RUNNING,
            TaskStatus.PAUSED
        ]
        
        query = db.query(self.model).filter(
            self.model.status.in_(active_statuses),
            self.model.is_deleted == False
        )
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        return query.order_by(
            self.model.priority.desc(),
            self.model.created_at
        ).all()
    
    def get_by_type(
        self,
        db: Session,
        *,
        task_type: TaskType,
        user_id: Union[UUID, str] = None,
        status: TaskStatus = None
    ) -> List[Task]:
        """根据类型获取任务"""
        query = db.query(self.model).filter(
            self.model.task_type == task_type,
            self.model.is_deleted == False
        )
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        if status:
            query = query.filter(self.model.status == status)
        
        return query.order_by(desc(self.model.created_at)).all()
    
    def get_by_priority(
        self,
        db: Session,
        *,
        priority: TaskPriority,
        user_id: Union[UUID, str] = None
    ) -> List[Task]:
        """根据优先级获取任务"""
        query = db.query(self.model).filter(
            self.model.priority == priority,
            self.model.is_deleted == False
        )
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        return query.order_by(desc(self.model.created_at)).all()
    
    def get_running_tasks(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None
    ) -> List[Task]:
        """获取正在运行的任务"""
        query = db.query(self.model).filter(
            self.model.status == TaskStatus.RUNNING,
            self.model.is_deleted == False
        )
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        return query.all()
    
    def get_failed_tasks(
        self,
        db: Session,
        *,
        can_retry: bool = None,
        user_id: Union[UUID, str] = None
    ) -> List[Task]:
        """获取失败的任务"""
        query = db.query(self.model).filter(
            self.model.status == TaskStatus.FAILED,
            self.model.is_deleted == False
        )
        
        if can_retry is not None:
            if can_retry:
                query = query.filter(self.model.retry_count < self.model.max_retries)
            else:
                query = query.filter(self.model.retry_count >= self.model.max_retries)
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        return query.order_by(desc(self.model.created_at)).all()
    
    def get_next_pending_tasks(
        self,
        db: Session,
        *,
        limit: int = 10,
        priority_order: bool = True
    ) -> List[Task]:
        """获取下一批待处理任务"""
        query = db.query(self.model).filter(
            self.model.status == TaskStatus.PENDING,
            self.model.is_deleted == False
        )
        
        if priority_order:
            # 按优先级排序
            priority_mapping = {
                TaskPriority.CRITICAL: 5,
                TaskPriority.URGENT: 4,
                TaskPriority.HIGH: 3,
                TaskPriority.MEDIUM: 2,
                TaskPriority.LOW: 1
            }
            query = query.order_by(
                desc(self.model.priority),
                self.model.created_at
            )
        else:
            query = query.order_by(self.model.created_at)
        
        return query.limit(limit).all()
    
    def update_progress(
        self,
        db: Session,
        *,
        task_id: Union[UUID, str],
        progress: int = None,
        current_step: str = None,
        completed_steps: int = None
    ) -> Optional[Task]:
        """更新任务进度"""
        task = self.get(db, id=task_id)
        if not task:
            return None
        
        task.update_progress(progress, current_step, completed_steps)
        
        db.add(task)
        db.commit()
        db.refresh(task)
        
        return task
    
    def start_task(
        self,
        db: Session,
        *,
        task_id: Union[UUID, str]
    ) -> Optional[Task]:
        """开始执行任务"""
        task = self.get(db, id=task_id)
        if not task:
            return None
        
        if not task.is_active:
            return None
        
        task.start_execution()
        
        db.add(task)
        db.commit()
        db.refresh(task)
        
        return task
    
    def complete_task(
        self,
        db: Session,
        *,
        task_id: Union[UUID, str],
        success: bool = True,
        result: str = None,
        error_message: str = None
    ) -> Optional[Task]:
        """完成任务执行"""
        task = self.get(db, id=task_id)
        if not task:
            return None
        
        task.complete_execution(success, result, error_message)
        
        db.add(task)
        db.commit()
        db.refresh(task)
        
        return task
    
    def cancel_task(
        self,
        db: Session,
        *,
        task_id: Union[UUID, str],
        reason: str = None
    ) -> Optional[Task]:
        """取消任务"""
        task = self.get(db, id=task_id)
        if not task:
            return None
        
        task.cancel_task(reason)
        
        db.add(task)
        db.commit()
        db.refresh(task)
        
        return task
    
    def get_task_statistics(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None,
        days: int = 30
    ) -> dict:
        """获取任务统计信息"""
        from datetime import datetime, timedelta
        
        base_query = db.query(self.model).filter(self.model.is_deleted == False)
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            base_query = base_query.filter(self.model.user_id == user_id)
        
        # 最近N天的任务
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        recent_query = base_query.filter(self.model.created_at >= cutoff_date)
        
        stats = {
            "total": base_query.count(),
            "recent": recent_query.count(),
            "active": base_query.filter(
                self.model.status.in_([
                    TaskStatus.PENDING, TaskStatus.QUEUED, 
                    TaskStatus.RUNNING, TaskStatus.PAUSED
                ])
            ).count(),
            "completed": base_query.filter(
                self.model.status.in_([
                    TaskStatus.SUCCESS, TaskStatus.FAILED, 
                    TaskStatus.CANCELLED, TaskStatus.TIMEOUT
                ])
            ).count(),
            "by_status": {},
            "by_type": {},
            "by_priority": {}
        }
        
        # 按状态统计
        for status in TaskStatus:
            count = base_query.filter(self.model.status == status).count()
            if count > 0:
                stats["by_status"][status.value] = count
        
        # 按类型统计
        for task_type in TaskType:
            count = base_query.filter(self.model.task_type == task_type).count()
            if count > 0:
                stats["by_type"][task_type.value] = count
        
        # 按优先级统计
        for priority in TaskPriority:
            count = base_query.filter(self.model.priority == priority).count()
            if count > 0:
                stats["by_priority"][priority.value] = count
        
        return stats
    
    def get_performance_summary(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None
    ) -> dict:
        """获取任务性能摘要"""
        base_query = db.query(self.model).filter(self.model.is_deleted == False)
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            base_query = base_query.filter(self.model.user_id == user_id)
        
        # 已完成的任务
        completed_tasks = base_query.filter(
            self.model.status.in_([TaskStatus.SUCCESS, TaskStatus.FAILED]),
            self.model.actual_duration.isnot(None)
        ).all()
        
        if not completed_tasks:
            return {
                "total_completed": 0,
                "success_rate": 0,
                "avg_execution_time": 0,
                "avg_efficiency": 0
            }
        
        successful_tasks = [t for t in completed_tasks if t.status == TaskStatus.SUCCESS]
        total_execution_time = sum(t.actual_duration for t in completed_tasks)
        
        avg_efficiency = sum(t.execution_efficiency for t in completed_tasks) / len(completed_tasks)
        
        return {
            "total_completed": len(completed_tasks),
            "success_rate": round((len(successful_tasks) / len(completed_tasks)) * 100, 2),
            "avg_execution_time": round(total_execution_time / len(completed_tasks), 2),
            "avg_efficiency": round(avg_efficiency, 2),
            "successful_tasks": len(successful_tasks),
            "failed_tasks": len(completed_tasks) - len(successful_tasks)
        }


# 创建CRUD实例
crud_task = CRUDTask()