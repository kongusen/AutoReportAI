"""
任务调度器

通用的异步任务调度和执行
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    LOW = 0
    NORMAL = 1  
    HIGH = 2
    URGENT = 3

@dataclass
class ScheduledTask:
    task_id: str
    name: str
    callback: Callable
    args: tuple
    kwargs: dict
    priority: TaskPriority
    scheduled_time: datetime
    created_at: datetime
    max_retries: int = 3
    retry_count: int = 0

class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._workers = []
        self._task_queue = asyncio.Queue()
        
        logger.info("任务调度器初始化完成")
    
    async def start(self):
        """启动调度器"""
        if self._running:
            return
            
        self._running = True
        
        # 启动工作线程
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker_{i}"))
            self._workers.append(worker)
        
        # 启动调度检查任务
        self._scheduler_task = asyncio.create_task(self._schedule_checker())
        
        logger.info("任务调度器已启动")
    
    async def stop(self):
        """停止调度器"""
        if not self._running:
            return
            
        self._running = False
        
        # 停止调度检查任务
        if hasattr(self, '_scheduler_task'):
            self._scheduler_task.cancel()
        
        # 等待队列清空
        await self._task_queue.join()
        
        # 停止工作线程
        for worker in self._workers:
            worker.cancel()
        
        self._workers.clear()
        logger.info("任务调度器已停止")
    
    async def schedule_task(self, 
                           task_id: str,
                           name: str,
                           callback: Callable,
                           scheduled_time: datetime,
                           priority: TaskPriority = TaskPriority.NORMAL,
                           *args, **kwargs) -> bool:
        """调度任务"""
        try:
            task = ScheduledTask(
                task_id=task_id,
                name=name, 
                callback=callback,
                args=args,
                kwargs=kwargs,
                priority=priority,
                scheduled_time=scheduled_time,
                created_at=datetime.now()
            )
            
            self._tasks[task_id] = task
            logger.info(f"调度任务: {task_id} - {name}")
            return True
        except Exception as e:
            logger.error(f"调度任务失败: {e}")
            return False
    
    async def _schedule_checker(self):
        """检查待执行任务"""
        while self._running:
            try:
                current_time = datetime.now()
                ready_tasks = []
                
                # 找到需要执行的任务
                for task_id, task in list(self._tasks.items()):
                    if task.scheduled_time <= current_time:
                        ready_tasks.append(task)
                        del self._tasks[task_id]
                
                # 按优先级排序
                ready_tasks.sort(key=lambda t: t.priority.value, reverse=True)
                
                # 加入执行队列
                for task in ready_tasks:
                    await self._task_queue.put(task)
                
                await asyncio.sleep(10)  # 每10秒检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"调度检查出错: {e}")
                await asyncio.sleep(10)
    
    async def _worker(self, worker_name: str):
        """工作线程"""
        while self._running:
            try:
                task = await self._task_queue.get()
                
                try:
                    logger.info(f"{worker_name} 执行任务: {task.name}")
                    
                    if asyncio.iscoroutinefunction(task.callback):
                        await task.callback(*task.args, **task.kwargs)
                    else:
                        task.callback(*task.args, **task.kwargs)
                    
                    logger.info(f"{worker_name} 完成任务: {task.name}")
                    
                except Exception as e:
                    logger.error(f"{worker_name} 任务执行失败: {task.name} - {e}")
                    
                    # 重试逻辑
                    if task.retry_count < task.max_retries:
                        task.retry_count += 1
                        task.scheduled_time = datetime.now() + timedelta(minutes=1)
                        self._tasks[task.task_id] = task
                        logger.info(f"任务 {task.name} 将重试 (第{task.retry_count}次)")
                
                self._task_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"{worker_name} 出错: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'pending_tasks': len(self._tasks),
            'queue_size': self._task_queue.qsize(),
            'workers': len(self._workers),
            'running': self._running
        }

# 全局任务调度器
_task_scheduler: Optional[TaskScheduler] = None

def get_task_scheduler() -> TaskScheduler:
    global _task_scheduler
    if _task_scheduler is None:
        _task_scheduler = TaskScheduler()
    return _task_scheduler