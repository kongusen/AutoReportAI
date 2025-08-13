"""
改进的Worker - 增强错误处理和状态更新机制
"""
import json
import logging
import time
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from celery import Celery, chord, group
from celery.exceptions import MaxRetriesExceededError, Retry
from kombu import Queue
from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.ai_integration.ai_service_enhanced import EnhancedAIService
from app.services.agents.orchestrator import AgentOrchestrator
from app.services.data_processing.etl.intelligent_etl_executor import IntelligentETLExecutor
from app.services.intelligent_placeholder.processor import PlaceholderProcessor
from app.services.notification.notification_service import NotificationService
from app.services.report_generation.generator import ReportGenerationService
from app.services.word_generator_service import WordGeneratorService

logger = logging.getLogger(__name__)


class EnhancedTaskProgressManager:
    """增强的任务进度管理器 - 改进错误处理"""
    
    def __init__(self):
        self.redis_client = redis.from_url(
            settings.REDIS_URL, 
            encoding="utf-8", 
            decode_responses=True
        )
    
    async def update_task_progress_safe(
        self,
        task_id: int,
        status: str,
        progress: int,
        current_step: Optional[str] = None,
        step_details: Optional[Dict[str, Any]] = None,
        error_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """安全的任务进度更新，包含错误处理和重试机制"""
        max_retries = 3
        
        status_data = {
            "status": status,
            "progress": progress,
            "updated_at": datetime.utcnow().isoformat(),
            "task_id": task_id
        }
        
        if current_step:
            status_data["current_step"] = current_step
        
        if step_details:
            status_data.update(step_details)
            
        if error_info:
            status_data.update(error_info)
            status_data["has_error"] = True
        
        for attempt in range(max_retries):
            try:
                # 更新Redis
                await self.redis_client.hset(
                    f"report_task:{task_id}:status", 
                    mapping=status_data
                )
                
                # 发送WebSocket通知
                try:
                    notification_service = NotificationService()
                    await notification_service.send_task_progress_update(task_id, status_data)
                except Exception as notify_error:
                    logger.warning(f"WebSocket通知发送失败: {notify_error}")
                
                logger.debug(f"任务进度更新成功 - 任务ID: {task_id}, 状态: {status}, 进度: {progress}%")
                return True
                
            except Exception as e:
                logger.warning(f"更新任务进度失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"任务进度更新彻底失败 - 任务ID: {task_id}: {e}")
                    return False
                await asyncio.sleep(1 * (attempt + 1))  # 递增等待时间
        
        return False


def sync_update_task_progress(task_id: int, status: str, progress: int, message: str, 
                            error_info: Optional[Dict[str, Any]] = None) -> bool:
    """同步版本的安全进度更新"""
    try:
        import redis
        redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        
        status_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "updated_at": datetime.utcnow().isoformat(),
            "task_id": task_id
        }
        
        if error_info:
            status_data.update(error_info)
            status_data["has_error"] = True
        
        redis_client.hset(f"report_task:{task_id}:status", mapping=status_data)
        redis_client.close()
        logger.debug(f"任务进度同步更新成功 - 任务ID: {task_id}, 状态: {status}")
        return True
        
    except Exception as e:
        logger.error(f"同步更新任务进度失败 - 任务ID: {task_id}: {e}")
        return False


def send_error_notification(task_id: int, error_message: str, user_id: Optional[str] = None):
    """发送错误通知"""
    try:
        from app.services.notification.notification_service import NotificationService
        notification_service = NotificationService()
        # 这里可以添加更多的通知机制，如邮件、短信等
        logger.info(f"错误通知已记录 - 任务ID: {task_id}: {error_message}")
        
        # 如果有用户ID，可以发送个人通知
        if user_id:
            # 这里可以添加用户特定的通知逻辑
            pass
            
    except Exception as e:
        logger.error(f"发送错误通知失败: {e}")


def enhanced_intelligent_report_generation_pipeline(task_id: int, user_id: str) -> Dict[str, Any]:
    """
    增强的智能占位符驱动报告生成流水线
    改进了错误处理、状态更新和文件保存机制
    """
    logger.info(f"开始增强版智能占位符报告生成流水线 - 任务ID: {task_id}")
    
    db = SessionLocal()
    
    try:
        # 1. 获取和验证任务信息
        sync_update_task_progress(task_id, "processing", 5, "验证任务配置...")
        
        task = crud.task.get(db, id=task_id)
        if not task:
            raise Exception(f"任务 {task_id} 不存在")
        
        # 获取模板和数据源
        from app.models.template import Template
        from app.models.data_source import DataSource
        
        template = db.query(Template).filter(Template.id == task.template_id).first()
        data_source = db.query(DataSource).filter(DataSource.id == task.data_source_id).first()
        
        if not template:
            raise Exception(f"模板 {task.template_id} 不存在")
        if not data_source:
            raise Exception(f"数据源 {task.data_source_id} 不存在")
        
        logger.info(f"任务配置验证成功 - 模板: {template.name}, 数据源: {data_source.name}")
        
        # 2. 分析模板中的占位符
        sync_update_task_progress(task_id, "processing", 15, "分析模板占位符...")
        
        try:
            from app.api.endpoints.intelligent_placeholders import extract_placeholders_from_content
            placeholders = extract_placeholders_from_content(template.content)
            
            if not placeholders:
                logger.warning(f"模板 {template.name} 中未发现占位符")
                placeholders = []
                
            logger.info(f"发现 {len(placeholders)} 个占位符")
            
        except Exception as placeholder_error:
            logger.error(f"占位符分析失败: {placeholder_error}")
            sync_update_task_progress(task_id, "failed", 0, f"占位符分析失败: {str(placeholder_error)}")
            raise
        
        # 3. 使用Agent系统处理占位符
        sync_update_task_progress(task_id, "processing", 30, f"开始处理 {len(placeholders)} 个占位符...")
        
        placeholder_results = []
        successful_count = 0
        
        # 创建任务上下文
        task_context = {
            "template_id": str(template.id),
            "template_name": template.name,
            "template_content": template.content,
            "data_source_id": str(data_source.id),
            "data_source_name": data_source.name,
            "data_source": data_source,
            "user_id": user_id,
            "task_id": str(task_id),
        }
        
        # 处理每个占位符
        for i, placeholder in enumerate(placeholders):
            try:
                current_progress = 30 + (i / len(placeholders)) * 50  # 30% to 80%
                placeholder_name = placeholder.get('placeholder_name', f'placeholder_{i}')
                
                sync_update_task_progress(
                    task_id, "processing", int(current_progress), 
                    f"处理占位符 {i+1}/{len(placeholders)}: {placeholder_name}"
                )
                
                # 使用Agent处理占位符
                from app.services.agents.orchestrator import AgentOrchestrator
                orchestrator = AgentOrchestrator()
                
                placeholder_input = {
                    "placeholder_type": placeholder.get("placeholder_type", "text"),
                    "description": placeholder.get("description", placeholder_name),
                    "data_source_id": str(data_source.id),
                }
                
                # 异步处理
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    agent_result = loop.run_until_complete(
                        orchestrator._process_single_placeholder(placeholder_input, task_context)
                    )
                finally:
                    loop.close()
                
                if agent_result.success and agent_result.data:
                    from app.api.endpoints.intelligent_placeholders import extract_content_from_agent_result
                    final_content = extract_content_from_agent_result(agent_result)
                    
                    placeholder_results.append({
                        "placeholder_name": placeholder_name,
                        "content": final_content,
                        "success": True,
                        "agent_result": str(agent_result.data)[:200]
                    })
                    successful_count += 1
                    logger.info(f"占位符 '{placeholder_name}' 处理成功")
                else:
                    error_msg = getattr(agent_result, 'error_message', "Agent处理失败")
                    placeholder_results.append({
                        "placeholder_name": placeholder_name,
                        "content": "数据获取失败",
                        "success": False,
                        "error": error_msg
                    })
                    logger.warning(f"占位符 '{placeholder_name}' 处理失败: {error_msg}")
                
            except Exception as placeholder_process_error:
                error_msg = str(placeholder_process_error)
                placeholder_results.append({
                    "placeholder_name": placeholder.get('placeholder_name', f'placeholder_{i}'),
                    "content": "处理异常",
                    "success": False,
                    "error": error_msg
                })
                logger.error(f"占位符处理异常: {error_msg}")
        
        # 4. 生成报告内容
        sync_update_task_progress(task_id, "processing", 85, "生成报告内容...")
        
        report_content = template.content
        for result in placeholder_results:
            if result.get("success"):
                placeholder_name = result.get("placeholder_name", "")
                content = result.get("content", "")
                report_content = report_content.replace(f"{{{{{placeholder_name}}}}}", str(content))
        
        # 5. 安全的文件保存
        sync_update_task_progress(task_id, "processing", 95, "保存报告文件...")
        
        report_path = safe_save_report_file(task_id, template, data_source, report_content, 
                                          placeholder_results, successful_count, len(placeholders))
        
        # 6. 完成任务
        final_status = {
            "status": "completed",
            "progress": 100,
            "message": f"智能占位符报告生成完成 ({successful_count}/{len(placeholders)} 个占位符处理成功)",
            "report_path": report_path,
            "placeholder_results": placeholder_results,
            "successful_count": successful_count,
            "total_placeholders": len(placeholders),
            "completion_time": datetime.now().isoformat(),
            "has_errors": successful_count < len(placeholders)
        }
        
        success = sync_update_task_progress(
            task_id, "completed", 100, 
            f"报告生成完成 ({successful_count}/{len(placeholders)})"
        )
        
        if not success:
            logger.error(f"最终状态更新失败，但报告已生成: {report_path}")
        
        logger.info(f"智能占位符报告生成完成 - 任务ID: {task_id}, 成功率: {successful_count}/{len(placeholders)}")
        
        return {
            "success": True,
            "task_id": task_id,
            "report_path": report_path,
            "successful_placeholders": successful_count,
            "total_placeholders": len(placeholders)
        }
        
    except Exception as e:
        import traceback
        error_msg = f"智能占位符报告生成失败: {str(e)}"
        full_traceback = traceback.format_exc()
        logger.error(f"{error_msg}\n完整错误堆栈:\n{full_traceback}")
        
        # 更新失败状态
        error_info = {
            "error": str(e),
            "traceback": full_traceback[:1000],
            "failed_at": datetime.now().isoformat()
        }
        
        sync_update_task_progress(task_id, "failed", 0, error_msg, error_info)
        send_error_notification(task_id, error_msg, user_id)
        
        return {
            "success": False,
            "task_id": task_id,
            "error": error_msg,
            "traceback": full_traceback
        }
        
    finally:
        db.close()


def safe_save_report_file(task_id: int, template, data_source, report_content: str, 
                         placeholder_results: List[Dict], successful_count: int, total_placeholders: int) -> str:
    """安全的报告文件保存，包含多重备用方案"""
    import os
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"intelligent_report_{task_id}_{timestamp}.txt"
    
    # 尝试多个保存位置
    save_paths = [
        "/app/reports",  # Docker环境
        os.path.join(os.getcwd(), "reports"),  # 本地环境
        "/tmp",  # 系统临时目录
        os.path.expanduser("~/reports")  # 用户目录
    ]
    
    for reports_dir in save_paths:
        try:
            os.makedirs(reports_dir, exist_ok=True)
            report_path = os.path.join(reports_dir, report_filename)
            
            logger.info(f"尝试写入报告文件: {report_path}")
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"# 智能占位符生成报告\n")
                f.write(f"## 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"## 模板: {template.name}\n")
                f.write(f"## 数据源: {data_source.name}\n")
                f.write(f"## 占位符处理结果: {successful_count}/{total_placeholders} 成功\n\n")
                f.write("## 报告内容\n\n")
                f.write(report_content)
                f.write(f"\n\n## 占位符处理详情\n")
                for result in placeholder_results:
                    status = "✅" if result.get("success") else "❌"
                    f.write(f"- {status} {result.get('placeholder_name', '')}: {result.get('content', '')}\n")
                    if not result.get("success") and result.get("error"):
                        f.write(f"  错误: {result.get('error')}\n")
            
            # 验证文件是否成功写入
            if os.path.exists(report_path) and os.path.getsize(report_path) > 0:
                logger.info(f"报告文件写入成功: {report_path} (文件大小: {os.path.getsize(report_path)} bytes)")
                return report_path
            else:
                logger.warning(f"文件写入验证失败: {report_path}")
                
        except Exception as save_error:
            logger.warning(f"保存到 {reports_dir} 失败: {save_error}")
            continue
    
    # 所有保存位置都失败，返回错误信息
    logger.error("所有报告文件保存位置都失败")
    return "文件保存失败 - 所有保存位置都不可用"