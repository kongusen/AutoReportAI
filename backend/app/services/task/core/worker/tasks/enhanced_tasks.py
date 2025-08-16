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
    system_user_id = "system"
    
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
def intelligent_report_generation_pipeline(self, task_id: int, user_id: str):
    """
    智能占位符驱动的报告生成流水线 - 使用增强版本
    """
    # 使用增强版本的函数
    from app.services.task.execution.pipeline import enhanced_intelligent_report_generation_pipeline
    return enhanced_intelligent_report_generation_pipeline(task_id, user_id)


@celery_app.task(bind=True, name='app.services.task.core.worker.tasks.enhanced_tasks.enhanced_intelligent_report_generation_pipeline')
def enhanced_intelligent_report_generation_pipeline(self, task_id: int, user_id: str):
    """
    增强版智能报告生成流水线 - 包含用户特定AI配置和详细进度管理
    """
    logger.info(f"开始增强版智能报告生成流水线 - 任务ID: {task_id}, 用户ID: {user_id}")
    
    start_time = time.time()
    db = SessionLocal()
    
    try:
        # 获取任务信息
        task = crud.task.get(db, id=task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        
        # 获取用户配置
        user_profile = crud.user_profile.get_by_user_id(db, user_id=user_id)
        ai_config = user_profile.ai_config if user_profile else {}
        
        # 获取模板和数据源
        template = crud.template.get(db, id=task.template_id)
        data_source = crud.data_source.get(db, id=task.data_source_id)
        
        if not template or not data_source:
            raise ValueError("模板或数据源不存在")
        
        # 更新任务状态
        update_task_progress(task_id, "processing", 5, "初始化任务")
        
        # 解析模板占位符
        update_task_progress(task_id, "processing", 10, "解析模板占位符")
        parser = TemplateParser()
        placeholders = parser.extract_placeholders(template.content)
        
        if not placeholders:
            # 没有占位符，直接生成报告
            update_task_progress(task_id, "generating", 90, "生成最终报告")
            
            word_generator = WordGeneratorService()
            report_path = word_generator.generate_report(
                content=template.content,
                title=task.name,
                format="docx"
            )
            
            # 保存报告记录
            report_data = {
                "task_id": task_id,
                "content": template.content,
                "file_path": report_path,
                "status": "completed",
                "generated_at": now(),
                "execution_time": time.time() - start_time
            }
            
            report_record = crud.report_history.create(
                db=db,
                obj_in=schemas.ReportHistoryCreate(**report_data)
            )
            
            update_task_progress(task_id, "completed", 100, "报告生成完成")
            
            return {
                "status": "completed",
                "report_path": report_path,
                "report_id": report_record.id,
                "execution_time": time.time() - start_time,
                "message": "报告生成成功（无占位符）"
            }
        
        # 有占位符，使用增强版Agent系统处理
        update_task_progress(task_id, "analyzing", 20, f"开始分析 {len(placeholders)} 个占位符")
        
        # 使用增强版Agent编排器
        orchestrator = AgentOrchestrator()
        
        # 准备增强的Agent输入
        agent_input = {
            "template_content": template.content,
            "placeholders": placeholders,
            "data_source_id": str(data_source.id),
            "task_id": task_id,
            "user_id": user_id,
            "ai_config": ai_config,  # 用户特定的AI配置
            "enhanced_mode": True
        }
        
        # 执行增强版Agent处理
        try:
            update_task_progress(task_id, "analyzing", 30, "执行Agent智能分析")
            
            # 运行异步Agent处理
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            agent_result = loop.run_until_complete(
                orchestrator.execute(agent_input)
            )
            
            loop.close()
            
            if agent_result.success:
                update_task_progress(task_id, "processing", 70, "处理Agent分析结果")
                
                # 从Agent结果中提取处理后的内容
                processed_content = agent_result.data.get("processed_content", template.content)
                
                # 生成Word文档
                update_task_progress(task_id, "generating", 90, "生成Word文档")
                word_generator = WordGeneratorService()
                report_path = word_generator.generate_report(
                    content=processed_content,
                    title=task.name,
                    format="docx"
                )
                
                # 保存报告记录
                execution_time = time.time() - start_time
                report_data = {
                    "task_id": task_id,
                    "content": processed_content,
                    "file_path": report_path,
                    "status": "completed",
                    "generated_at": now(),
                    "execution_time": execution_time,
                    "ai_config_used": ai_config
                }
                
                report_record = crud.report_history.create(
                    db=db,
                    obj_in=schemas.ReportHistoryCreate(**report_data)
                )
                
                update_task_progress(task_id, "completed", 100, "增强版报告生成完成")
                
                # 发送成功通知
                try:
                    notification_service = NotificationService()
                    notification_service.send_task_completion_notification(
                        task_id=task_id,
                        report_path=report_path,
                        user_id=user_id
                    )
                except Exception as notify_error:
                    logger.warning(f"发送成功通知失败: {notify_error}")
                
                return {
                    "status": "completed",
                    "report_path": report_path,
                    "report_id": report_record.id,
                    "execution_time": execution_time,
                    "ai_config_used": ai_config,
                    "message": "增强版智能报告生成成功"
                }
            else:
                raise Exception(f"增强版Agent处理失败: {agent_result.error}")
                
        except Exception as e:
            logger.error(f"增强版Agent处理异常: {e}")
            raise
            
    except Exception as e:
        logger.error(f"增强版智能报告生成失败 - 任务ID: {task_id}: {e}")
        
        # 更新任务状态为失败
        update_task_progress(task_id, "failed", 0, f"增强版生成失败: {str(e)}")
        
        # 发送错误通知
        send_error_notification(task_id, str(e))
        
        # 发送失败通知
        try:
            notification_service = NotificationService()
            notification_service.send_task_failure_notification(
                task_id=task_id,
                user_id=user_id,
                error_message=str(e)
            )
        except Exception as notify_error:
            logger.warning(f"发送失败通知失败: {notify_error}")
        
        raise
        
    finally:
        db.close()
