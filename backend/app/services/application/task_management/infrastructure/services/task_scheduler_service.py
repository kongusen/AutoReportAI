"""
Task Scheduler Service Implementation

任务调度服务实现
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job

from ...application.interfaces.task_scheduler_interface import TaskSchedulerInterface
from ...domain.entities.task_entity import ScheduleConfig

logger = logging.getLogger(__name__)


class TaskSchedulerService(TaskSchedulerInterface):
    """任务调度服务实现"""
    
    def __init__(self, task_execution_callback=None):
        self.scheduler = AsyncIOScheduler()
        self.scheduled_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_execution_callback = task_execution_callback
        self._scheduler_started = False
    
    async def start(self):
        """启动调度器"""
        if not self._scheduler_started:
            self.scheduler.start()
            self._scheduler_started = True
            logger.info("Task scheduler started")
    
    async def stop(self):
        """停止调度器"""
        if self._scheduler_started:
            self.scheduler.shutdown(wait=False)
            self._scheduler_started = False
            logger.info("Task scheduler stopped")
    
    async def schedule_task(self, task_id: str, schedule_config: ScheduleConfig):
        """调度任务"""
        try:
            if not schedule_config.is_valid():
                raise ValueError("Invalid schedule configuration")
            
            job_id = f"task_{task_id}"
            
            # 如果任务已存在，先移除
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # 创建cron触发器
            trigger = CronTrigger.from_crontab(
                schedule_config.cron_expression,
                timezone=schedule_config.timezone
            )
            
            # 添加任务
            job = self.scheduler.add_job(
                func=self._execute_scheduled_task,
                trigger=trigger,
                id=job_id,
                args=[task_id],
                replace_existing=True,
                max_instances=1,  # 防止同一任务并行执行
                coalesce=True,   # 合并错过的执行
                misfire_grace_time=300  # 5分钟的错过执行宽限时间
            )
            
            # 记录调度信息
            self.scheduled_tasks[task_id] = {
                "job_id": job_id,
                "schedule_config": schedule_config.__dict__,
                "next_run_time": job.next_run_time,
                "created_at": datetime.utcnow(),
                "execution_count": 0,
                "last_execution_time": None,
                "last_execution_status": None
            }
            
            logger.info(f"Task {task_id} scheduled with cron: {schedule_config.cron_expression}")
            
        except Exception as e:
            logger.error(f"Failed to schedule task {task_id}: {e}")
            raise
    
    async def unschedule_task(self, task_id: str) -> bool:
        """取消任务调度"""
        try:
            job_id = f"task_{task_id}"
            
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                
                # 移除调度记录
                if task_id in self.scheduled_tasks:
                    del self.scheduled_tasks[task_id]
                
                logger.info(f"Task {task_id} unscheduled")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to unschedule task {task_id}: {e}")
            return False
    
    async def reschedule_task(self, task_id: str, schedule_config: ScheduleConfig):
        """重新调度任务"""
        try:
            # 先取消现有调度
            await self.unschedule_task(task_id)
            
            # 重新调度
            await self.schedule_task(task_id, schedule_config)
            
            logger.info(f"Task {task_id} rescheduled")
            
        except Exception as e:
            logger.error(f"Failed to reschedule task {task_id}: {e}")
            raise
    
    async def get_next_run_time(self, task_id: str) -> Optional[datetime]:
        """获取下次运行时间"""
        try:
            job_id = f"task_{task_id}"
            job = self.scheduler.get_job(job_id)
            
            return job.next_run_time if job else None
            
        except Exception as e:
            logger.error(f"Failed to get next run time for task {task_id}: {e}")
            return None
    
    async def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """获取所有已调度的任务信息"""
        try:
            scheduled_tasks = []
            
            for task_id, task_info in self.scheduled_tasks.items():
                job_id = task_info["job_id"]
                job = self.scheduler.get_job(job_id)
                
                if job:
                    scheduled_tasks.append({
                        "task_id": task_id,
                        "job_id": job_id,
                        "cron_expression": task_info["schedule_config"]["cron_expression"],
                        "timezone": task_info["schedule_config"]["timezone"],
                        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                        "execution_count": task_info["execution_count"],
                        "last_execution_time": (
                            task_info["last_execution_time"].isoformat() 
                            if task_info["last_execution_time"] else None
                        ),
                        "last_execution_status": task_info["last_execution_status"],
                        "created_at": task_info["created_at"].isoformat()
                    })
            
            return scheduled_tasks
            
        except Exception as e:
            logger.error(f"Failed to get scheduled tasks: {e}")
            return []
    
    async def is_task_scheduled(self, task_id: str) -> bool:
        """检查任务是否已调度"""
        job_id = f"task_{task_id}"
        return self.scheduler.get_job(job_id) is not None
    
    async def pause_scheduler(self):
        """暂停调度器"""
        try:
            self.scheduler.pause()
            logger.info("Task scheduler paused")
            
        except Exception as e:
            logger.error(f"Failed to pause scheduler: {e}")
            raise
    
    async def resume_scheduler(self):
        """恢复调度器"""
        try:
            self.scheduler.resume()
            logger.info("Task scheduler resumed")
            
        except Exception as e:
            logger.error(f"Failed to resume scheduler: {e}")
            raise
    
    async def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        try:
            jobs = self.scheduler.get_jobs()
            
            return {
                "running": self.scheduler.running,
                "state": str(self.scheduler.state),
                "total_jobs": len(jobs),
                "scheduled_tasks": len(self.scheduled_tasks),
                "next_run_time": (
                    min([job.next_run_time for job in jobs if job.next_run_time]).isoformat()
                    if jobs else None
                ),
                "timezone": str(self.scheduler.timezone) if hasattr(self.scheduler, 'timezone') else 'UTC'
            }
            
        except Exception as e:
            logger.error(f"Failed to get scheduler status: {e}")
            return {"error": str(e)}
    
    async def _execute_scheduled_task(self, task_id: str):
        """执行调度任务"""
        try:
            logger.info(f"Executing scheduled task: {task_id}")
            
            # 更新执行统计
            if task_id in self.scheduled_tasks:
                self.scheduled_tasks[task_id]["execution_count"] += 1
                self.scheduled_tasks[task_id]["last_execution_time"] = datetime.utcnow()
                self.scheduled_tasks[task_id]["last_execution_status"] = "running"
            
            # 调用执行回调
            if self.task_execution_callback:
                try:
                    result = await self.task_execution_callback(task_id)
                    
                    # 更新执行状态
                    if task_id in self.scheduled_tasks:
                        if result and result.get("success"):
                            self.scheduled_tasks[task_id]["last_execution_status"] = "completed"
                        else:
                            self.scheduled_tasks[task_id]["last_execution_status"] = "failed"
                    
                    logger.info(f"Scheduled task {task_id} execution completed: {result}")
                    
                except Exception as callback_error:
                    logger.error(f"Task execution callback failed for {task_id}: {callback_error}")
                    
                    # 更新失败状态
                    if task_id in self.scheduled_tasks:
                        self.scheduled_tasks[task_id]["last_execution_status"] = "failed"
            else:
                logger.warning(f"No execution callback defined for task {task_id}")
            
        except Exception as e:
            logger.error(f"Failed to execute scheduled task {task_id}: {e}")
            
            # 更新失败状态
            if task_id in self.scheduled_tasks:
                self.scheduled_tasks[task_id]["last_execution_status"] = "failed"
    
    def set_execution_callback(self, callback):
        """设置任务执行回调"""
        self.task_execution_callback = callback
        logger.info("Task execution callback set")
    
    async def reload_schedules(self):
        """重新加载所有调度"""
        try:
            logger.info("Reloading all task schedules")
            
            # 获取当前所有任务ID
            current_task_ids = list(self.scheduled_tasks.keys())
            
            # 清除现有调度
            for task_id in current_task_ids:
                await self.unschedule_task(task_id)
            
            logger.info(f"Cleared {len(current_task_ids)} existing schedules")
            
            # 这里应该从数据库重新加载调度配置
            # 简化实现，由外部调用方重新设置调度
            
            logger.info("Schedule reload completed")
            
        except Exception as e:
            logger.error(f"Failed to reload schedules: {e}")
            raise
    
    async def get_job_details(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务作业详情"""
        try:
            job_id = f"task_{task_id}"
            job = self.scheduler.get_job(job_id)
            
            if not job:
                return None
            
            task_info = self.scheduled_tasks.get(task_id, {})
            
            return {
                "job_id": job_id,
                "task_id": task_id,
                "name": job.name,
                "func": str(job.func),
                "trigger": str(job.trigger),
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "max_instances": job.max_instances,
                "coalesce": job.coalesce,
                "misfire_grace_time": job.misfire_grace_time,
                "execution_count": task_info.get("execution_count", 0),
                "last_execution_status": task_info.get("last_execution_status"),
                "created_at": task_info.get("created_at").isoformat() if task_info.get("created_at") else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get job details for task {task_id}: {e}")
            return None