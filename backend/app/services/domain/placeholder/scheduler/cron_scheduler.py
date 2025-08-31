"""
Cron调度器

基于Cron表达式的任务调度
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import croniter
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CronJob:
    job_id: str
    name: str
    cron_expression: str
    callback: Callable
    args: tuple
    kwargs: dict
    enabled: bool
    next_run: datetime
    last_run: Optional[datetime] = None

class CronScheduler:
    """Cron调度器"""
    
    def __init__(self):
        self._jobs: Dict[str, CronJob] = {}
        self._running = False
        self._scheduler_task = None
        
        logger.info("Cron调度器初始化完成")
    
    async def start(self):
        """启动调度器"""
        if self._running:
            return
            
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Cron调度器已启动")
    
    async def stop(self):
        """停止调度器"""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
        logger.info("Cron调度器已停止")
    
    async def add_job(self, 
                     job_id: str,
                     name: str, 
                     cron_expression: str,
                     callback: Callable,
                     *args, **kwargs) -> bool:
        """添加Cron任务"""
        try:
            # 验证cron表达式
            cron = croniter.croniter(cron_expression, datetime.now())
            next_run = cron.get_next(datetime)
            
            job = CronJob(
                job_id=job_id,
                name=name,
                cron_expression=cron_expression,
                callback=callback,
                args=args,
                kwargs=kwargs,
                enabled=True,
                next_run=next_run
            )
            
            self._jobs[job_id] = job
            logger.info(f"添加Cron任务: {job_id} - {cron_expression}")
            return True
            
        except Exception as e:
            logger.error(f"添加Cron任务失败: {e}")
            return False
    
    async def remove_job(self, job_id: str) -> bool:
        """移除任务"""
        if job_id in self._jobs:
            del self._jobs[job_id]
            logger.info(f"移除Cron任务: {job_id}")
            return True
        return False
    
    async def _scheduler_loop(self):
        """调度循环"""
        while self._running:
            try:
                current_time = datetime.now()
                
                for job in self._jobs.values():
                    if job.enabled and job.next_run <= current_time:
                        # 执行任务
                        asyncio.create_task(self._execute_job(job))
                        
                        # 计算下次运行时间
                        cron = croniter.croniter(job.cron_expression, current_time)
                        job.next_run = cron.get_next(datetime)
                        job.last_run = current_time
                
                await asyncio.sleep(30)  # 每30秒检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cron调度循环出错: {e}")
                await asyncio.sleep(30)
    
    async def _execute_job(self, job: CronJob):
        """执行任务"""
        try:
            logger.info(f"执行Cron任务: {job.name}")
            
            if asyncio.iscoroutinefunction(job.callback):
                await job.callback(*job.args, **job.kwargs)
            else:
                job.callback(*job.args, **job.kwargs)
                
        except Exception as e:
            logger.error(f"Cron任务执行失败: {job.name} - {e}")

# 全局Cron调度器
_cron_scheduler: Optional[CronScheduler] = None

def get_cron_scheduler() -> CronScheduler:
    global _cron_scheduler
    if _cron_scheduler is None:
        _cron_scheduler = CronScheduler()
    return _cron_scheduler