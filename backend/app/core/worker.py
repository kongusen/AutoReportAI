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

# Celery应用实例配置
celery_app = Celery(
    "autoreport_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.core.worker"]
)

# Celery配置优化
celery_app.conf.update(
    task_track_started=True,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    result_expires=3600,
    timezone='UTC',
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_max_tasks_per_child=1000,
    broker_connection_retry_on_startup=True,
)


class TaskStatus:
    """任务状态常量"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    QUERYING = "querying"
    PROCESSING = "processing"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class TaskProgressManager:
    """任务进度管理器"""
    
    def __init__(self):
        self.redis_client = redis.from_url(
            settings.REDIS_URL, 
            encoding="utf-8", 
            decode_responses=True
        )
    
    async def update_task_progress(
        self,
        task_id: int,
        status: str,
        progress: int,
        current_step: Optional[str] = None,
        step_details: Optional[Dict[str, Any]] = None
    ):
        """更新任务进度"""
        status_data = {
            "status": status,
            "progress": progress,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if current_step:
            status_data["current_step"] = current_step
        
        if step_details:
            status_data.update(step_details)
        
        # 更新Redis
        await self.redis_client.hset(
            f"report_task:{task_id}:status", 
            mapping=status_data
        )
        
        # 发送WebSocket通知
        notification_service = NotificationService()
        await notification_service.send_task_progress_update(task_id, status_data)


progress_manager = TaskProgressManager()


@celery_app.task(bind=True, autoretry_for=(Exception,), 
                retry_kwargs={'max_retries': 3, 'countdown': 60})
def report_generation_pipeline(self, task_id: int) -> Dict[str, Any]:
    """
    主报告生成任务 - 协调整个报告生成流程
    实现完整的任务分解和并行处理
    """
    logger.info(f"开始报告生成流程，任务ID: {task_id}")
    
    db = SessionLocal()
    try:
        # 1. 获取任务配置
        task = crud.task.get(db=db, id=task_id)
        if not task:
            raise ValueError(f"任务 ID {task_id} 不存在")
        
        # 更新任务状态
        asyncio.create_task(progress_manager.update_task_progress(
            task_id, TaskStatus.ANALYZING, 10, "解析模板"
        ))
        
        # 2. 解析模板获取占位符列表
        template_result = template_parsing.delay(
            template_id=task.template_id,
            task_id=task_id
        )
        placeholders = template_result.get(timeout=300)
        
        if not placeholders:
            raise ValueError("模板解析失败或未找到占位符")
        
        # 更新进度
        asyncio.create_task(progress_manager.update_task_progress(
            task_id, TaskStatus.ANALYZING, 25, "分析占位符需求"
        ))
        
        # 3. 创建占位符分析任务组
        analysis_tasks = []
        for placeholder in placeholders:
            analysis_tasks.append(
                placeholder_analysis.s(
                    placeholder_data=placeholder,
                    data_source_id=task.data_source_id,
                    task_id=task_id
                )
            )
        
        # 并行执行占位符分析
        analysis_job = group(analysis_tasks)
        analysis_results = analysis_job.apply_async()
        analysis_data = analysis_results.get(timeout=600)
        
        # 更新进度
        asyncio.create_task(progress_manager.update_task_progress(
            task_id, TaskStatus.QUERYING, 50, "执行数据查询"
        ))
        
        # 4. 创建数据查询任务组
        query_tasks = []
        for analysis in analysis_data:
            if analysis and analysis.get('etl_instruction'):
                query_tasks.append(
                    data_query.s(
                        etl_instruction=analysis['etl_instruction'],
                        data_source_id=task.data_source_id,
                        task_id=task_id
                    )
                )
        
        # 并行执行数据查询
        if query_tasks:
            query_job = group(query_tasks)
            query_results = query_job.apply_async()
            query_data = query_results.get(timeout=900)
        else:
            query_data = []
        
        # 更新进度
        asyncio.create_task(progress_manager.update_task_progress(
            task_id, TaskStatus.PROCESSING, 75, "填充报告内容"
        ))
        
        # 5. 内容填充任务
        filling_result = content_filling.delay(
            template_content=task.template.content,
            placeholders=placeholders,
            query_results=query_data,
            task_id=task_id
        )
        filled_content = filling_result.get(timeout=300)
        
        # 更新进度
        asyncio.create_task(progress_manager.update_task_progress(
            task_id, TaskStatus.GENERATING, 90, "生成报告文件"
        ))
        
        # 6. 报告生成任务
        generation_result = report_generation.delay(
            template_content=filled_content,
            output_config={
                "format": "docx",
                "title": task.name,
                "task_id": task_id
            },
            task_id=task_id
        )
        final_report = generation_result.get(timeout=300)
        
        # 更新完成状态
        asyncio.create_task(progress_manager.update_task_progress(
            task_id, TaskStatus.COMPLETED, 100, "报告生成完成"
        ))
        
        logger.info(f"报告生成流程完成，任务ID: {task_id}")
        
        return {
            "task_id": task_id,
            "status": "completed",
            "report_path": final_report.get("report_path"),
            "placeholders_count": len(placeholders),
            "queries_executed": len(query_data),
            "completion_time": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"报告生成流程失败，任务ID: {task_id}, 错误: {str(e)}")
        
        # 更新失败状态
        asyncio.create_task(progress_manager.update_task_progress(
            task_id, TaskStatus.FAILED, 0, f"生成失败: {str(e)}"
        ))
        
        # 重试逻辑
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (self.request.retries + 1))
        
        raise
    finally:
        db.close()


@celery_app.task
def template_parsing(template_id: str, task_id: int) -> List[Dict[str, Any]]:
    """模板解析任务 - 提取所有占位符"""
    logger.info(f"开始解析模板，模板ID: {template_id}, 任务ID: {task_id}")
    
    db = SessionLocal()
    try:
        template = crud.template.get(db=db, id=template_id)
        if not template:
            raise ValueError(f"模板 {template_id} 不存在")
        
        processor = PlaceholderProcessor()
        placeholders = processor.extract_placeholders(template.content)
        
        logger.info(f"模板解析完成，找到 {len(placeholders)} 个占位符")
        return placeholders
        
    except Exception as e:
        logger.error(f"模板解析失败: {str(e)}")
        raise
    finally:
        db.close()


@celery_app.task(bind=True, autoretry_for=(Exception,), 
                retry_kwargs={'max_retries': 3, 'countdown': 30})
def placeholder_analysis(self, placeholder_data: Dict[str, Any], 
                        data_source_id: str, task_id: int) -> Dict[str, Any]:
    """占位符分析任务 - 使用Agent系统进行智能分析"""
    placeholder_name = placeholder_data.get('name', 'unknown')
    logger.info(f"开始分析占位符: {placeholder_name}, 任务ID: {task_id}")
    
    try:
        # 使用Agent编排器进行智能分析
        orchestrator = AgentOrchestrator()
        
        # 准备占位符数据，添加必要字段
        agent_input = {
            "placeholder_type": placeholder_data.get('type', '统计'),
            "description": placeholder_data.get('description', placeholder_name),
            "data_source_id": data_source_id,
            "name": placeholder_name,
            **placeholder_data
        }
        
        # 添加上下文信息
        context = {
            "task_id": task_id,
            "processing_mode": "placeholder_analysis"
        }
        
        # 执行异步分析（在同步函数中运行异步代码）
        import asyncio
        try:
            # 尝试获取已存在的事件循环
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # 如果没有事件循环，创建一个新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # 运行Agent分析
        if loop.is_running():
            # 如果循环已在运行，使用run_coroutine_threadsafe
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, orchestrator.execute(agent_input, context))
                agent_result = future.result(timeout=120)
        else:
            # 如果循环未运行，直接使用run
            agent_result = loop.run_until_complete(orchestrator.execute(agent_input, context))
        
        if agent_result.success:
            logger.info(f"Agent占位符分析完成: {placeholder_name}")
            
            # 从Agent结果中提取ETL指令
            workflow_result = agent_result.data
            if workflow_result and hasattr(workflow_result, 'results'):
                # 查找数据查询结果
                data_query_result = workflow_result.results.get('fetch_data')
                if data_query_result and data_query_result.success:
                    return {
                        "placeholder": placeholder_data,
                        "etl_instruction": data_query_result.data.get('etl_instruction'),
                        "data_source_id": data_source_id,
                        "analysis_time": datetime.now().isoformat(),
                        "agent_workflow": True
                    }
            
            # 如果没有找到具体的ETL指令，返回Agent结果
            return {
                "placeholder": placeholder_data,
                "etl_instruction": {
                    "query_type": "agent_processed",
                    "agent_result": agent_result.data,
                    "description": f"通过Agent系统处理占位符: {placeholder_name}"
                },
                "data_source_id": data_source_id,
                "analysis_time": datetime.now().isoformat(),
                "agent_workflow": True
            }
        else:
            # Agent分析失败，回退到传统方法
            logger.warning(f"Agent分析失败，回退到传统AI服务: {placeholder_name}")
            return _fallback_ai_analysis(placeholder_data, data_source_id)
            
    except Exception as e:
        logger.error(f"Agent占位符分析异常: {placeholder_name}, 错误: {str(e)}")
        
        # 回退到传统AI服务
        logger.info(f"回退到传统AI分析方法: {placeholder_name}")
        try:
            return _fallback_ai_analysis(placeholder_data, data_source_id)
        except Exception as fallback_error:
            logger.error(f"传统AI分析也失败: {fallback_error}")
            
            if self.request.retries < self.max_retries:
                logger.warning(f"重试占位符分析: {placeholder_name}, 第{self.request.retries + 1}次重试")
                raise self.retry(countdown=30 * (self.request.retries + 1))
            
            # 返回默认结果而不是失败
            return {
                "placeholder": placeholder_data,
                "etl_instruction": None,
                "error": str(e),
                "fallback_error": str(fallback_error)
            }


def _fallback_ai_analysis(placeholder_data: Dict[str, Any], data_source_id: str) -> Dict[str, Any]:
    """回退的AI分析方法"""
    db = SessionLocal()
    try:
        ai_service = EnhancedAIService(db)
        return asyncio.run(ai_service.analyze_placeholder_requirements(placeholder_data, data_source_id))
    finally:
        db.close()


@celery_app.task(bind=True, autoretry_for=(Exception,), 
                retry_kwargs={'max_retries': 2, 'countdown': 60})
def data_query(self, etl_instruction: Dict[str, Any], 
               data_source_id: str, task_id: int) -> Dict[str, Any]:
    """数据查询任务 - 执行单个ETL指令"""
    logger.info(f"开始执行数据查询，任务ID: {task_id}")
    
    db = SessionLocal()
    try:
        etl_executor = IntelligentETLExecutor(db)
        
        # 执行ETL指令
        query_result = etl_executor.execute_instruction(
            etl_instruction, data_source_id
        )
        
        logger.info(f"数据查询完成，任务ID: {task_id}")
        return query_result
        
    except Exception as e:
        logger.error(f"数据查询失败，任务ID: {task_id}, 错误: {str(e)}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (self.request.retries + 1))
        
        raise
    finally:
        db.close()


@celery_app.task
def content_filling(template_content: str, placeholders: List[Dict[str, Any]], 
                   query_results: List[Dict[str, Any]], task_id: int) -> str:
    """内容填充任务 - 将查询结果填入模板"""
    logger.info(f"开始填充内容，任务ID: {task_id}")
    
    try:
        # 创建占位符到结果的映射
        result_mapping = {}
        for i, result in enumerate(query_results):
            if i < len(placeholders):
                placeholder_name = placeholders[i].get('name')
                if placeholder_name and result:
                    result_mapping[placeholder_name] = result
        
        # 替换模板中的占位符
        filled_content = template_content
        for placeholder_name, result_data in result_mapping.items():
            placeholder_pattern = f"{{{{{placeholder_name}}}}}"
            
            # 根据结果类型进行不同的处理
            if isinstance(result_data.get('data'), list):
                # 如果是列表数据，取第一个值或格式化显示
                data_list = result_data['data']
                replacement = str(data_list[0]) if data_list else "无数据"
            elif isinstance(result_data.get('data'), dict):
                # 如果是字典数据，取第一个值
                data_dict = result_data['data']
                replacement = str(next(iter(data_dict.values()))) if data_dict else "无数据"
            else:
                replacement = str(result_data.get('data', '无数据'))
            
            filled_content = filled_content.replace(placeholder_pattern, replacement)
        
        logger.info(f"内容填充完成，任务ID: {task_id}")
        return filled_content
        
    except Exception as e:
        logger.error(f"内容填充失败，任务ID: {task_id}, 错误: {str(e)}")
        raise


@celery_app.task
def report_generation(template_content: str, output_config: Dict[str, Any], 
                     task_id: int) -> Dict[str, Any]:
    """报告生成任务 - 最终生成报告文件"""
    logger.info(f"开始生成报告文件，任务ID: {task_id}")
    
    db = SessionLocal()
    try:
        # 生成Word文档
        word_generator = WordGeneratorService()
        report_path = word_generator.generate_report(
            content=template_content,
            title=output_config.get('title', '自动生成报告'),
            format=output_config.get('format', 'docx')
        )
        
        # 保存报告记录到数据库
        report_data = {
            "task_id": task_id,
            "content": template_content,
            "file_path": report_path,
            "status": "completed",
            "generated_at": datetime.utcnow()
        }
        
        report_record = crud.report_history.create(
            db=db, 
            obj_in=schemas.ReportHistoryCreate(**report_data)
        )
        
        logger.info(f"报告生成完成，任务ID: {task_id}, 路径: {report_path}")
        
        return {
            "report_path": report_path,
            "report_id": report_record.id,
            "task_id": task_id,
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"报告生成失败，任务ID: {task_id}, 错误: {str(e)}")
        raise
    finally:
        db.close()


# ETL作业执行任务
@celery_app.task(bind=True, autoretry_for=(Exception,), 
                retry_kwargs={'max_retries': 3, 'countdown': 60})
def execute_etl_job(self, job_id: str, job_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行ETL作业任务
    
    Args:
        job_id: ETL作业ID
        job_config: 作业配置
        
    Returns:
        执行结果
    """
    logger.info(f"开始执行ETL作业: {job_id}")
    
    db = SessionLocal()
    try:
        # 获取作业信息
        etl_job = crud.etl_job.get(db, id=job_id)
        if not etl_job:
            raise ValueError(f"ETL作业不存在: {job_id}")
        
        # 检查作业是否启用
        if not etl_job.enabled:
            logger.warning(f"ETL作业已禁用: {job_id}")
            return {"status": "skipped", "message": "作业已禁用"}
        
        # 创建ETL执行器
        etl_executor = IntelligentETLExecutor(db)
        
        # 准备执行参数
        data_source_id = str(etl_job.data_source_id)
        etl_config = etl_job.config or {}
        
        # 构建ETL指令
        etl_instruction = {
            "query_type": etl_config.get("query_type", "sql"),
            "table": etl_config.get("table_name", ""),
            "fields": etl_config.get("fields", []),
            "filters": etl_config.get("filters", []),
            "group_by": etl_config.get("group_by", []),
            "order_by": etl_config.get("order_by", []),
            "limit": etl_config.get("limit"),
            "sql_query": etl_config.get("sql_query", "")
        }
        
        # 执行ETL作业
        start_time = datetime.utcnow()
        result = etl_executor.execute_instruction(etl_instruction, data_source_id)
        end_time = datetime.utcnow()
        
        # 更新作业执行状态
        crud.etl_job.update(
            db, 
            db_obj=etl_job,
            obj_in={
                "last_run_at": start_time,
                "status": "completed",
                "execution_time": (end_time - start_time).total_seconds()
            }
        )
        
        # 发送通知（如果配置了）
        if etl_config.get("notify_on_completion", False):
            notification_service = NotificationService()
            notification_service.send_etl_completion_notification(
                job_id=job_id,
                job_name=etl_job.name,
                status="success",
                execution_time=(end_time - start_time).total_seconds(),
                result_summary=f"处理了{len(result) if isinstance(result, list) else 1}条记录"
            )
        
        logger.info(f"ETL作业执行完成: {job_id}")
        
        return {
            "status": "completed",
            "job_id": job_id,
            "job_name": etl_job.name,
            "execution_time": (end_time - start_time).total_seconds(),
            "records_processed": len(result) if isinstance(result, list) else 1,
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"ETL作业执行失败: {job_id}, 错误: {str(e)}")
        
        # 更新作业执行状态为失败
        try:
            etl_job = crud.etl_job.get(db, id=job_id)
            if etl_job:
                crud.etl_job.update(
                    db,
                    db_obj=etl_job,
                    obj_in={
                        "last_run_at": datetime.utcnow(),
                        "status": "failed",
                        "error_message": str(e)
                    }
                )
        except Exception as update_error:
            logger.error(f"更新ETL作业状态失败: {update_error}")
        
        # 发送失败通知
        try:
            etl_job = crud.etl_job.get(db, id=job_id)
            if etl_job and etl_job.config and etl_job.config.get("notify_on_failure", True):
                notification_service = NotificationService()
                notification_service.send_etl_failure_notification(
                    job_id=job_id,
                    job_name=etl_job.name if etl_job else job_id,
                    error_message=str(e)
                )
        except Exception as notify_error:
            logger.error(f"发送ETL失败通知失败: {notify_error}")
        
        # 如果还有重试次数，则重试
        if self.request.retries < self.max_retries:
            logger.warning(f"重试ETL作业: {job_id}, 第{self.request.retries + 1}次重试")
            raise self.retry(countdown=60 * (self.request.retries + 1))
        
        # 重试次数用尽，返回失败结果
        return {
            "status": "failed",
            "job_id": job_id,
            "error": str(e),
            "retries": self.request.retries
        }
        
    finally:
        db.close()


# 保留测试任务
@celery_app.task
def test_celery_task(word: str) -> str:
    """测试任务"""
    return f"测试任务成功执行，收到的参数是: {word}"


# 添加辅助函数
def update_task_progress(task_id: int, status: str, progress: int, message: str):
    """同步更新任务进度的辅助函数"""
    try:
        import redis
        redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        
        status_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        redis_client.hset(f"report_task:{task_id}:status", mapping=status_data)
        redis_client.close()
    except Exception as e:
        logger.error(f"更新任务进度失败: {e}")


def update_task_progress_dict(task_id: int, status_data: dict):
    """同步更新任务进度的辅助函数（字典版本）"""
    try:
        import redis
        redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        redis_client.hset(f"report_task:{task_id}:status", mapping=status_data)
        redis_client.close()
    except Exception as e:
        logger.error(f"更新任务进度失败: {e}")


@celery_app.task(bind=True, name='app.core.worker.intelligent_report_generation_pipeline')
def intelligent_report_generation_pipeline(self, task_id: int, user_id: str):
    """
    智能占位符驱动的报告生成流水线
    """
    from app.core.database import SessionLocal
    from app.models.task import Task
    from app.models.template import Template
    from app.models.data_source import DataSource
    from app import crud
    from datetime import datetime
    import asyncio
    import uuid
    
    logger.info(f"开始智能占位符报告生成流水线 - 任务ID: {task_id}")
    
    db = SessionLocal()
    
    try:
        # 获取任务信息
        task = crud.task.get(db, id=task_id)
        if not task:
            raise Exception(f"任务 {task_id} 不存在")
        
        # 获取模板和数据源
        template = db.query(Template).filter(Template.id == task.template_id).first()
        data_source = db.query(DataSource).filter(DataSource.id == task.data_source_id).first()
        
        if not template:
            raise Exception(f"模板 {task.template_id} 不存在")
        if not data_source:
            raise Exception(f"数据源 {task.data_source_id} 不存在")
        
        logger.info(f"任务信息 - 模板: {template.name}, 数据源: {data_source.name}")
        
        # 更新任务状态
        update_task_progress(task_id, "processing", 10, "开始智能占位符分析...")
        
        # 第一步：分析模板中的占位符
        from app.api.endpoints.intelligent_placeholders import extract_placeholders_from_content
        placeholders = extract_placeholders_from_content(template.content)
        
        logger.info(f"发现 {len(placeholders)} 个占位符")
        update_task_progress(task_id, "processing", 25, f"发现 {len(placeholders)} 个占位符，开始Agent处理...")
        
        # 第二步：使用Agent系统处理占位符
        from app.services.agents.orchestrator import orchestrator
        
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
            "processing_config": {},
            "output_config": {}
        }
        
        # 异步处理占位符
        async def process_placeholders():
            placeholder_results = []
            successful_count = 0
            
            for i, placeholder in enumerate(placeholders):
                try:
                    progress = 25 + (i / len(placeholders)) * 60  # 25% to 85%
                    update_task_progress(
                        task_id, "processing", int(progress), 
                        f"处理占位符 {i+1}/{len(placeholders)}: {placeholder.get('placeholder_name', '')}"
                    )
                    
                    # 准备占位符处理数据
                    placeholder_input = {
                        "placeholder_type": placeholder.get("placeholder_type", "text"),
                        "description": placeholder.get("description", placeholder.get("placeholder_name", "")),
                        "data_source_id": str(data_source.id),
                    }
                    
                    # 通过orchestrator处理单个占位符
                    agent_result = await orchestrator._process_single_placeholder(placeholder_input, task_context)
                    
                    if agent_result.success and agent_result.data:
                        # 从工作流结果中提取最终内容
                        from app.api.endpoints.intelligent_placeholders import extract_content_from_agent_result
                        final_content = extract_content_from_agent_result(agent_result)
                        
                        placeholder_results.append({
                            "placeholder_name": placeholder.get("placeholder_name", ""),
                            "content": final_content,
                            "success": True,
                            "agent_result": str(agent_result.data)[:200]  # 限制长度
                        })
                        successful_count += 1
                        logger.info(f"占位符 '{placeholder.get('placeholder_name', '')}' 处理成功: {final_content}")
                    else:
                        error_msg = agent_result.error_message if hasattr(agent_result, 'error_message') else "未知错误"
                        placeholder_results.append({
                            "placeholder_name": placeholder.get("placeholder_name", ""),
                            "content": "数据获取失败",
                            "success": False,
                            "error": error_msg
                        })
                        logger.warning(f"占位符 '{placeholder.get('placeholder_name', '')}' 处理失败: {error_msg}")
                
                except Exception as e:
                    error_msg = str(e)
                    placeholder_results.append({
                        "placeholder_name": placeholder.get("placeholder_name", ""),
                        "content": "处理失败",
                        "success": False,
                        "error": error_msg
                    })
                    logger.error(f"占位符 '{placeholder.get('placeholder_name', '')}' 处理异常: {error_msg}")
            
            return placeholder_results, successful_count
        
        # 运行异步处理
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            placeholder_results, successful_count = loop.run_until_complete(process_placeholders())
        finally:
            loop.close()
        
        # 第三步：生成报告内容
        update_task_progress(task_id, "processing", 85, f"生成报告内容... ({successful_count}/{len(placeholders)} 个占位符处理成功)")
        
        # 替换模板中的占位符
        report_content = template.content
        for result in placeholder_results:
            if result.get("success"):
                placeholder_name = result.get("placeholder_name", "")
                content = result.get("content", "")
                # 替换占位符
                report_content = report_content.replace(f"{{{{{placeholder_name}}}}}", str(content))
        
        # 第四步：保存报告结果
        update_task_progress(task_id, "processing", 95, "保存报告结果...")
        
        # 生成报告文件路径
        from datetime import datetime
        import os
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"intelligent_report_{task_id}_{timestamp}.txt"
        reports_dir = os.path.join(os.getcwd(), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        report_path = os.path.join(reports_dir, report_filename)
        
        # 保存报告内容
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# 智能占位符生成报告\n")
            f.write(f"## 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"## 模板: {template.name}\n")
            f.write(f"## 数据源: {data_source.name}\n")
            f.write(f"## 占位符处理结果: {successful_count}/{len(placeholders)} 成功\n\n")
            f.write("## 报告内容\n\n")
            f.write(report_content)
            f.write(f"\n\n## 占位符处理详情\n")
            for result in placeholder_results:
                status = "✅" if result.get("success") else "❌"
                f.write(f"- {status} {result.get('placeholder_name', '')}: {result.get('content', '')}\n")
                if not result.get("success") and result.get("error"):
                    f.write(f"  错误: {result.get('error')}\n")
        
        # 完成任务
        final_status = {
            "status": "completed",
            "progress": 100,
            "message": f"智能占位符报告生成完成 ({successful_count}/{len(placeholders)} 个占位符处理成功)",
            "report_path": report_path,
            "report_filename": report_filename,
            "placeholder_results": placeholder_results,
            "successful_count": successful_count,
            "total_placeholders": len(placeholders),
            "completion_time": datetime.now().isoformat()
        }
        
        update_task_progress_dict(task_id, final_status)
        
        logger.info(f"智能占位符报告生成完成 - 任务ID: {task_id}, 成功率: {successful_count}/{len(placeholders)}")
        
        return {
            "success": True,
            "task_id": task_id,
            "report_path": report_path,
            "successful_placeholders": successful_count,
            "total_placeholders": len(placeholders)
        }
        
    except Exception as e:
        error_msg = f"智能占位符报告生成失败: {str(e)}"
        logger.error(error_msg)
        
        update_task_progress(task_id, "failed", 0, error_msg)
        
        return {
            "success": False,
            "task_id": task_id,
            "error": error_msg
        }
        
    finally:
        db.close()
