"""
优化的ETL作业CRUD操作
"""

from typing import List, Optional, Union
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.crud.base_optimized import CRUDComplete
from app.models.optimized.etl_job import ETLJob, ETLJobType, ETLJobStatus, ETLJobPriority
from app.schemas.etl_job import ETLJobCreate, ETLJobUpdate


class CRUDETLJob(CRUDComplete[ETLJob, ETLJobCreate, ETLJobUpdate]):
    """ETL作业CRUD操作类"""
    
    def __init__(self):
        super().__init__(ETLJob, search_fields=["name", "description"])
    
    def get_by_status(
        self,
        db: Session,
        *,
        status: ETLJobStatus,
        user_id: Union[UUID, str] = None
    ) -> List[ETLJob]:
        """根据状态获取ETL作业"""
        query = db.query(self.model).filter(
            self.model.status == status,
            self.model.is_deleted == False
        )
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        return query.all()
    
    def get_active_jobs(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None
    ) -> List[ETLJob]:
        """获取活跃的ETL作业"""
        active_statuses = [
            ETLJobStatus.PENDING,
            ETLJobStatus.RUNNING,
            ETLJobStatus.RETRYING
        ]
        
        query = db.query(self.model).filter(
            self.model.status.in_(active_statuses),
            self.model.is_deleted == False
        )
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        return query.all()
    
    def get_scheduled_jobs(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None
    ) -> List[ETLJob]:
        """获取已调度的ETL作业"""
        query = db.query(self.model).filter(
            self.model.is_scheduled == True,
            self.model.is_deleted == False
        )
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        return query.all()
    
    def get_by_data_source(
        self,
        db: Session,
        *,
        data_source_id: Union[UUID, str],
        user_id: Union[UUID, str] = None
    ) -> List[ETLJob]:
        """根据数据源获取ETL作业"""
        if isinstance(data_source_id, str):
            data_source_id = UUID(data_source_id)
        
        query = db.query(self.model).filter(
            self.model.data_source_id == data_source_id,
            self.model.is_deleted == False
        )
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        return query.all()
    
    def get_by_priority(
        self,
        db: Session,
        *,
        priority: ETLJobPriority,
        user_id: Union[UUID, str] = None
    ) -> List[ETLJob]:
        """根据优先级获取ETL作业"""
        query = db.query(self.model).filter(
            self.model.priority == priority,
            self.model.is_deleted == False
        ).order_by(desc(self.model.created_at))
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        return query.all()
    
    def get_failed_jobs(
        self,
        db: Session,
        *,
        can_retry: bool = None,
        user_id: Union[UUID, str] = None
    ) -> List[ETLJob]:
        """获取失败的ETL作业"""
        query = db.query(self.model).filter(
            self.model.status == ETLJobStatus.FAILED,
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
        
        return query.all()
    
    def record_execution(
        self,
        db: Session,
        *,
        job_id: Union[UUID, str],
        status: ETLJobStatus,
        execution_time: float,
        records_processed: int = 0,
        error_message: str = None,
        quality_score: float = None
    ) -> Optional[ETLJob]:
        """记录ETL作业执行结果"""
        job = self.get(db, id=job_id)
        if not job:
            return None
        
        job.record_execution(status, execution_time, records_processed, error_message)
        
        if quality_score is not None:
            job.quality_score = quality_score
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        return job
    
    def get_next_scheduled_jobs(
        self,
        db: Session,
        *,
        limit: int = 10
    ) -> List[ETLJob]:
        """获取下一批需要执行的调度作业"""
        from datetime import datetime
        
        current_time = datetime.utcnow().isoformat()
        
        return db.query(self.model).filter(
            self.model.is_scheduled == True,
            self.model.status.in_([ETLJobStatus.PENDING, ETLJobStatus.RETRYING]),
            self.model.next_run_time <= current_time,
            self.model.is_deleted == False
        ).order_by(
            self.model.priority.desc(),
            self.model.next_run_time
        ).limit(limit).all()
    
    def get_health_summary(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None
    ) -> dict:
        """获取ETL作业健康状况摘要"""
        base_query = db.query(self.model).filter(self.model.is_deleted == False)
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            base_query = base_query.filter(self.model.user_id == user_id)
        
        healthy_jobs = base_query.filter(
            self.model.success_count > 0,
            (self.model.success_count / (self.model.success_count + self.model.failure_count) * 100) >= 80
        ).count()
        
        total_jobs = base_query.count()
        
        summary = {
            "total_jobs": total_jobs,
            "healthy_jobs": healthy_jobs,
            "health_percentage": round((healthy_jobs / total_jobs * 100) if total_jobs > 0 else 0, 2),
            "by_status": {},
            "by_priority": {},
            "performance_grades": {}
        }
        
        # 按状态统计
        for status in ETLJobStatus:
            count = base_query.filter(self.model.status == status).count()
            if count > 0:
                summary["by_status"][status.value] = count
        
        # 按优先级统计
        for priority in ETLJobPriority:
            count = base_query.filter(self.model.priority == priority).count()
            if count > 0:
                summary["by_priority"][priority.value] = count
        
        return summary
    
    def get_performance_metrics(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None,
        days: int = 30
    ) -> dict:
        """获取ETL作业性能指标"""
        from datetime import datetime, timedelta
        
        base_query = db.query(self.model).filter(self.model.is_deleted == False)
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            base_query = base_query.filter(self.model.user_id == user_id)
        
        # 最近N天的作业
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        recent_jobs = base_query.filter(self.model.last_run_time >= cutoff_date).all()
        
        if not recent_jobs:
            return {
                "total_executions": 0,
                "avg_execution_time": 0,
                "success_rate": 0,
                "avg_quality_score": 0,
                "total_records_processed": 0
            }
        
        total_executions = sum(job.execution_count for job in recent_jobs)
        total_success = sum(job.success_count for job in recent_jobs)
        total_records = sum(job.processed_records for job in recent_jobs)
        
        avg_execution_time = sum(job.avg_execution_time for job in recent_jobs) / len(recent_jobs)
        avg_quality_score = sum(job.quality_score for job in recent_jobs) / len(recent_jobs)
        
        return {
            "total_executions": total_executions,
            "avg_execution_time": round(avg_execution_time, 2),
            "success_rate": round((total_success / total_executions * 100) if total_executions > 0 else 0, 2),
            "avg_quality_score": round(avg_quality_score, 2),
            "total_records_processed": total_records,
            "jobs_analyzed": len(recent_jobs)
        }


# 创建CRUD实例
crud_etl_job = CRUDETLJob()