"""
基于Task模型的智能调度器
专门处理智能占位符驱动的报告生成任务
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import redis.asyncio as redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.db.session import get_db_session
from app.models.task import Task
# 移除循环导入，在需要时动态导入
from app.services.infrastructure.notification.notification_service import NotificationService

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Task智能调度器 - 专门处理基于模板和数据源的智能报告生成任务"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.active_tasks: Dict[int, Dict[str, Any]] = {}
        self.redis_client = redis.from_url(
            settings.REDIS_URL, 
            encoding="utf-8", 
            decode_responses=True
        )
        
    async def start(self):
        """启动调度器"""
        self.scheduler.start()
        await self._load_scheduled_tasks()
        logger.info("Task智能调度器已启动")
        
    async def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        await self.redis_client.close()
        logger.info("Task智能调度器已停止")
        
    async def _load_scheduled_tasks(self):
        """从数据库加载所有活跃的Task调度"""
        with get_db_session() as db:
            tasks = db.query(Task).filter(
                Task.is_active == True,
                Task.schedule.isnot(None)
            ).all()
            
            loaded_count = 0
            for task in tasks:
                try:
                    await self.schedule_task(task.id, task.schedule)
                    loaded_count += 1
                except Exception as e:
                    logger.error(f"加载Task调度失败 ID={task.id}: {e}")
            
            if loaded_count > 0:
                logger.info(f"总共加载了 {loaded_count} 个Task调度")
    
    async def schedule_task(self, task_id: int, cron_expression: str):
        """调度单个Task"""
        try:
            job_id = f"task_{task_id}"
            
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            self.scheduler.add_job(
                func=self._execute_task_job,
                trigger=CronTrigger.from_crontab(cron_expression),
                id=job_id,
                args=[task_id],
                replace_existing=True,
            )
            
            logger.info(f"Task {task_id} 已调度，cron: {cron_expression}")
            
        except Exception as e:
            logger.error(f"调度Task {task_id} 失败: {e}")
            raise
    
    async def unschedule_task(self, task_id: int):
        """取消Task调度"""
        try:
            job_id = f"task_{task_id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"已取消Task {task_id} 的调度")
        except Exception as e:
            logger.error(f"取消Task {task_id} 调度失败: {e}")
    
    async def execute_task_immediately(self, task_id: int, user_id: str) -> Dict[str, Any]:
        """立即执行Task"""
        if task_id in self.active_tasks and self.active_tasks[task_id].get("status") == "running":
            return {"status": "error", "message": "任务正在执行中"}
        
        with get_db_session() as db:
            task = crud.task.get(db, id=task_id)
            if not task:
                return {"status": "error", "message": "任务不存在"}
            
            try:
                # 预先发送开始通知
                await self._send_start_notification(db, task, user_id)
                
                # 更新Redis初始状态
                initial_progress = {
                    "status": "pending",
                    "progress": 5,
                    "current_step": "任务已启动，等待Worker响应...",
                    "updated_at": datetime.utcnow().isoformat()
                }
                await self.redis_client.hset(f"report_task:{task_id}:status", mapping=initial_progress)
                
                # 异步启动Celery任务
                from app.services.application.task_management.core.worker.tasks.enhanced_tasks import intelligent_report_generation_pipeline
                celery_result = intelligent_report_generation_pipeline.delay(task_id, user_id)
                
                self.active_tasks[task_id] = {
                    "status": "running",
                    "start_time": datetime.now(),
                    "user_id": user_id,
                    "celery_task_id": celery_result.id
                }
                
                return {
                    "status": "started",
                    "task_id": task_id,
                    "celery_task_id": celery_result.id,
                    "message": "智能报告生成任务已启动"
                }
            
            except Exception as e:
                logger.error(f"立即执行Task {task_id} 失败: {e}")
                await self._send_error_notification(db, task, str(e))
                return {"status": "error", "message": f"任务启动失败: {str(e)}"}
    
    def _execute_task_job(self, task_id: int):
        """执行Task作业（调度器回调），改为同步启动异步任务"""
        asyncio.create_task(self._async_execute_task_job(task_id))

    async def _async_execute_task_job(self, task_id: int):
        """异步执行Task作业"""
        logger.info(f"开始执行调度的Task: {task_id}")
        with get_db_session() as db:
            task = crud.task.get(db, id=task_id)
            if not task:
                logger.error(f"Task {task_id} 不存在，无法执行调度")
                return

            if not task.is_active:
                logger.warning(f"Task {task.id} ({task.name}) 已禁用，跳过本次调度执行")
                return

            if task_id in self.active_tasks and self.active_tasks[task_id].get("status") == "running":
                logger.warning(f"Task {task_id} 正在执行中，跳过本次调度执行")
                return

            try:
                user_id = str(task.owner_id)
                await self._send_start_notification(db, task, user_id)
                
                initial_progress = {
                    "status": "pending",
                    "progress": 5,
                    "current_step": "任务已由调度器启动...",
                    "updated_at": datetime.utcnow().isoformat()
                }
                await self.redis_client.hset(f"report_task:{task_id}:status", mapping=initial_progress)

                # 动态导入避免循环依赖
                from app.services.application.task_management.core.worker.tasks.enhanced_tasks import intelligent_report_generation_pipeline

                celery_result = intelligent_report_generation_pipeline.delay(task_id, user_id)
                
                self.active_tasks[task_id] = {
                    "status": "running",
                    "start_time": datetime.now(),
                    "user_id": user_id,
                    "celery_task_id": celery_result.id,
                    "triggered_by": "scheduler"
                }
                logger.info(f"Task {task_id} 调度执行已启动，Celery任务: {celery_result.id}")
            
            except Exception as e:
                logger.error(f"调度执行Task {task_id} 失败: {e}")
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
                await self._send_error_notification(db, task, str(e))
    
    async def get_task_status(self, task_id: int) -> Dict[str, Any]:
        """获取Task的综合状态（结合调度器和Redis）"""
        
        # 1. 从Redis获取实时进度
        redis_status = await self.redis_client.hgetall(f"report_task:{task_id}:status")
        
        if redis_status:
            # 如果是终态，清理本地active_tasks
            if redis_status.get("status") in ["completed", "failed"]:
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
            return redis_status

        # 2. 如果Redis没有，检查本地active_tasks
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]

        # 3. 检查调度状态
        job_id = f"task_{task_id}"
        scheduled_job = self.scheduler.get_job(job_id)
        if scheduled_job:
            return {
                "status": "scheduled",
                "progress": 0,
                "current_step": "等待调度执行",
                "next_run_time": (
                    scheduled_job.next_run_time.isoformat()
                    if scheduled_job.next_run_time
                    else None
                ),
            }
        
        return {"status": "not_found", "message": "未找到任务状态或调度信息"}
    
    async def _send_start_notification(self, db: Session, task: Task, user_id: str):
        """发送任务开始通知"""
        try:
            notification_service = NotificationService()
            await notification_service.send_task_progress_update(
                task_id=task.id,
                progress_data={
                    "status": "starting", 
                    "progress": 5, 
                    "message": "任务已启动..."
                }
            )
            logger.info(f"已发送任务启动通知, Task ID: {task.id}")
        except Exception as e:
            logger.error(f"发送开始通知失败: {e}")
    
    async def _send_error_notification(self, db: Session, task: Task, error_message: str):
        """发送错误通知"""
        try:
            notification_service = NotificationService()
            await notification_service.notify_task_failed(
                db=db,
                task_id=task.id,
                user_id=str(task.owner_id),
                task_name=task.name,
                error_message=error_message
            )
        except Exception as e:
            logger.error(f"发送错误通知失败: {e}")
    
    def get_all_active_tasks(self) -> Dict[int, Dict[str, Any]]:
        """获取所有活跃的Task"""
        return self.active_tasks.copy()
    
    def get_scheduled_tasks_info(self) -> List[Dict[str, Any]]:
        """获取所有调度的Task信息"""
        scheduled_tasks = []
        jobs = self.scheduler.get_jobs()
        
        for job in jobs:
            if job.id.startswith("task_"):
                task_id = int(job.id.replace("task_", ""))
                scheduled_tasks.append({
                    "task_id": task_id,
                    "job_id": job.id,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                })
        
        return scheduled_tasks
    
    async def reload_task_schedules(self):
        """重新加载所有Task调度"""
        logger.info("开始重新加载Task调度")
        
        # 清除现有调度
        for job in self.scheduler.get_jobs():
            if job.id.startswith("task_"):
                self.scheduler.remove_job(job.id)
        
        await self._load_scheduled_tasks()
        logger.info("Task调度重新加载完成")


