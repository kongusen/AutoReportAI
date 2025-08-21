"""
Celery Application Configuration

Celery应用配置，包括：
- Celery实例创建
- 配置优化
- 调度器初始化
"""

import logging
import os
import shutil
from celery import Celery

from app.core.config import settings

logger = logging.getLogger(__name__)

# Celery应用实例配置
celery_app = Celery(
    "autoreport_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.services.application.task_management.core.worker.tasks.basic_tasks",
        "app.services.application.task_management.core.worker.tasks.enhanced_tasks",
        "app.services.application.task_management.core.worker.tasks.two_phase_tasks",
        "app.services.application.task_management.core.worker.tasks.ai_analysis_tasks"
    ]
)

# Celery配置优化
celery_app.conf.update(
    task_track_started=True,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    result_expires=3600,
    timezone='Asia/Shanghai',
    enable_utc=False,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_max_tasks_per_child=1000,
    broker_connection_retry_on_startup=True,
    # Beat调度器配置
    beat_schedule={},
    beat_scheduler='celery.beat.PersistentScheduler',
    beat_sync_every=1,
    beat_max_loop_interval=300,
    # 确保 beat_schedule 存在 - 使用绝对路径
    beat_schedule_filename='/tmp/celerybeat-schedule',
    beat_schedule_db='/tmp/celerybeat-schedule.db',
)

# 确保 beat_schedule 字典存在
if not hasattr(celery_app.conf, 'beat_schedule') or celery_app.conf.beat_schedule is None:
    celery_app.conf.beat_schedule = {}

# 清理旧的调度文件
schedule_files = [
    'celerybeat-schedule',
    'celerybeat-schedule.db',
    '/tmp/celerybeat-schedule',
    '/tmp/celerybeat-schedule.db'
]
for schedule_file in schedule_files:
    if os.path.exists(schedule_file):
        try:
            if os.path.isdir(schedule_file):
                shutil.rmtree(schedule_file)
            else:
                os.remove(schedule_file)
            logger.info(f"清理了调度文件: {schedule_file}")
        except Exception as e:
            logger.warning(f"清理调度文件失败 {schedule_file}: {e}")

# 初始化 Celery 调度系统
def init_celery_scheduler():
    """初始化 Celery 调度系统"""
    try:
        from app.core.celery_scheduler import initialize_celery_scheduler
        return initialize_celery_scheduler(celery_app)
    except Exception as e:
        logger.error(f"初始化 Celery 调度器失败: {e}")
        return False

# 在模块加载时初始化调度器
init_celery_scheduler()
