"""
统一任务调度系统
使用 APScheduler 替代 Celery Beat，提供数据库持久化的调度功能
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import threading

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
    """统一任务调度器 - 使用 APScheduler 管理所有任务调度"""

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
        self.apscheduler_manager = None
        self._running = False

    async def initialize(self):
        """异步初始化"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )

            # 使用 APScheduler
            from app.core.apscheduler_config import apscheduler_manager
            self.apscheduler_manager = apscheduler_manager

            logger.info("✅ 统一调度器初始化完成，使用 APScheduler")

        except Exception as e:
            logger.error(f"❌ 统一调度器初始化失败: {e}")
            raise

    async def add_or_update_task(self, task_id: int, cron_expression: str):
        """
        添加或更新任务调度

        Args:
            task_id: 任务ID
            cron_expression: Cron表达式
        """
        try:
            next_run = self.apscheduler_manager.add_task(task_id, cron_expression)
            logger.info(f"✅ 任务 {task_id} 调度已更新，下次执行: {next_run}")
        except Exception as e:
            logger.error(f"❌ 更新任务调度失败 {task_id}: {e}")
            raise

    async def remove_task(self, task_id: int):
        """
        移除任务调度

        Args:
            task_id: 任务ID
        """
        try:
            self.apscheduler_manager.remove_task(task_id)

            # 清理活跃任务记录
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

            logger.info(f"✅ 任务 {task_id} 调度已移除")

        except Exception as e:
            logger.error(f"❌ 移除任务调度失败 {task_id}: {e}")

    async def execute_task_immediately(self, task_id: int, user_id: str) -> Dict[str, Any]:
        """
        立即执行任务 - 优先级模式

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            执行结果字典
        """
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
            logger.error(f"❌ 立即执行任务失败 {task_id}: {e}")
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
                logger.debug(f"✅ 已存储任务 {task_id} 的所有者信息: {user_id}")
        except Exception as e:
            logger.error(f"❌ 存储任务所有者信息失败 {task_id}: {e}")

    async def _execute_with_priority(self, task_id: int, user_id: str) -> Dict[str, Any]:
        """智能优先级执行 - 检查worker状态并优化执行"""
        try:
            from app.services.application.tasks.workflow_tasks import generate_report_workflow
            from app.services.infrastructure.task_queue.celery_config import celery_app

            # 检查当前活跃的worker数量
            active_workers = celery_app.control.inspect().active_queues()
            worker_count = len(active_workers) if active_workers else 0

            # 检查当前队列中等待的任务数量
            queue_stats = celery_app.control.inspect().active()
            pending_tasks = sum(len(tasks) for tasks in queue_stats.values()) if queue_stats else 0

            logger.info(f"📊 当前活跃worker数量: {worker_count}, 队列中任务数量: {pending_tasks}")

            # 获取任务信息
            with get_db_session() as db:
                task_obj = crud.task.get(db, id=task_id)
                if not task_obj:
                    raise Exception(f"Task {task_id} not found")

                # 智能调度决策
                if worker_count > 0 and pending_tasks < worker_count:
                    # 有空闲worker，使用高优先级立即执行
                    celery_result = generate_report_workflow.apply_async(
                        args=[
                            str(task_obj.template_id) if task_obj.template_id else '',
                            [str(task_obj.data_source_id)] if task_obj.data_source_id else [],
                            {'user_id': user_id, 'task_id': str(task_id), 'priority': 'high'}
                        ],
                        priority=9,  # 高优先级
                        queue='application_queue'
                    )
                    return {
                        "celery_task_id": celery_result.id,
                        "queued": False,
                        "processing_mode": "intelligent",
                        "message": "任务已立即开始执行"
                    }
                else:
                    # worker繁忙，正常加入队列
                    celery_result = generate_report_workflow.delay(
                        str(task_obj.template_id) if task_obj.template_id else '',
                        [str(task_obj.data_source_id)] if task_obj.data_source_id else [],
                        {'user_id': user_id, 'task_id': str(task_id)}
                    )
                    return {
                        "celery_task_id": celery_result.id,
                        "queued": True,
                        "processing_mode": "intelligent",
                        "message": "智能占位符报告生成任务已加入队列"
                    }

        except Exception as e:
            logger.error(f"⚠️ 优先级执行检查失败: {e}, 使用普通执行")
            # 回退到普通执行
            from app.services.application.tasks.workflow_tasks import generate_report_workflow

            with get_db_session() as db:
                task_obj = crud.task.get(db, id=task_id)
                if not task_obj:
                    raise Exception(f"Task {task_id} not found")

                celery_result = generate_report_workflow.delay(
                    str(task_obj.template_id) if task_obj.template_id else '',
                    [str(task_obj.data_source_id)] if task_obj.data_source_id else [],
                    {'user_id': user_id, 'task_id': str(task_id)}
                )

            return {
                "celery_task_id": celery_result.id,
                "queued": True,
                "processing_mode": "intelligent",
                "message": "智能占位符报告生成任务已加入队列"
            }

    async def get_task_status(self, task_id: int) -> Dict[str, Any]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态字典
        """
        try:
            # 先从Redis获取实时状态
            if self.redis_client:
                redis_status = await self.redis_client.hgetall(f"report_task:{task_id}:status")
                if redis_status:
                    return redis_status

            # 检查活跃任务
            if task_id in self.active_tasks:
                return self.active_tasks[task_id]

            # 从 APScheduler 获取调度状态
            task_info = self.apscheduler_manager.get_task_info(task_id)
            if task_info:
                return {
                    "status": "scheduled",
                    "progress": 0,
                    "current_step": "等待调度执行",
                    "next_run_time": task_info.get("next_run_time")
                }

            return {"status": "not_found", "message": "未找到任务状态"}

        except Exception as e:
            logger.error(f"❌ 获取任务状态失败 {task_id}: {e}")
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
            logger.error(f"⚠️ 发送开始通知失败: {e}")

    async def get_scheduler_info(self) -> Dict[str, Any]:
        """获取调度器信息"""
        scheduler_state = self.apscheduler_manager.get_scheduler_state()
        all_jobs = self.apscheduler_manager.list_all_jobs()

        return {
            "scheduler_type": "apscheduler",
            "scheduler_state": scheduler_state,
            "active_tasks_count": len(self.active_tasks),
            "active_tasks": list(self.active_tasks.keys()),
            "scheduled_jobs": all_jobs
        }

    async def reload_all_tasks(self):
        """重新加载所有任务"""
        try:
            result = self.apscheduler_manager.load_tasks_from_database()
            logger.info(f"✅ 所有任务调度已重新加载: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ 重新加载任务失败: {e}")
            raise

    async def shutdown(self):
        """关闭调度器"""
        try:
            if self.apscheduler_manager:
                self.apscheduler_manager.shutdown(wait=True)

            if self.redis_client:
                await self.redis_client.close()

            self.active_tasks.clear()
            logger.info("✅ 统一调度器已关闭")

        except Exception as e:
            logger.error(f"❌ 关闭调度器失败: {e}")


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
