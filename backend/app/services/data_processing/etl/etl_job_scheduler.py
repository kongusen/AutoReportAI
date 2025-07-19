import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app import crud
from app.db.session import get_db_session
from .etl_service import ETLJobStatus, etl_service
from ...notification import NotificationService

logger = logging.getLogger(__name__)


class ETLJobExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ETLJobScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.running_jobs: Dict[str, Dict[str, Any]] = {}

    async def start(self):
        """启动调度器"""
        self.scheduler.start()
        await self._load_scheduled_jobs()
        logger.info("ETL Job Scheduler started")

    async def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        logger.info("ETL Job Scheduler stopped")

    async def _load_scheduled_jobs(self):
        """从数据库加载已调度的作业"""
        with get_db_session() as db:
            etl_jobs = crud.etl_job.get_multi(db, skip=0, limit=1000)

            for job in etl_jobs:
                if job.enabled and job.schedule:
                    await self.schedule_job(str(job.id), job.schedule)

    async def schedule_job(self, job_id: str, cron_expression: str):
        """调度ETL作业"""
        try:
            # 移除现有的调度（如果存在）
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)

            # 添加新的调度
            self.scheduler.add_job(
                func=self._execute_job_async,
                trigger=CronTrigger.from_crontab(cron_expression),
                id=job_id,
                args=[job_id],
                replace_existing=True,
            )

            logger.info(f"Scheduled ETL job {job_id} with cron: {cron_expression}")

        except Exception as e:
            logger.error(f"Failed to schedule ETL job {job_id}: {e}")
            raise

    async def unschedule_job(self, job_id: str):
        """取消调度ETL作业"""
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"Unscheduled ETL job {job_id}")
        except Exception as e:
            logger.error(f"Failed to unschedule ETL job {job_id}: {e}")

    async def execute_job_immediately(self, job_id: str) -> Dict[str, Any]:
        """立即执行ETL作业"""
        if job_id in self.running_jobs:
            return {"status": "error", "message": "Job is already running"}

        # 异步执行作业
        task = asyncio.create_task(self._execute_job_async(job_id))

        return {
            "status": "started",
            "job_id": job_id,
            "message": "Job execution started",
        }

    async def _execute_job_async(self, job_id: str):
        """异步执行ETL作业"""
        execution_id = f"{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 记录作业开始执行
        self.running_jobs[job_id] = {
            "execution_id": execution_id,
            "status": ETLJobExecutionStatus.RUNNING,
            "start_time": datetime.now(),
            "progress": 0,
        }

        try:
            with get_db_session() as db:
                etl_job = crud.etl_job.get(db, id=job_id)
                if not etl_job:
                    raise ValueError(f"ETL Job {job_id} not found")

                # 发送开始通知
                notification_service = NotificationService()
                await notification_service.notify_task_started(
                    db=db,
                    task_id=int(job_id) if job_id.isdigit() else 0,
                    user_id=str(etl_job.user_id),
                    task_name=etl_job.name,
                )

                # 执行ETL作业
                result = etl_service.run_job(job_id)

                # 更新作业状态
                self.running_jobs[job_id]["status"] = ETLJobExecutionStatus.SUCCESS
                self.running_jobs[job_id]["end_time"] = datetime.now()
                self.running_jobs[job_id]["result"] = result

                # 发送成功通知
                notification_service = NotificationService()
                await notification_service.notify_task_completed(
                    db=db,
                    task_id=int(job_id) if job_id.isdigit() else 0,
                    user_id=str(etl_job.user_id),
                    task_name=etl_job.name,
                )

                # 记录执行历史
                await self._save_execution_history(job_id, result, None)

                logger.info(f"ETL job {job_id} completed successfully")

        except Exception as e:
            # 更新作业状态为失败
            self.running_jobs[job_id]["status"] = ETLJobExecutionStatus.FAILED
            self.running_jobs[job_id]["end_time"] = datetime.now()
            self.running_jobs[job_id]["error"] = str(e)

            # 发送失败通知
            with get_db_session() as db:
                etl_job = crud.etl_job.get(db, id=job_id)
                if etl_job:
                    notification_service = NotificationService()
                    await notification_service.notify_task_failed(
                        db=db,
                        task_id=int(job_id) if job_id.isdigit() else 0,
                        user_id=str(etl_job.user_id),
                        task_name=etl_job.name,
                        error_message=str(e),
                    )

            # 记录执行历史
            await self._save_execution_history(job_id, None, str(e))

            logger.error(f"ETL job {job_id} failed: {e}")

        finally:
            # 清理运行状态（保留一段时间供查询）
            await asyncio.sleep(300)  # 5分钟后清理
            if job_id in self.running_jobs:
                del self.running_jobs[job_id]

    async def _save_execution_history(
        self, job_id: str, result: Optional[Dict], error: Optional[str]
    ):
        """保存执行历史"""
        try:
            with get_db_session() as db:
                # 这里应该创建一个ETL执行历史表来记录
                # 暂时使用日志记录
                history_data = {
                    "job_id": job_id,
                    "execution_time": datetime.now().isoformat(),
                    "status": "success" if result else "failed",
                    "result": result,
                    "error": error,
                }
                logger.info(f"ETL execution history: {history_data}")
        except Exception as e:
            logger.error(f"Failed to save execution history: {e}")

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """获取作业状态"""
        if job_id in self.running_jobs:
            return self.running_jobs[job_id]

        # 检查是否有调度
        scheduled_job = self.scheduler.get_job(job_id)
        if scheduled_job:
            return {
                "status": ETLJobExecutionStatus.PENDING,
                "next_run_time": (
                    scheduled_job.next_run_time.isoformat()
                    if scheduled_job.next_run_time
                    else None
                ),
            }

        return {"status": "not_scheduled", "message": "Job is not scheduled or running"}

    def get_all_running_jobs(self) -> Dict[str, Dict[str, Any]]:
        """获取所有运行中的作业"""
        return self.running_jobs.copy()


# 全局调度器实例
etl_scheduler = ETLJobScheduler()
