"""
Infrastructure层 - Celery配置

基础设施层的Celery任务队列配置
遵循DDD原则，专注于技术实现细节
"""

import logging
from celery import Celery
from app.core.config import settings

logger = logging.getLogger(__name__)

# 创建Celery应用实例
celery_app = Celery(
    "autoreport_ddd",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# 基础设施层配置 - 专注技术细节
celery_app.conf.update(
    # 序列化配置
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    
    # 时区配置
    timezone='UTC',
    enable_utc=True,
    
    # 性能配置
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # 队列路由 - 按DDD层次划分
    task_routes={
        # Domain层任务队列
        'tasks.domain.*': {'queue': 'domain_queue'},
        # Application层任务队列
        'tasks.application.*': {'queue': 'application_queue'},
        # Infrastructure层任务队列
        'tasks.infrastructure.*': {'queue': 'infrastructure_queue'},
        # Data层任务队列
        'tasks.data.*': {'queue': 'data_queue'},
        # 默认队列
        '*': {'queue': 'default'},
    },
    
    # 重试配置
    task_default_retry_delay=60,
    task_max_retries=3,
    
    # 结果存储
    result_expires=3600,
    task_track_started=True,
    
    # 监控配置
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # 错误处理
    task_reject_on_worker_lost=True,
)

# 自动发现任务
celery_app.autodiscover_tasks([
    'app.services.domain.tasks',
    'app.services.application.tasks',
    'app.services.infrastructure.task_queue.tasks',
    'app.services.data.tasks',
])

# 手动导入关键任务以确保正确加载
try:
    from app.services.infrastructure.task_queue.tasks import (
        execute_report_task,
        scheduled_task_runner
    )
    logger.info("✅ Critical tasks imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ Failed to import some tasks: {e}")

# 健康检查任务
@celery_app.task(name='infrastructure.health.ping')
def health_ping():
    """基础设施健康检查"""
    return {"status": "healthy", "service": "celery_worker", "layer": "infrastructure"}

logger.info("✅ Celery infrastructure configuration loaded")