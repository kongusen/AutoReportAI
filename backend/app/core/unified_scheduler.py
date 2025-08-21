"""
统一任务调度系统
整合APScheduler和Celery Beat，提供统一的调度接口
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
import threading
import time

import redis.asyncio as redis
from app.core.time_utils import now, format_iso
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.db.session import get_db_session, SessionLocal
from app.models.task import Task
from app.services.infrastructure.notification.notification_service import NotificationService

logger = logging.getLogger(__name__)


class UnifiedTaskScheduler:
    """统一任务调度器 - 管理所有任务调度"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.active_tasks: Dict[int, Dict[str, Any]] = {}
        self.redis_client = None
        self.scheduler_type = 'celery'  # 默认使用Celery Beat
        self.apscheduler = None
        self._running = False
        
    async def initialize(self):
        """异步初始化"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL, 
                encoding="utf-8", 
                decode_responses=True
            )
            
            # 选择调度器类型
            scheduler_choice = getattr(settings, 'TASK_SCHEDULER_TYPE', 'celery').lower()
            
            if scheduler_choice == 'apscheduler':
                await self._init_apscheduler()
            else:
                await self._init_celery_scheduler()
                
            logger.info(f"统一调度器初始化完成，使用: {self.scheduler_type}")
            
        except Exception as e:
            logger.error(f"统一调度器初始化失败: {e}")
            raise
    
    async def _init_apscheduler(self):
        """初始化APScheduler"""
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.cron import CronTrigger
            
            self.apscheduler = AsyncIOScheduler()
            self.scheduler_type = 'apscheduler'
            
            # 启动调度器
            self.apscheduler.start()
            await self._load_scheduled_tasks_apscheduler()
            
        except Exception as e:
            logger.error(f"APScheduler初始化失败: {e}")
            # 回退到Celery
            await self._init_celery_scheduler()
    
    async def _init_celery_scheduler(self):
        """初始化Celery Beat调度器"""
        try:
            self.scheduler_type = 'celery'
            await self._load_scheduled_tasks_celery()
            
        except Exception as e:
            logger.error(f"Celery调度器初始化失败: {e}")
            raise
    
    async def _load_scheduled_tasks_apscheduler(self):
        """为APScheduler加载调度任务"""
        with get_db_session() as db:
            tasks = db.query(Task).filter(
                Task.is_active == True,
                Task.schedule.isnot(None)
            ).all()
            
            loaded_count = 0
            for task in tasks:
                try:
                    await self._add_apscheduler_job(task)
                    loaded_count += 1
                except Exception as e:
                    logger.error(f"加载APScheduler任务 {task.id} 失败: {e}")
            
            logger.info(f"APScheduler加载了 {loaded_count} 个任务")
    
    async def _load_scheduled_tasks_celery(self):
        """为Celery Beat加载调度任务"""
        try:
            from app.services.application.task_management.core.worker import celery_app
            from celery.schedules import crontab
            
            with get_db_session() as db:
                tasks = db.query(Task).filter(
                    Task.is_active == True,
                    Task.schedule.isnot(None)
                ).all()
                
                loaded_count = 0
                for task in tasks:
                    try:
                        # 解析cron表达式
                        cron_parts = task.schedule.split()
                        if len(cron_parts) == 5:
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
                            task_name = f"unified_task_{task.id}"
                            celery_app.conf.beat_schedule[task_name] = {
                                'task': 'app.services.application.task_management.core.worker.tasks.enhanced_tasks.execute_scheduled_task',
                                'schedule': schedule,
                                'args': (task.id,)
                            }
                            loaded_count += 1
                            logger.debug(f"Celery任务 {task.id} ({task.name}) 已注册")
                            
                    except Exception as e:
                        logger.error(f"加载Celery任务 {task.id} 失败: {e}")
                
                logger.info(f"Celery Beat加载了 {loaded_count} 个任务")
                
        except Exception as e:
            logger.error(f"Celery调度器加载失败: {e}")
            raise
    
    async def _add_apscheduler_job(self, task: Task):
        """添加APScheduler作业"""
        try:
            from apscheduler.triggers.cron import CronTrigger
            
            # 解析cron表达式
            cron_parts = task.schedule.split()
            if len(cron_parts) != 5:
                raise ValueError(f"Invalid cron expression: {task.schedule}")
            
            minute, hour, day, month, day_of_week = cron_parts
            trigger = CronTrigger(
                minute=minute,
                hour=hour, 
                day=day,
                month=month,
                day_of_week=day_of_week
            )
            
            job_id = f"unified_task_{task.id}"
            
            # 移除现有作业
            if self.apscheduler.get_job(job_id):
                self.apscheduler.remove_job(job_id)
            
            # 添加新作业
            self.apscheduler.add_job(
                func=self._execute_apscheduler_task,
                trigger=trigger,
                id=job_id,
                args=[task.id],
                replace_existing=True,
                misfire_grace_time=60
            )
            
        except Exception as e:
            logger.error(f"添加APScheduler作业失败 {task.id}: {e}")
            raise
    
    async def _execute_apscheduler_task(self, task_id: int):
        """APScheduler任务执行回调"""
        try:
            logger.info(f"APScheduler执行任务: {task_id}")
            
            with get_db_session() as db:
                task = crud.task.get(db, id=task_id)
                if not task or not task.is_active:
                    logger.warning(f"任务 {task_id} 不存在或未激活")
                    return
                
                # 使用Celery执行实际的任务处理
                from app.services.application.task_management.core.worker.tasks.enhanced_tasks import intelligent_report_generation_pipeline
                user_id = str(task.owner_id)
                
                # 异步启动Celery任务
                result = intelligent_report_generation_pipeline.delay(task_id, user_id)
                
                # 记录任务执行
                self.active_tasks[task_id] = {
                    "status": "running",
                    "start_time": now(),
                    "user_id": user_id,
                    "celery_task_id": result.id,
                    "triggered_by": "apscheduler"
                }
                
                logger.info(f"APScheduler任务 {task_id} 已启动Celery执行: {result.id}")
                
        except Exception as e:
            logger.error(f"APScheduler任务执行失败 {task_id}: {e}")
    
    async def add_or_update_task(self, task_id: int, cron_expression: str):
        """添加或更新任务调度"""
        try:
            if self.scheduler_type == 'apscheduler' and self.apscheduler:
                with get_db_session() as db:
                    task = crud.task.get(db, id=task_id)
                    if task:
                        await self._add_apscheduler_job(task)
            else:
                # 对于Celery，需要重新加载配置
                await self._reload_celery_task(task_id, cron_expression)
            
            logger.info(f"任务 {task_id} 调度已更新")
            
        except Exception as e:
            logger.error(f"更新任务调度失败 {task_id}: {e}")
            raise
    
    async def _reload_celery_task(self, task_id: int, cron_expression: str):
        """重新加载单个Celery任务"""
        try:
            from app.services.application.task_management.core.worker import celery_app
            from celery.schedules import crontab
            
            # 解析cron表达式
            cron_parts = cron_expression.split()
            if len(cron_parts) == 5:
                minute, hour, day, month, day_of_week = cron_parts
                
                schedule = crontab(
                    minute=minute,
                    hour=hour,
                    day_of_month=day,
                    month_of_year=month,
                    day_of_week=day_of_week
                )
                
                task_name = f"unified_task_{task_id}"
                celery_app.conf.beat_schedule[task_name] = {
                    'task': 'app.services.application.task_management.core.worker.tasks.enhanced_tasks.execute_scheduled_task',
                    'schedule': schedule,
                    'args': (task_id,)
                }
                
                logger.debug(f"Celery任务 {task_id} 调度已更新")
            
        except Exception as e:
            logger.error(f"重新加载Celery任务失败 {task_id}: {e}")
            raise
    
    async def remove_task(self, task_id: int):
        """移除任务调度"""
        try:
            job_id = f"unified_task_{task_id}"
            
            if self.scheduler_type == 'apscheduler' and self.apscheduler:
                if self.apscheduler.get_job(job_id):
                    self.apscheduler.remove_job(job_id)
            else:
                # 对于Celery，从beat_schedule中移除
                from app.services.application.task_management.core.worker import celery_app
                if job_id in celery_app.conf.beat_schedule:
                    del celery_app.conf.beat_schedule[job_id]
            
            # 清理活跃任务记录
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            
            logger.info(f"任务 {task_id} 调度已移除")
            
        except Exception as e:
            logger.error(f"移除任务调度失败 {task_id}: {e}")
    
    async def execute_task_immediately(self, task_id: int, user_id: str) -> Dict[str, Any]:
        """立即执行任务 - 优先级模式"""
        try:
            if task_id in self.active_tasks and self.active_tasks[task_id].get("status") == "running":
                return {"status": "error", "message": "任务正在执行中"}
            
            with get_db_session() as db:
                task = crud.task.get(db, id=task_id)
                if not task:
                    return {"status": "error", "message": "任务不存在"}
                
                # 存储任务所有者信息到Redis，供WebSocket通知使用
                await self._store_task_owner(task_id, user_id)
                
                # 发送开始通知
                await self._send_start_notification(db, task, user_id)
                
                # 检查是否有空闲worker，如果有就使用高优先级队列立即执行
                celery_result = await self._execute_with_priority(task_id, user_id)
                
                # 记录活跃任务
                self.active_tasks[task_id] = {
                    "status": "queued" if celery_result.get("queued") else "running",
                    "start_time": now(),
                    "user_id": user_id,
                    "celery_task_id": celery_result["celery_task_id"],
                    "triggered_by": "manual",
                    "processing_mode": celery_result.get("processing_mode", "intelligent")
                }
                
                return {
                    "status": "queued" if celery_result.get("queued") else "running",
                    "task_id": task_id,
                    "celery_task_id": celery_result["celery_task_id"],
                    "processing_mode": celery_result.get("processing_mode", "intelligent"),
                    "message": "智能占位符报告生成任务已加入队列" if celery_result.get("queued") else "任务已立即开始执行"
                }
                
        except Exception as e:
            logger.error(f"立即执行任务失败 {task_id}: {e}")
            return {"status": "error", "message": f"任务启动失败: {str(e)}"}
    
    async def _store_task_owner(self, task_id: int, user_id: str):
        """存储任务所有者信息到Redis供WebSocket通知使用"""
        try:
            if self.redis_client:
                await self.redis_client.set(
                    f"report_task:{task_id}:owner", 
                    user_id,
                    ex=86400  # 24小时过期
                )
                logger.debug(f"已存储任务 {task_id} 的所有者信息: {user_id}")
        except Exception as e:
            logger.error(f"存储任务所有者信息失败 {task_id}: {e}")
    
    async def _execute_with_priority(self, task_id: int, user_id: str) -> Dict[str, Any]:
        """智能优先级执行 - 检查worker状态并优化执行"""
        try:
            from app.services.application.task_management.core.worker.tasks.enhanced_tasks import intelligent_report_generation_pipeline
            from app.services.application.task_management.core.worker import celery_app
            
            # 检查当前活跃的worker数量
            active_workers = celery_app.control.inspect().active_queues()
            if active_workers:
                worker_count = len(active_workers)
                logger.info(f"当前活跃worker数量: {worker_count}")
            else:
                worker_count = 0
            
            # 检查当前队列中等待的任务数量
            queue_stats = celery_app.control.inspect().active()
            pending_tasks = 0
            if queue_stats:
                for worker_tasks in queue_stats.values():
                    pending_tasks += len(worker_tasks)
            
            logger.info(f"当前队列中任务数量: {pending_tasks}")
            
            # 智能调度决策
            if worker_count > 0 and pending_tasks < worker_count:
                # 有空闲worker，使用高优先级立即执行
                celery_result = intelligent_report_generation_pipeline.apply_async(
                    args=[task_id, user_id],
                    priority=9,  # 高优先级
                    queue='report_tasks'  # 指定队列
                )
                return {
                    "celery_task_id": celery_result.id,
                    "queued": False,
                    "processing_mode": "intelligent",
                    "message": "任务已立即开始执行"
                }
            else:
                # worker繁忙，正常加入队列
                celery_result = intelligent_report_generation_pipeline.delay(task_id, user_id)
                return {
                    "celery_task_id": celery_result.id,
                    "queued": True,
                    "processing_mode": "intelligent",
                    "message": "智能占位符报告生成任务已加入队列"
                }
                
        except Exception as e:
            logger.error(f"优先级执行检查失败: {e}")
            # 回退到普通执行
            from app.services.application.task_management.core.worker.tasks.enhanced_tasks import intelligent_report_generation_pipeline
            celery_result = intelligent_report_generation_pipeline.delay(task_id, user_id)
            return {
                "celery_task_id": celery_result.id,
                "queued": True,
                "processing_mode": "intelligent",
                "message": "智能占位符报告生成任务已加入队列"
            }
    
    async def get_task_status(self, task_id: int) -> Dict[str, Any]:
        """获取任务状态"""
        try:
            # 先从Redis获取实时状态
            if self.redis_client:
                redis_status = await self.redis_client.hgetall(f"report_task:{task_id}:status")
                if redis_status:
                    return redis_status
            
            # 检查活跃任务
            if task_id in self.active_tasks:
                return self.active_tasks[task_id]
            
            # 检查调度状态
            job_id = f"unified_task_{task_id}"
            if self.scheduler_type == 'apscheduler' and self.apscheduler:
                scheduled_job = self.apscheduler.get_job(job_id)
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
            
            return {"status": "not_found", "message": "未找到任务状态"}
            
        except Exception as e:
            logger.error(f"获取任务状态失败 {task_id}: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _send_start_notification(self, db: Session, task: Task, user_id: str):
        """发送开始通知"""
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
        except Exception as e:
            logger.error(f"发送开始通知失败: {e}")
    
    async def get_scheduler_info(self) -> Dict[str, Any]:
        """获取调度器信息"""
        info = {
            "scheduler_type": self.scheduler_type,
            "active_tasks_count": len(self.active_tasks),
            "active_tasks": list(self.active_tasks.keys())
        }
        
        if self.scheduler_type == 'apscheduler' and self.apscheduler:
            jobs = self.apscheduler.get_jobs()
            info["scheduled_jobs"] = [
                {
                    "job_id": job.id,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                }
                for job in jobs
                if job.id.startswith("unified_task_")
            ]
        else:
            try:
                from app.services.application.task_management.core.worker import celery_app
                info["celery_beat_schedule"] = list(celery_app.conf.beat_schedule.keys())
            except:
                info["celery_beat_schedule"] = []
        
        return info
    
    async def reload_all_tasks(self):
        """重新加载所有任务"""
        try:
            if self.scheduler_type == 'apscheduler' and self.apscheduler:
                # 清除所有现有作业
                for job in self.apscheduler.get_jobs():
                    if job.id.startswith("unified_task_"):
                        self.apscheduler.remove_job(job.id)
                
                # 重新加载
                await self._load_scheduled_tasks_apscheduler()
            else:
                # 清除Celery调度
                from app.services.application.task_management.core.worker import celery_app
                keys_to_remove = [k for k in celery_app.conf.beat_schedule.keys() if k.startswith("unified_task_")]
                for key in keys_to_remove:
                    del celery_app.conf.beat_schedule[key]
                
                # 重新加载
                await self._load_scheduled_tasks_celery()
            
            logger.info("所有任务调度已重新加载")
            
        except Exception as e:
            logger.error(f"重新加载任务失败: {e}")
            raise
    
    async def shutdown(self):
        """关闭调度器"""
        try:
            if self.apscheduler:
                self.apscheduler.shutdown()
            
            if self.redis_client:
                await self.redis_client.close()
            
            self.active_tasks.clear()
            logger.info("统一调度器已关闭")
            
        except Exception as e:
            logger.error(f"关闭调度器失败: {e}")


# 全局单例实例
scheduler = UnifiedTaskScheduler()


async def get_scheduler() -> UnifiedTaskScheduler:
    """获取统一调度器实例"""
    if not hasattr(scheduler, '_initialized') or not scheduler._initialized:
        await scheduler.initialize()
    return scheduler


# 便捷函数
async def add_task_schedule(task_id: int, cron_expression: str):
    """添加任务调度"""
    scheduler_instance = await get_scheduler()
    return await scheduler_instance.add_or_update_task(task_id, cron_expression)


async def remove_task_schedule(task_id: int):
    """移除任务调度"""
    scheduler_instance = await get_scheduler()
    return await scheduler_instance.remove_task(task_id)


async def execute_task(task_id: int, user_id: str):
    """立即执行任务"""
    scheduler_instance = await get_scheduler()
    return await scheduler_instance.execute_task_immediately(task_id, user_id)


async def get_task_status(task_id: int):
    """获取任务状态"""
    scheduler_instance = await get_scheduler()
    return await scheduler_instance.get_task_status(task_id)