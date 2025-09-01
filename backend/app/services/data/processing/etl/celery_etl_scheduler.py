"""
基于Celery的ETL任务调度器

替代APScheduler，使用Celery Beat进行统一的任务调度
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from celery import current_app
from celery.schedules import crontab
from sqlalchemy.orm import Session

from app import crud
# 使用新的DDD架构Celery配置
from app.services.infrastructure.task_queue.celery_config import celery_app
from app.db.session import get_db_session

logger = logging.getLogger(__name__)


class ETLJobExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running" 
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CeleryETLScheduler:
    """基于Celery的ETL任务调度器"""
    
    def __init__(self):
        self.scheduled_jobs: Dict[str, Dict[str, Any]] = {}
        
    def schedule_job(self, job_id: str, cron_expression: str, job_config: Dict[str, Any]) -> bool:
        """
        调度ETL作业
        
        Args:
            job_id: 作业ID
            cron_expression: Cron表达式 (格式: "minute hour day month day_of_week")
            job_config: 作业配置
            
        Returns:
            调度是否成功
        """
        try:
            # 解析cron表达式
            cron_parts = cron_expression.split()
            if len(cron_parts) != 5:
                raise ValueError(f"Invalid cron expression: {cron_expression}")
                
            minute, hour, day, month, day_of_week = cron_parts
            
            # 创建Celery crontab调度
            schedule = crontab(
                minute=minute,
                hour=hour,
                day_of_month=day,
                month_of_year=month, 
                day_of_week=day_of_week
            )
            
            # 注册到Celery Beat
            task_name = f"etl_job_{job_id}"
            
            # 确保 beat_schedule 存在
            if not hasattr(celery_app.conf, 'beat_schedule') or celery_app.conf.beat_schedule is None:
                celery_app.conf.beat_schedule = {}
            
            celery_app.conf.beat_schedule[task_name] = {
                'task': 'app.services.application.task_management.core.worker.tasks.basic_tasks.execute_etl_job',
                'schedule': schedule,
                'args': (job_id, job_config)
            }
            
            # 记录调度信息
            self.scheduled_jobs[job_id] = {
                'task_name': task_name,
                'cron_expression': cron_expression,
                'job_config': job_config,
                'scheduled_at': datetime.utcnow(),
                'status': 'scheduled'
            }
            
            logger.info(f"ETL作业 {job_id} 已调度: {cron_expression}")
            return True
            
        except Exception as e:
            logger.error(f"ETL作业调度失败 {job_id}: {str(e)}")
            return False
    
    def unschedule_job(self, job_id: str) -> bool:
        """
        取消调度ETL作业
        
        Args:
            job_id: 作业ID
            
        Returns:
            取消调度是否成功
        """
        try:
            if job_id in self.scheduled_jobs:
                task_name = self.scheduled_jobs[job_id]['task_name']
                
                # 从Celery Beat中移除
                if (hasattr(celery_app.conf, 'beat_schedule') and 
                    celery_app.conf.beat_schedule is not None and
                    task_name in celery_app.conf.beat_schedule):
                    del celery_app.conf.beat_schedule[task_name]
                
                # 从本地记录中移除
                del self.scheduled_jobs[job_id]
                
                logger.info(f"ETL作业 {job_id} 调度已取消")
                return True
            else:
                logger.warning(f"ETL作业 {job_id} 未找到调度记录")
                return False
                
        except Exception as e:
            logger.error(f"取消ETL作业调度失败 {job_id}: {str(e)}")
            return False
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        获取作业状态
        
        Args:
            job_id: 作业ID
            
        Returns:
            作业状态信息
        """
        if job_id in self.scheduled_jobs:
            job_info = self.scheduled_jobs[job_id].copy()
            
            # 检查最近的执行状态
            task_name = job_info['task_name']
            # 这里可以添加从Celery结果后端查询最近执行状态的逻辑
            
            return job_info
        
        return None
    
    def list_scheduled_jobs(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有已调度的作业
        
        Returns:
            所有调度作业的信息
        """
        return self.scheduled_jobs.copy()
    
    def load_jobs_from_database(self) -> int:
        """
        从数据库加载ETL作业并进行调度
        
        Returns:
            成功调度的作业数量
        """
        try:
            with get_db_session() as db:
                # 获取所有启用的ETL作业
                etl_jobs = crud.etl_job.get_multi(db, skip=0, limit=1000)
                
                scheduled_count = 0
                for job in etl_jobs:
                    if job.enabled and hasattr(job, 'schedule') and job.schedule:
                        job_config = {
                            'name': job.name,
                            'description': job.description,
                            'data_source_id': str(job.data_source_id),
                            'template_id': str(job.template_id) if job.template_id else None,
                            'config': job.config or {}
                        }
                        
                        if self.schedule_job(str(job.id), job.schedule, job_config):
                            scheduled_count += 1
                
                logger.info(f"从数据库加载并调度了 {scheduled_count} 个ETL作业")
                return scheduled_count
                
        except Exception as e:
            logger.error(f"从数据库加载ETL作业失败: {str(e)}")
            return 0
    
    def update_job_schedule(self, job_id: str, new_cron_expression: str) -> bool:
        """
        更新作业调度
        
        Args:
            job_id: 作业ID
            new_cron_expression: 新的cron表达式
            
        Returns:
            更新是否成功
        """
        try:
            if job_id in self.scheduled_jobs:
                job_config = self.scheduled_jobs[job_id]['job_config']
                
                # 先取消旧调度
                self.unschedule_job(job_id)
                
                # 创建新调度
                return self.schedule_job(job_id, new_cron_expression, job_config)
            else:
                logger.warning(f"尝试更新不存在的ETL作业调度: {job_id}")
                return False
                
        except Exception as e:
            logger.error(f"更新ETL作业调度失败 {job_id}: {str(e)}")
            return False


# 全局调度器实例
etl_scheduler = CeleryETLScheduler()


def init_etl_scheduler():
    """初始化ETL调度器"""
    try:
        # 从数据库加载作业
        scheduled_count = etl_scheduler.load_jobs_from_database()
        logger.info(f"ETL调度器初始化完成，调度了 {scheduled_count} 个作业")
        return True
    except Exception as e:
        logger.error(f"ETL调度器初始化失败: {str(e)}")
        return False