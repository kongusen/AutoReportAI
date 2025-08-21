"""
Two-Phase Architecture Celery Tasks

基于两阶段架构的Celery任务实现
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from app import crud, schemas
from app.db.session import SessionLocal
from app.services.notification.notification_service import NotificationService
from app.services.task.execution.two_phase_pipeline import (
    TwoPhasePipeline,
    PipelineConfiguration,
    ExecutionMode
)
from app.services.task.execution.unified_pipeline import (
    unified_report_generation_pipeline,
    PipelineMode
)
from ..config.celery_app import celery_app
from ..utils.progress_utils import update_task_progress, send_error_notification

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name='app.services.task.core.worker.tasks.two_phase_tasks.execute_two_phase_report_task')
def execute_two_phase_report_task(self, task_id: int, user_id: str = None, force_reanalyze: bool = False):
    """
    执行两阶段架构的报告生成任务
    
    这是主要的Celery任务入口，使用新的两阶段架构
    """
    # 如果没有提供user_id，使用系统用户ID
    if user_id is None:
        from app.core.config import settings
        user_id = settings.SYSTEM_USER_ID
    
    logger.info(f"开始执行两阶段报告任务: {task_id}")
    
    try:
        # 使用统一流水线接口，默认使用两阶段架构
        result = unified_report_generation_pipeline(
            task_id=task_id,
            user_id=user_id,
            mode=PipelineMode.TWO_PHASE,
            force_reanalyze=force_reanalyze,
            enable_progress_tracking=True,
            enable_notifications=True
        )
        
        logger.info(f"两阶段报告任务完成: {task_id}, 模式: {result.get('pipeline_mode')}")
        return result
        
    except Exception as e:
        logger.error(f"两阶段报告任务失败: {task_id}, 错误: {str(e)}")
        
        # 发送错误通知
        send_error_notification(task_id, str(e))
        
        # 尝试发送失败通知
        try:
            notification_service = NotificationService()
            notification_service.send_task_failure_notification(
                task_id=task_id,
                user_id=user_id,
                error_message=str(e)
            )
        except Exception as notify_error:
            logger.warning(f"发送失败通知失败: {notify_error}")
        
        return {
            "success": False,
            "task_id": task_id,
            "error": str(e),
            "pipeline_mode": "two_phase"
        }


@celery_app.task(bind=True, name='app.services.task.core.worker.tasks.two_phase_tasks.execute_phase_1_analysis_task')
def execute_phase_1_analysis_task(self, template_id: str, data_source_id: str, user_id: str = None, force_reanalyze: bool = False):
    """
    仅执行阶段1: 模板分析和占位符处理
    
    用于预先分析模板，为后续的报告生成做准备
    """
    # 如果没有提供user_id，使用系统用户ID
    if user_id is None:
        from app.core.config import settings
        user_id = settings.SYSTEM_USER_ID
    
    logger.info(f"开始执行阶段1分析任务: 模板 {template_id}")
    
    start_time = datetime.now()
    db = SessionLocal()
    
    try:
        # 创建配置为仅执行阶段1
        config = PipelineConfiguration(
            execution_mode=ExecutionMode.PHASE_1_ONLY,
            force_reanalyze=force_reanalyze,
            enable_caching=True,
            enable_progress_tracking=False,  # 不需要任务级别的进度跟踪
            enable_notifications=False
        )
        
        # 执行阶段1
        pipeline = TwoPhasePipeline(config)
        
        # 创建一个虚拟任务上下文来执行阶段1
        result = asyncio.run(pipeline._execute_phase_1(
            {
                "template_id": template_id,
                "data_source_id": data_source_id,
                "user_id": user_id,
                "template": crud.template.get(db, id=template_id),
                "data_source": crud.data_source.get(db, id=data_source_id)
            },
            db
        ))
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"阶段1分析任务完成: 模板 {template_id}, 耗时: {execution_time:.2f}秒")
        
        return {
            "success": result.success,
            "template_id": template_id,
            "data_source_id": data_source_id,
            "execution_time": execution_time,
            "phase_result": result.data if result.success else None,
            "error": result.error if not result.success else None,
            "task_type": "phase_1_analysis"
        }
        
    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"阶段1分析任务失败: 模板 {template_id}, 错误: {str(e)}")
        
        return {
            "success": False,
            "template_id": template_id,
            "data_source_id": data_source_id,
            "execution_time": execution_time,
            "error": str(e),
            "task_type": "phase_1_analysis"
        }
        
    finally:
        db.close()


@celery_app.task(bind=True, name='app.services.task.core.worker.tasks.two_phase_tasks.execute_smart_report_task')
def execute_smart_report_task(self, task_id: int, user_id: str = None):
    """
    智能报告生成任务 - 自动选择执行策略
    
    根据模板的准备状态，智能选择执行完整流水线还是仅执行阶段2
    """
    # 如果没有提供user_id，使用系统用户ID
    if user_id is None:
        from app.core.config import settings
        user_id = settings.SYSTEM_USER_ID
    
    logger.info(f"开始执行智能报告任务: {task_id}")
    
    try:
        # 使用统一流水线接口，启用智能模式
        result = unified_report_generation_pipeline(
            task_id=task_id,
            user_id=user_id,
            mode=PipelineMode.AUTO,  # 自动选择模式
            optimization_enabled=True,
            enable_progress_tracking=True,
            enable_notifications=True
        )
        
        logger.info(f"智能报告任务完成: {task_id}, 使用模式: {result.get('pipeline_mode')}")
        return result
        
    except Exception as e:
        logger.error(f"智能报告任务失败: {task_id}, 错误: {str(e)}")
        
        # 发送错误通知
        send_error_notification(task_id, str(e))
        
        return {
            "success": False,
            "task_id": task_id,
            "error": str(e),
            "pipeline_mode": "auto_smart"
        }


@celery_app.task(bind=True, name='app.services.task.core.worker.tasks.two_phase_tasks.execute_batch_template_preparation')
def execute_batch_template_preparation(self, template_ids: list, data_source_id: str, user_id: str = None):
    """
    批量模板预备任务 - 预先分析多个模板
    
    为多个模板执行阶段1分析，提高后续报告生成的效率
    """
    # 如果没有提供user_id，使用系统用户ID
    if user_id is None:
        from app.core.config import settings
        user_id = settings.SYSTEM_USER_ID
    
    logger.info(f"开始批量模板预备: {len(template_ids)} 个模板")
    
    start_time = datetime.now()
    results = []
    
    for i, template_id in enumerate(template_ids):
        try:
            logger.info(f"处理模板 {i+1}/{len(template_ids)}: {template_id}")
            
            # 为每个模板执行阶段1分析
            task_result = execute_phase_1_analysis_task.delay(
                template_id, data_source_id, user_id, force_reanalyze=False
            )
            
            # 等待任务完成
            result = task_result.get(timeout=300)  # 5分钟超时
            results.append(result)
            
        except Exception as e:
            logger.error(f"批量预备中模板失败: {template_id}, 错误: {str(e)}")
            results.append({
                "success": False,
                "template_id": template_id,
                "error": str(e)
            })
    
    execution_time = (datetime.now() - start_time).total_seconds()
    successful_count = len([r for r in results if r.get("success", False)])
    
    logger.info(f"批量模板预备完成: {successful_count}/{len(template_ids)} 成功, 耗时: {execution_time:.2f}秒")
    
    return {
        "success": True,
        "total_templates": len(template_ids),
        "successful_templates": successful_count,
        "failed_templates": len(template_ids) - successful_count,
        "execution_time": execution_time,
        "results": results,
        "success_rate": (successful_count / len(template_ids) * 100) if template_ids else 0,
        "task_type": "batch_template_preparation"
    }


@celery_app.task(bind=True, name='app.services.task.core.worker.tasks.two_phase_tasks.execute_scheduled_two_phase_task')
def execute_scheduled_two_phase_task(self, task_id: int):
    """执行调度的两阶段任务"""
    logger.info(f"开始执行调度的两阶段任务: {task_id}")
    
    try:
        with SessionLocal() as db:
            task = crud.task.get(db, id=task_id)
            if not task:
                logger.error(f"调度任务 {task_id} 不存在")
                return {"status": "error", "message": f"任务 {task_id} 不存在"}
            
            if not task.is_active:
                logger.warning(f"调度任务 {task_id} 未激活，跳过执行")
                return {"status": "skipped", "message": f"任务 {task_id} 未激活"}
        
        # 提交到两阶段报告任务
        result = execute_two_phase_report_task.delay(task_id, "system", force_reanalyze=False)
        logger.info(f"调度任务 {task_id} 已提交到两阶段流水线，Celery task ID: {result.id}")
        
        return {
            "status": "submitted",
            "task_id": task_id,
            "celery_task_id": result.id,
            "pipeline_type": "two_phase",
            "submitted_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"执行调度的两阶段任务失败: {task_id}, 错误: {str(e)}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name='app.services.task.core.worker.tasks.two_phase_tasks.migrate_to_two_phase_task')
def migrate_to_two_phase_task(self, task_id: int, user_id: str = None):
    """
    迁移任务到两阶段架构
    
    为现有任务执行两阶段架构迁移，包括模板分析和优化设置
    """
    # 如果没有提供user_id，使用系统用户ID
    if user_id is None:
        from app.core.config import settings
        user_id = settings.SYSTEM_USER_ID
    
    logger.info(f"开始迁移任务到两阶段架构: {task_id}")
    
    db = SessionLocal()
    start_time = datetime.now()
    
    try:
        # 获取任务信息
        task = crud.task.get(db, id=task_id)
        if not task:
            return {"success": False, "error": f"任务不存在: {task_id}"}
        
        template_id = str(task.template_id)
        data_source_id = str(task.data_source_id)
        
        # 1. 首先执行阶段1分析，确保模板准备就绪
        logger.info(f"为任务 {task_id} 执行模板分析...")
        phase1_task = execute_phase_1_analysis_task.delay(
            template_id, data_source_id, user_id, force_reanalyze=True
        )
        phase1_result = phase1_task.get(timeout=300)
        
        if not phase1_result.get("success", False):
            return {
                "success": False,
                "task_id": task_id,
                "error": f"模板分析失败: {phase1_result.get('error')}",
                "phase": "template_analysis"
            }
        
        # 2. 执行一次完整的两阶段流水线验证
        logger.info(f"为任务 {task_id} 执行两阶段流水线验证...")
        validation_result = unified_report_generation_pipeline(
            task_id=task_id,
            user_id=user_id,
            mode=PipelineMode.TWO_PHASE,
            force_reanalyze=False,  # 使用刚才的分析结果
            enable_progress_tracking=False,
            enable_notifications=False
        )
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        if validation_result.get("status") == "completed":
            logger.info(f"任务 {task_id} 成功迁移到两阶段架构，耗时: {execution_time:.2f}秒")
            
            return {
                "success": True,
                "task_id": task_id,
                "execution_time": execution_time,
                "phase1_result": phase1_result,
                "validation_result": validation_result,
                "migration_completed": True,
                "message": "任务成功迁移到两阶段架构"
            }
        else:
            return {
                "success": False,
                "task_id": task_id,
                "execution_time": execution_time,
                "error": f"流水线验证失败: {validation_result.get('error')}",
                "phase": "pipeline_validation"
            }
        
    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"迁移任务到两阶段架构失败: {task_id}, 错误: {str(e)}")
        
        return {
            "success": False,
            "task_id": task_id,
            "execution_time": execution_time,
            "error": str(e),
            "phase": "migration"
        }
        
    finally:
        db.close()