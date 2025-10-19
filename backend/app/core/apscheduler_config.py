"""
APScheduler 配置和任务管理器
使用数据库持久化调度信息，替代 Celery Beat
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def task_executor_function(task_id: int):
    """
    APScheduler 调用的任务执行函数

    Args:
        task_id: 任务ID
    """
    from app.services.infrastructure.task_queue.celery_config import celery_app
    from app.services.application.tasks.workflow_tasks import generate_report_workflow
    from app.db.session import SessionLocal
    from app.models.task import Task

    logger.info(f"📅 APScheduler 触发任务执行: task_id={task_id}")

    # 获取任务信息
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task or not task.is_active:
            logger.warning(f"⚠️ 任务 {task_id} 不存在或未激活，跳过执行")
            return

        # 提交到 Celery 队列执行
        celery_result = generate_report_workflow.delay(
            str(task.template_id),
            [str(task.data_source_id)],
            {'user_id': str(task.owner_id), 'task_id': str(task_id), 'triggered_by': 'apscheduler'}
        )

        logger.info(f"✅ 任务 {task_id} 已提交到 Celery: {celery_result.id}")
    except Exception as e:
        logger.error(f"❌ APScheduler 执行任务 {task_id} 失败: {e}")
    finally:
        db.close()


class APSchedulerTaskManager:
    """APScheduler 任务管理器"""

    def __init__(self):
        """初始化 APScheduler"""
        from app.core.config import settings

        # 配置 APScheduler
        jobstores = {
            'default': SQLAlchemyJobStore(url=settings.DATABASE_URL)
        }

        executors = {
            'default': ThreadPoolExecutor(20)
        }

        job_defaults = {
            'coalesce': True,  # 错过的任务只执行一次
            'max_instances': 1,  # 同一个任务最多只有一个实例在运行
            'misfire_grace_time': 60  # 错过执行时间60秒内仍然执行
        }

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='Asia/Shanghai'
        )

        logger.info("✅ APScheduler 初始化完成")

    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("✅ APScheduler 已启动")
        else:
            logger.warning("⚠️ APScheduler 已在运行")

    def shutdown(self, wait: bool = True):
        """
        关闭调度器

        Args:
            wait: 是否等待正在执行的任务完成
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("✅ APScheduler 已关闭")

    def add_task(self, task_id: int, cron_expression: str) -> Optional[datetime]:
        """
        添加任务到调度器

        Args:
            task_id: 任务ID
            cron_expression: Cron表达式

        Returns:
            下次执行时间
        """
        job_id = f"task_{task_id}"

        try:
            # 解析 cron 表达式
            parts = cron_expression.split()
            if len(parts) != 5:
                raise ValueError(f"Invalid cron expression: {cron_expression}")

            minute, hour, day, month, day_of_week = parts

            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone='Asia/Shanghai'
            )

            # 移除旧任务（如果存在）
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"🔄 移除旧任务调度: {job_id}")

            # 添加新任务
            self.scheduler.add_job(
                func=task_executor_function,
                trigger=trigger,
                args=[task_id],
                id=job_id,
                name=f"Task_{task_id}",
                replace_existing=True
            )

            next_run = self.scheduler.get_job(job_id).next_run_time
            logger.info(f"✅ 任务 {task_id} 已添加到调度器，下次执行: {next_run}")
            return next_run

        except Exception as e:
            logger.error(f"❌ 添加任务 {task_id} 到调度器失败: {e}")
            raise

    def remove_task(self, task_id: int):
        """
        从调度器移除任务

        Args:
            task_id: 任务ID
        """
        job_id = f"task_{task_id}"

        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"✅ 任务 {task_id} 已从调度器移除")
            else:
                logger.warning(f"⚠️ 任务 {task_id} 不在调度器中")
        except Exception as e:
            logger.error(f"❌ 移除任务 {task_id} 失败: {e}")
            raise

    def get_task_info(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        获取任务调度信息

        Args:
            task_id: 任务ID

        Returns:
            任务信息字典，如果任务不存在返回 None
        """
        job_id = f"task_{task_id}"
        job = self.scheduler.get_job(job_id)

        if not job:
            return None

        return {
            "job_id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
            "pending": job.pending
        }

    def load_tasks_from_database(self):
        """从数据库加载所有活跃任务"""
        from app.db.session import SessionLocal
        from app.models.task import Task

        db = SessionLocal()
        try:
            tasks = db.query(Task).filter(
                Task.is_active == True,
                Task.schedule.isnot(None)
            ).all()

            loaded_count = 0
            failed_count = 0

            for task in tasks:
                try:
                    self.add_task(task.id, task.schedule)
                    loaded_count += 1
                except Exception as e:
                    logger.error(f"❌ 加载任务 {task.id} 失败: {e}")
                    failed_count += 1

            logger.info(f"✅ 从数据库加载了 {loaded_count} 个任务，失败 {failed_count} 个")
            return {"loaded": loaded_count, "failed": failed_count}

        except Exception as e:
            logger.error(f"❌ 从数据库加载任务失败: {e}")
            raise
        finally:
            db.close()

    def list_all_jobs(self) -> List[Dict[str, Any]]:
        """
        列出所有调度任务

        Returns:
            任务列表
        """
        jobs = self.scheduler.get_jobs()
        return [
            {
                "job_id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
                "pending": job.pending
            }
            for job in jobs
        ]

    def get_scheduler_state(self) -> Dict[str, Any]:
        """
        获取调度器状态

        Returns:
            调度器状态信息
        """
        return {
            "running": self.scheduler.running,
            "total_jobs": len(self.scheduler.get_jobs()),
            "state": self.scheduler.state
        }


# 全局实例
apscheduler_manager = APSchedulerTaskManager()
