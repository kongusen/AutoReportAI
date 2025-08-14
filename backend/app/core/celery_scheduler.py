"""
完整的 Celery 调度系统
提供任务调度、监控和管理功能
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import redis
from celery import Celery, chord, group
from celery.schedules import crontab
from celery.signals import task_prerun, task_postrun, task_failure, task_success
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.db.session import get_db_session, SessionLocal
from app.models.task import Task
from app.services.notification.notification_service import NotificationService

logger = logging.getLogger(__name__)


class CelerySchedulerManager:
    """Celery 调度管理器"""
    
    def __init__(self, celery_app: Celery):
        self.celery_app = celery_app
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.notification_service = NotificationService()
        
    def load_scheduled_tasks_from_database(self) -> int:
        """从数据库加载调度任务到 Celery Beat"""
        try:
            with get_db_session() as db:
                # 获取所有激活的调度任务
                tasks = db.query(Task).filter(
                    and_(
                        Task.is_active == True,
                        Task.schedule.isnot(None)
                    )
                ).all()
                
                loaded_count = 0
                for task in tasks:
                    try:
                        success = self._register_task_to_celery_beat(task)
                        if success:
                            loaded_count += 1
                    except Exception as e:
                        logger.error(f"注册任务 {task.id} 到 Celery Beat 失败: {e}")
                
                logger.info(f"成功从数据库加载 {loaded_count}/{len(tasks)} 个任务到 Celery Beat")
                return loaded_count
                
        except Exception as e:
            logger.error(f"从数据库加载任务失败: {e}")
            return 0
    
    def _register_task_to_celery_beat(self, task: Task) -> bool:
        """将单个任务注册到 Celery Beat"""
        try:
            # 解析 cron 表达式
            cron_parts = task.schedule.strip().split()
            if len(cron_parts) != 5:
                logger.warning(f"任务 {task.id} 的 cron 表达式格式不正确: {task.schedule}")
                return False
            
            minute, hour, day, month, day_of_week = cron_parts
            
            # 创建 Celery crontab 调度
            schedule = crontab(
                minute=minute,
                hour=hour, 
                day_of_month=day,
                month_of_year=month,
                day_of_week=day_of_week
            )
            
            # 注册到 Celery Beat
            task_name = f"scheduled_task_{task.id}"
            self.celery_app.conf.beat_schedule[task_name] = {
                'task': 'app.core.worker.execute_scheduled_task',
                'schedule': schedule,
                'args': (task.id,),
                'options': {
                    'queue': 'report_tasks',
                    'priority': task.priority if hasattr(task, 'priority') else 5
                }
            }
            
            logger.info(f"任务 {task.id} ({task.name}) 已注册到 Celery Beat，调度: {task.schedule}")
            return True
            
        except Exception as e:
            logger.error(f"注册任务 {task.id} 到 Celery Beat 失败: {e}")
            return False
    
    def add_or_update_task(self, task_id: int, cron_expression: str) -> bool:
        """添加或更新任务调度"""
        try:
            with get_db_session() as db:
                task = crud.task.get(db, id=task_id)
                if not task:
                    logger.error(f"任务 {task_id} 不存在")
                    return False
                
                # 更新数据库中的调度表达式
                task_update = {"schedule": cron_expression}
                crud.task.update(db, db_obj=task, obj_in=task_update)
                
                # 重新注册到 Celery Beat
                success = self._register_task_to_celery_beat(task)
                
                if success:
                    logger.info(f"任务 {task_id} 调度已更新: {cron_expression}")
                    
                return success
                
        except Exception as e:
            logger.error(f"更新任务 {task_id} 调度失败: {e}")
            return False
    
    def remove_task(self, task_id: int) -> bool:
        """从调度中移除任务"""
        try:
            task_name = f"scheduled_task_{task_id}"
            
            # 从 Celery Beat 中移除
            if task_name in self.celery_app.conf.beat_schedule:
                del self.celery_app.conf.beat_schedule[task_name]
                logger.info(f"任务 {task_id} 已从 Celery Beat 中移除")
            
            # 更新数据库
            with get_db_session() as db:
                task = crud.task.get(db, id=task_id)
                if task:
                    task_update = {"schedule": None, "is_active": False}
                    crud.task.update(db, db_obj=task, obj_in=task_update)
            
            return True
            
        except Exception as e:
            logger.error(f"移除任务 {task_id} 调度失败: {e}")
            return False
    
    def get_task_status(self, task_id: int) -> Dict[str, Any]:
        """获取任务状态信息"""
        try:
            # 从 Redis 获取实时状态
            status_key = f"report_task:{task_id}:status"
            status_data = self.redis_client.hgetall(status_key)
            
            # 从数据库获取基本信息
            with get_db_session() as db:
                task = crud.task.get(db, id=task_id)
                if not task:
                    return {"error": f"任务 {task_id} 不存在"}
                
                result = {
                    "task_id": task_id,
                    "name": task.name,
                    "schedule": task.schedule,
                    "is_active": task.is_active,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                }
                
                # 合并实时状态
                if status_data:
                    result.update(status_data)
                    
                # 检查是否在 Celery Beat 中
                task_name = f"scheduled_task_{task_id}"
                result["in_celery_beat"] = task_name in self.celery_app.conf.beat_schedule
                
                return result
                
        except Exception as e:
            logger.error(f"获取任务 {task_id} 状态失败: {e}")
            return {"error": str(e)}
    
    def get_all_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """获取所有调度任务的信息"""
        try:
            tasks_info = []
            
            # 从数据库获取任务信息
            with get_db_session() as db:
                tasks = db.query(Task).filter(Task.is_active == True).all()
                
                for task in tasks:
                    task_info = {
                        "task_id": task.id,
                        "name": task.name,
                        "schedule": task.schedule,
                        "is_active": task.is_active,
                        "template_id": task.template_id,
                        "data_source_id": task.data_source_id,
                        "created_at": task.created_at.isoformat() if task.created_at else None,
                    }
                    
                    # 检查是否在 Celery Beat 中
                    task_name = f"scheduled_task_{task.id}"
                    task_info["in_celery_beat"] = task_name in self.celery_app.conf.beat_schedule
                    
                    # 获取最近的执行状态
                    status_key = f"report_task:{task.id}:status"
                    status_data = self.redis_client.hgetall(status_key)
                    if status_data:
                        task_info["last_status"] = status_data
                    
                    tasks_info.append(task_info)
            
            return tasks_info
            
        except Exception as e:
            logger.error(f"获取所有调度任务信息失败: {e}")
            return []
    
    def execute_task_immediately(self, task_id: int, user_id: str) -> Dict[str, Any]:
        """立即执行任务（不等待调度）"""
        try:
            # 验证任务存在
            with get_db_session() as db:
                task = crud.task.get(db, id=task_id)
                if not task:
                    return {"status": "error", "message": f"任务 {task_id} 不存在"}
                
                if not task.is_active:
                    return {"status": "error", "message": f"任务 {task_id} 未激活"}
            
            # 提交任务到 Celery 队列
            from app.core.worker import intelligent_report_generation_pipeline
            result = intelligent_report_generation_pipeline.delay(task_id, user_id)
            
            logger.info(f"任务 {task_id} 已提交立即执行，Celery task ID: {result.id}")
            
            return {
                "status": "submitted",
                "message": f"任务 {task_id} 已提交执行",
                "celery_task_id": result.id,
                "task_id": task_id
            }
            
        except Exception as e:
            logger.error(f"立即执行任务 {task_id} 失败: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """获取 Worker 统计信息"""
        try:
            inspect = self.celery_app.control.inspect()
            
            stats = {
                "workers": {},
                "active_tasks": {},
                "scheduled_tasks": {},
                "reserved_tasks": {},
                "stats": {}
            }
            
            # 获取活跃的 workers
            active_workers = inspect.active()
            if active_workers:
                stats["workers"] = active_workers
            
            # 获取活跃任务
            active_tasks = inspect.active()
            if active_tasks:
                stats["active_tasks"] = active_tasks
            
            # 获取已注册的任务
            registered = inspect.registered()
            if registered:
                stats["registered_tasks"] = registered
            
            # 获取统计信息
            worker_stats = inspect.stats()
            if worker_stats:
                stats["stats"] = worker_stats
            
            # 添加 beat_schedule 信息
            stats["beat_schedule"] = list(self.celery_app.conf.beat_schedule.keys())
            
            return stats
            
        except Exception as e:
            logger.error(f"获取 Worker 统计信息失败: {e}")
            return {"error": str(e)}


# 全局调度管理器实例
scheduler_manager: Optional[CelerySchedulerManager] = None


def get_scheduler_manager(celery_app: Celery) -> CelerySchedulerManager:
    """获取调度管理器实例"""
    global scheduler_manager
    if scheduler_manager is None:
        scheduler_manager = CelerySchedulerManager(celery_app)
    return scheduler_manager


def initialize_celery_scheduler(celery_app: Celery) -> bool:
    """初始化 Celery 调度系统"""
    try:
        manager = get_scheduler_manager(celery_app)
        
        # 从数据库加载任务
        loaded_count = manager.load_scheduled_tasks_from_database()
        
        logger.info(f"Celery 调度系统初始化完成，加载了 {loaded_count} 个任务")
        return True
        
    except Exception as e:
        logger.error(f"初始化 Celery 调度系统失败: {e}")
        return False


# 注意：execute_scheduled_task 函数已移除
# 调度任务现在直接在 worker.py 的 execute_scheduled_task_celery 中使用智能占位符驱动的流水线


# Celery 信号处理
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """任务开始前的处理"""
    logger.info(f"开始执行任务: {task.name} (ID: {task_id})")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """任务执行后的处理"""
    logger.info(f"任务执行完成: {task.name} (ID: {task_id}), 状态: {state}")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **kwds):
    """任务失败处理"""
    logger.error(f"任务执行失败: {sender.name} (ID: {task_id}), 异常: {exception}")
    
    # 发送失败通知
    try:
        notification_service = NotificationService()
        # 这里可以添加异步通知逻辑
        logger.info(f"任务失败通知已记录: {task_id}")
    except Exception as e:
        logger.error(f"发送任务失败通知失败: {e}")


@task_success.connect  
def task_success_handler(sender=None, result=None, **kwargs):
    """任务成功处理"""
    logger.info(f"任务执行成功: {sender.name}")