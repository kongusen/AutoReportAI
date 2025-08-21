"""
Enhanced Celery Tasks

增强版Celery任务定义，包括：
- 调度任务执行
- 智能报告生成流水线
- 增强版智能报告生成流水线
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict

from celery import chord, group
from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.time_utils import now, format_iso
from app.db.session import SessionLocal
from app.services.agents.orchestration import AgentOrchestrator
from app.services.notification.notification_service import NotificationService
from app.services.report_generation.document_pipeline import TemplateParser
from app.services.report_generation.word_generator_service import WordGeneratorService
from ..config.celery_app import celery_app
from ..utils.progress_utils import update_task_progress, send_error_notification

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name='app.services.task.core.worker.tasks.enhanced_tasks.execute_scheduled_task')
def execute_scheduled_task(self, task_id: int):
    """执行调度的任务 - 由 Celery Beat 调用，使用智能占位符驱动的版本"""
    logger.info(f"开始执行调度任务 {task_id}，使用智能占位符驱动的流水线")
    
    # 直接调用智能占位符驱动的报告生成流水线
    # 使用系统用户执行调度任务
    from app.core.config import settings
    system_user_id = settings.SYSTEM_USER_ID
    
    # 更新任务执行状态
    try:
        with SessionLocal() as db:
            task = crud.task.get(db, id=task_id)
            if not task:
                logger.error(f"调度任务 {task_id} 不存在")
                return {"status": "error", "message": f"任务 {task_id} 不存在"}
            
            if not task.is_active:
                logger.warning(f"调度任务 {task_id} 未激活，跳过执行")
                return {"status": "skipped", "message": f"任务 {task_id} 未激活"}
        
        # 提交到智能报告生成流水线
        result = intelligent_report_generation_pipeline.delay(task_id, system_user_id)
        logger.info(f"调度任务 {task_id} 已提交到智能流水线，Celery task ID: {result.id}")
        
        return {
            "status": "submitted",
            "task_id": task_id,
            "celery_task_id": result.id,
            "submitted_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"执行调度任务 {task_id} 失败: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name='app.services.task.core.worker.tasks.enhanced_tasks.intelligent_report_generation_pipeline')
def intelligent_report_generation_pipeline(self, task_id: int, user_id: str, execution_context: Dict[str, Any] = None):
    """
    智能占位符驱动的报告生成流水线 - 使用增强版本，支持执行上下文
    """
    # 使用增强版本的函数，传递执行上下文
    from app.services.task.execution.unified_pipeline import unified_report_generation_pipeline, PipelineMode
    return unified_report_generation_pipeline(
        task_id, 
        user_id, 
        mode=PipelineMode.ENHANCED,
        execution_context=execution_context
    )


@celery_app.task(bind=True, name='app.services.task.core.worker.tasks.enhanced_tasks.enhanced_intelligent_report_generation_pipeline')
def enhanced_intelligent_report_generation_pipeline(self, task_id: int, user_id: str):
    """
    增强版智能报告生成流水线 - 包含用户特定AI配置和详细进度管理
    """
    logger.info(f"开始增强版智能报告生成流水线 - 任务ID: {task_id}, 用户ID: {user_id}")
    
    # 使用统一的流水线接口，增强模式
    try:
        from app.services.task.execution.unified_pipeline import unified_report_generation_pipeline, PipelineMode
        result = unified_report_generation_pipeline(task_id, user_id, mode=PipelineMode.ENHANCED)
        
        logger.info(f"增强版流水线执行完成 - 任务ID: {task_id}, 模式: {result.get('pipeline_mode', 'unknown')}")
        return result
        
    except Exception as e:
        logger.error(f"增强版智能报告生成失败 - 任务ID: {task_id}: {e}")
        raise
