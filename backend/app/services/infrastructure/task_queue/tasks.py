"""
Infrastructure层 - Celery任务定义

基于DDD架构的Celery任务定义，使用新的TaskExecutionService能力
"""

import logging
import asyncio
import os
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
from celery import Task as CeleryTask
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.task import Task, TaskExecution, TaskStatus
from app.services.application.placeholder import PlaceholderApplicationService as PlaceholderProcessingSystem
from app.utils.time_context import TimeContextManager
from app.services.infrastructure.task_queue.celery_config import celery_app
from app.services.infrastructure.storage.hybrid_storage_service import get_hybrid_storage_service
from app.services.infrastructure.notification.notification_service import NotificationService
from celery.schedules import crontab

logger = logging.getLogger(__name__)

class DatabaseTask(CeleryTask):
    """带数据库会话的基础任务类"""
    
    def __call__(self, *args, **kwargs):
        """执行任务时自动管理数据库会话"""
        with SessionLocal() as db:
            return self.run_with_db(db, *args, **kwargs)
    
    def run_with_db(self, db: Session, *args, **kwargs):
        """子类需要实现的方法"""
        return self.run(*args, **kwargs)

@celery_app.task(bind=True, base=DatabaseTask, name='tasks.infrastructure.execute_report_task')
def execute_report_task(self, db: Session, task_id: int, execution_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    执行报告生成任务 - 使用新的TaskExecutionService
    
    Args:
        task_id: 任务ID
        execution_context: 执行上下文（可选）
    
    Returns:
        Dict: 执行结果
    """
    task_execution_id = None
    notification_service = NotificationService()
    
    try:
        # 1. 获取任务信息
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        if not task.is_active:
            logger.info(f"Task {task_id} is not active, skipping execution")
            return {"status": "skipped", "reason": "task_inactive"}
        
        # 2. 创建任务执行记录
        task_execution = TaskExecution(
            task_id=task_id,
            execution_status=TaskStatus.PROCESSING,
            workflow_type=task.workflow_type,
            started_at=datetime.utcnow(),
            celery_task_id=self.request.id,
            execution_context=execution_context or {},
            progress_percentage=0
        )
        db.add(task_execution)
        db.commit()
        task_execution_id = task_execution.id
        
        # 3. 更新任务状态
        task.status = TaskStatus.PROCESSING
        task.execution_count += 1
        task.last_execution_at = datetime.utcnow()
        db.commit()
        
        # 4. 初始化新Agent系统与时间上下文
        system = PlaceholderProcessingSystem(user_id=str(task.owner_id))
        time_ctx_mgr = TimeContextManager()
        
        # 5. 准备执行参数
        execution_params = {
            "task_id": task_id,
            "template_id": str(task.template_id),
            "data_source_id": str(task.data_source_id),
            "report_period": task.report_period.value if task.report_period else "monthly",
            "user_id": str(task.owner_id),
            "execution_id": str(task_execution.execution_id),
            "recipients": task.recipients or [],
            "schedule": task.schedule
        }
        
        logger.info(f"Starting task execution for task {task_id} with Agents pipeline")

        # 5. 生成时间窗口（基于任务报告周期）
        time_ctx = time_ctx_mgr.generate_time_context(
            report_period=task.report_period.value if task.report_period else "monthly",
            execution_time=datetime.utcnow(),
            schedule=task.schedule,
        )
        time_window = {
            "start": f"{time_ctx.get('period_start_date')} 00:00:00",
            "end": f"{time_ctx.get('period_end_date')} 23:59:59",
        }

        # 6. 运行ReAct流水线（生成SQL→注入时间→执行→自修正）
        asyncio.run(system.initialize())
        events = []

        # Build required_fields from template placeholders if available
        required_fields: List[str] = []
        try:
            from app.crud import template_placeholder as crud_template_placeholder
            placeholders = crud_template_placeholder.get_by_template(db, str(task.template_id))
            fields: set[str] = set()
            for ph in placeholders or []:
                rf = getattr(ph, 'required_fields', None)
                # Accept list or dict forms
                if isinstance(rf, list):
                    for f in rf:
                        if isinstance(f, str):
                            fields.add(f)
                elif isinstance(rf, dict):
                    for key in ('columns', 'fields', 'required_fields'):
                        val = rf.get(key)
                        if isinstance(val, list):
                            for f in val:
                                if isinstance(f, str):
                                    fields.add(f)
                            break
                # Fallback to parsing_metadata if present
                pm = getattr(ph, 'parsing_metadata', None)
                if isinstance(pm, dict):
                    meta_rf = pm.get('required_fields') or pm.get('metadata', {}).get('required_fields')
                    if isinstance(meta_rf, list):
                        for f in meta_rf:
                            if isinstance(f, str):
                                fields.add(f)
            required_fields = sorted(fields)
        except Exception as e:
            logger.warning(f"Failed to load required_fields from placeholders: {e}")

        success_criteria = {
            "min_rows": 1,
            "max_rows": 100000,
            "required_fields": required_fields,
            "quality_threshold": 0.6,
        }
        objective = f"执行任务[{task.name}]的数据准备与分析"
        async def _run():
            async for ev in system.run_task_with_agent(
                task_objective=objective,
                success_criteria=success_criteria,
                data_source_id=str(task.data_source_id),
                time_window=time_window,
                time_column="created_at",
                max_attempts=3,
            ):
                events.append(ev)
        asyncio.run(_run())

        final = next((e for e in reversed(events) if e.get("type") == "agent_session_complete"), None)
        execution_result = {
            "success": bool(final and final.get("success")),
            "events": events,
            "final": final,
            "time_window": time_window,
        }

        # 7b. 生成文档（使用模板 + doc_assembler）
        try:
            from app.services.infrastructure.document.template_path_resolver import resolve_docx_template_path
            from app.services.infrastructure.agents.tools.doc_assembler import DocAssemblerTool
            from io import BytesIO
            from app.services.infrastructure.storage.hybrid_storage_service import get_hybrid_storage_service

            # 仅在有模板文件时生成
            if getattr(task, 'template_id', None):
                tpl_meta = resolve_docx_template_path(db, str(task.template_id))
                assembler = DocAssemblerTool()
                # 简单内容块（可改为基于 events 的摘要/指标）
                context_blocks = [
                    {"type": "text", "title": f"任务 {task.name}", "content": f"执行时间: {datetime.utcnow().isoformat()}"},
                ]
                safe_tmp_dir = os.path.join(os.path.expanduser('~'), ".autoreportai", "tmp")
                docx_out = os.path.join(safe_tmp_dir, f"report_{task.id}_{int(datetime.utcnow().timestamp())}.docx")
                assemble_res = asyncio.run(assembler.execute({
                    "format": "docx",
                    "template_path": tpl_meta['path'],
                    "context_blocks": context_blocks,
                    "charts": [],
                    "output_path": docx_out,
                }))
                if assemble_res.get('success') and assemble_res.get('output_path'):
                    # 上传到存储
                    storage = get_hybrid_storage_service()
                    with open(assemble_res['output_path'], 'rb') as f:
                        file_bytes = f.read()
                    # 采用对象键: reports/{tenant_id}/{task_name}/report_{timestamp}.docx
                    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                    # 获取租户（若无租户字段，则使用用户ID代替）
                    from app.models.user import User
                    user = db.query(User).filter(User.id == task.owner_id).first()
                    tenant_id = getattr(user, 'tenant_id', str(task.owner_id)) if user else str(task.owner_id)
                    # 任务名slug
                    import re
                    slug = re.sub(r'[^\w\-]+', '-', (task.name or f'task_{task.id}')).strip('-')[:50]
                    object_name = f"reports/{tenant_id}/{slug}/report_{ts}.docx"
                    upload = storage.upload_with_key(BytesIO(file_bytes), object_name, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                    execution_result["report"] = {
                        "storage_path": upload.get("file_path"),
                        "backend": upload.get("backend"),
                        "friendly_name": f"{slug}_{ts}.docx",
                    }
        except Exception as e:
            logger.error(f"Document assembly failed: {e}")
        
        # 7. 更新执行结果
        task_execution.execution_status = TaskStatus.COMPLETED
        task_execution.completed_at = datetime.utcnow()
        task_execution.total_duration = int((task_execution.completed_at - task_execution.started_at).total_seconds())
        task_execution.execution_result = execution_result
        task_execution.progress_percentage = 100
        
        # 更新任务统计
        task.status = TaskStatus.COMPLETED
        task.success_count += 1
        task.last_execution_duration = task_execution.total_duration
        
        # 更新平均执行时间
        if task.average_execution_time == 0:
            task.average_execution_time = task_execution.total_duration
        else:
            task.average_execution_time = (task.average_execution_time + task_execution.total_duration) / 2
        
        db.commit()
        
        # 8. 发送成功通知（携带下载链接）
        if task.recipients:
            try:
                # 生成下载URL（若有report）
                download_url = None
                try:
                    if execution_result.get("report", {}).get("storage_path"):
                        storage = get_hybrid_storage_service()
                        download_url = storage.get_download_url(execution_result["report"]["storage_path"], expires=86400)
                except Exception as e:
                    logger.warning(f"Failed to generate download URL: {e}")

                # 使用DeliveryService 发送邮件（若可用）或通知服务
                from app.services.infrastructure.delivery.delivery_service import create_delivery_service, DeliveryRequest, DeliveryMethod, StorageConfig, EmailConfig, NotificationConfig
                delivery_service = create_delivery_service(str(task.owner_id))
                # 友好名称: 任务名+时间
                friendly_name = execution_result.get("report", {}).get("friendly_name") or f"report_{task.id}.docx"
                ts_email = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                email_config = EmailConfig(
                    recipients=task.recipients,
                    subject=f"报告生成完成 - {task.name} - {ts_email}",
                    body=(
                        f"报告已生成: {friendly_name}\n\n"
                        f"下载链接: {download_url if download_url else '请登录系统查看'}\n"
                        f"任务: {task.name}\n时间窗口: {time_window['start']} - {time_window['end']}\n"
                    ),
                    attach_files=False
                )
                req = DeliveryRequest(
                    task_id=str(task_id),
                    user_id=str(task.owner_id),
                    files=[],
                    delivery_method=DeliveryMethod.EMAIL_ONLY,
                    storage_config=StorageConfig(bucket_name="reports", path_prefix=f"reports/{task.owner_id}", public_access=False, retention_days=90),
                    email_config=email_config,
                    notification_config=NotificationConfig(channels=["system"], message="报告已生成", priority="normal"),
                    metadata={"report_path": execution_result.get("report", {}).get("storage_path")}
                )
                # 在同步任务中执行异步投递
                asyncio.run(delivery_service.deliver_report(req))
            except Exception as e:
                logger.error(f"Failed to send success notification for task {task_id}: {e}")
        
        logger.info(f"Task {task_id} completed successfully in {task_execution.total_duration}s")
        
        return {
            "status": "completed",
            "task_id": task_id,
            "execution_id": str(task_execution.execution_id),
            "execution_time": task_execution.total_duration,
            "result": execution_result
        }
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}", exc_info=True)
        
        # 更新失败状态
        if task_execution_id:
            task_execution = db.query(TaskExecution).filter(TaskExecution.id == task_execution_id).first()
            if task_execution:
                task_execution.execution_status = TaskStatus.FAILED
                task_execution.completed_at = datetime.utcnow()
                task_execution.error_details = str(e)
                task_execution.total_duration = int((task_execution.completed_at - task_execution.started_at).total_seconds()) if task_execution.started_at else 0
        
        # 更新任务统计
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = TaskStatus.FAILED
            task.failure_count += 1
            
        db.commit()
        
        # 发送失败通知
        if task and task.recipients:
            try:
                notification_service.send_task_completion_notification(
                    task_id=task_id,
                    task_name=task.name,
                    recipients=task.recipients,
                    execution_result={"error": str(e)},
                    success=False
                )
            except Exception as notification_error:
                logger.error(f"Failed to send failure notification for task {task_id}: {notification_error}")
        
        # 重新抛出异常让Celery处理重试
        raise

@celery_app.task(bind=True, name='tasks.infrastructure.validate_placeholders_task')
def validate_placeholders_task(self, template_id: str, data_source_id: str, user_id: str) -> Dict[str, Any]:
    """
    验证模板占位符任务
    
    Args:
        template_id: 模板ID
        data_source_id: 数据源ID
        user_id: 用户ID
    
    Returns:
        Dict: 验证结果
    """
    try:
        # 迁移说明：旧的占位符验证流程已弃用。
        # 新架构在执行阶段由 Agents 进行 SQL 生成→注入→执行的自验证（ReAct）。
        logger.info(f"Placeholder validation (legacy) skipped for template {template_id}; replaced by Agents pipeline")
        return {
            "status": "migrated",
            "template_id": template_id,
            "message": "Validation is handled by Agents pipeline during execution",
        }
        
    except Exception as e:
        logger.error(f"Placeholder validation failed for template {template_id}: {str(e)}", exc_info=True)
        raise

@celery_app.task(bind=True, base=DatabaseTask, name='tasks.infrastructure.scheduled_task_runner')
def scheduled_task_runner(self, db: Session, task_id: int) -> Dict[str, Any]:
    """
    定时任务执行器 - 由调度器触发
    
    Args:
        task_id: 任务ID
    
    Returns:
        Dict: 执行结果
    """
    try:
        # 检查任务是否应该执行
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task or not task.is_active:
            return {"status": "skipped", "reason": "task_inactive_or_not_found"}
        
        # 检查是否有正在进行的执行
        ongoing_execution = db.query(TaskExecution).filter(
            TaskExecution.task_id == task_id,
            TaskExecution.execution_status.in_([TaskStatus.PENDING, TaskStatus.PROCESSING])
        ).first()
        
        if ongoing_execution:
            logger.warning(f"Task {task_id} has ongoing execution, skipping")
            return {"status": "skipped", "reason": "execution_in_progress"}
        
        # 构建执行上下文（包含调度信息）
        execution_context = {
            "trigger": "scheduled",
            "schedule": task.schedule,
            "triggered_at": datetime.utcnow().isoformat()
        }
        
        # 委托给主执行任务
        result = execute_report_task.delay(task_id, execution_context)
        
        logger.info(f"Scheduled task {task_id} delegated to execution task {result.id}")
        
        return {
            "status": "delegated",
            "task_id": task_id,
            "execution_task_id": result.id
        }
        
    except Exception as e:
        logger.error(f"Scheduled task runner failed for task {task_id}: {str(e)}", exc_info=True)
        raise

@celery_app.task(name='tasks.infrastructure.cleanup_old_executions')
def cleanup_old_executions(days_to_keep: int = 30) -> Dict[str, Any]:
    """
    清理旧的任务执行记录
    
    Args:
        days_to_keep: 保留天数，默认30天
    
    Returns:
        Dict: 清理结果
    """
    try:
        with SessionLocal() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # 删除旧的执行记录
            deleted_count = db.query(TaskExecution).filter(
                TaskExecution.created_at < cutoff_date,
                TaskExecution.execution_status.in_([TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED])
            ).delete()
            
            db.commit()
            
            logger.info(f"Cleaned up {deleted_count} old task executions")
            
            return {
                "status": "completed",
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date.isoformat()
            }
            
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}", exc_info=True)
        raise

# 注册周期性任务
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """设置周期性任务"""
    
    # 每天凌晨2点清理旧的执行记录
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        cleanup_old_executions.s(),
        name='cleanup_old_executions_daily',
    )
    
    logger.info("✅ Periodic tasks configured")

logger.info("✅ Task infrastructure layer loaded")
