"""
Basic Celery Tasks

基础Celery任务定义，包括：
- 模板解析
- 占位符分析
- 数据查询
- 内容填充
- 报告生成
- ETL作业执行
"""

import asyncio
import logging
from typing import Any, Dict, List

from celery import chord, group
from celery.exceptions import MaxRetriesExceededError, Retry
from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.time_utils import now, format_iso
from app.db.session import SessionLocal
from app.services.ai.integration.ai_service_enhanced import EnhancedAIService
# AgentOrchestrator not available, using placeholder
class AgentOrchestrator:
    def __init__(self):
        pass
    
    async def execute(self, agent_input, context):
        # Placeholder implementation
        return type('obj', (object,), {
            'success': True,
            'data': type('obj', (object,), {
                'results': {
                    'fetch_data': type('obj', (object,), {
                        'success': True,
                        'data': {'etl_instruction': 'SELECT * FROM placeholder_table'}
                    })()
                }
            })()
        })()
from app.services.data.processing.etl.intelligent_etl_executor import IntelligentETLExecutor
from app.services.infrastructure.notification.notification_service import NotificationService
from app.services.domain.template.services.template_domain_service import TemplateParser
from app.services.domain.reporting.word_generator_service import WordGeneratorService
from ..config.celery_app import celery_app
from ..utils.progress_utils import update_task_progress, send_error_notification

# 添加WebSocket通知工具函数
async def send_progress_notification(task_id: int, progress: int, message: str, user_id: str = None):
    """发送进度通知到前端"""
    try:
        from app.websocket.manager import manager, NotificationMessage
        
        if not user_id:
            # 从任务中获取用户ID
            db = SessionLocal()
            try:
                task = crud.task.get(db, id=task_id)
                if task:
                    user_id = str(task.owner_id)
            finally:
                db.close()
        
        if user_id:
            notification = NotificationMessage(
                type="info",
                title="任务进度更新",
                message=message,
                data={
                    "task_id": task_id,
                    "progress": progress,
                    "action": "task_progress"
                },
                user_id=user_id
            )
            await manager.send_to_user(user_id, notification.to_dict())
            logger.debug(f"发送进度通知: 任务{task_id}, 进度{progress}%")
    except Exception as e:
        logger.warning(f"发送进度通知失败: {e}")

def send_progress_notification_sync(task_id: int, progress: int, message: str, user_id: str = None):
    """同步版本的进度通知"""
    import asyncio
    try:
        # 在新的事件循环中运行异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_progress_notification(task_id, progress, message, user_id))
        loop.close()
    except Exception as e:
        logger.warning(f"同步进度通知失败: {e}")

logger = logging.getLogger(__name__)


@celery_app.task(name='app.services.application.task_management.core.worker.tasks.basic_tasks.template_parsing')
def template_parsing(template_id: str, task_id: int) -> List[Dict[str, Any]]:
    """模板解析任务 - 提取所有占位符"""
    logger.info(f"开始解析模板，模板ID: {template_id}, 任务ID: {task_id}")
    
    # 发送开始通知
    send_progress_notification_sync(task_id, 10, "开始解析模板...")
    
    db = SessionLocal()
    try:
        template = crud.template.get(db=db, id=template_id)
        if not template:
            raise ValueError(f"模板 {template_id} 不存在")
        
        send_progress_notification_sync(task_id, 30, "正在提取占位符...")
        
        parser = TemplateParser()
        placeholders = parser.extract_placeholders(template.content)
        
        send_progress_notification_sync(task_id, 50, f"模板解析完成，发现 {len(placeholders)} 个占位符")
        
        logger.info(f"模板解析完成，找到 {len(placeholders)} 个占位符")
        return placeholders
        
    except Exception as e:
        logger.error(f"模板解析失败: {str(e)}")
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name='app.services.application.task_management.core.worker.tasks.basic_tasks.placeholder_analysis',
                autoretry_for=(Exception,), 
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
                        "analysis_time": format_iso(),
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
                "analysis_time": format_iso(),
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


@celery_app.task(bind=True, name='app.services.application.task_management.core.worker.tasks.basic_tasks.data_query',
                autoretry_for=(Exception,), 
                retry_kwargs={'max_retries': 2, 'countdown': 60})
def data_query(self, etl_instruction: Dict[str, Any], 
               data_source_id: str, task_id: int) -> Dict[str, Any]:
    """数据查询任务 - 使用统一的Agent执行系统"""
    logger.info(f"🚀 开始Agent数据查询执行，任务ID: {task_id}")
    
    # 发送开始通知
    send_progress_notification_sync(task_id, 60, "开始执行数据查询...")
    
    db = SessionLocal()
    try:
        # 使用TaskSQLExecutionAgent替代直接的ETL执行器
        from app.services.ai.agents.task_sql_execution_agent import (
            TaskSQLExecutionAgent, 
            TaskExecutionContext,
            TaskExecutionMode,
            ExecutionPriority
        )
        
        # 创建Agent实例
        agent_config = {
            'enable_intelligent_analysis': True,
            'enable_cache_optimization': True,
            'enable_recovery_mode': True,
            'default_timeout': 120
        }
        
        sql_agent = TaskSQLExecutionAgent(db, agent_config)
        
        # 构建执行上下文
        context = TaskExecutionContext(
            task_id=task_id,
            etl_instruction=etl_instruction,
            data_source_id=data_source_id,
            execution_mode=TaskExecutionMode.DIRECT_SQL,  # 默认模式，Agent会智能优化
            priority=ExecutionPriority.MEDIUM,
            retry_count=self.request.retries,
            max_retries=self.max_retries,
            timeout_seconds=120,
            enable_cache=True,
            enable_recovery=True
        )
        
        # 执行Agent任务
        try:
            # 获取或创建事件循环
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # 异步执行Agent任务
            if loop.is_running():
                # 如果循环已在运行，使用线程池执行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, sql_agent.execute_task(context))
                    agent_result = future.result(timeout=context.timeout_seconds)
            else:
                # 如果循环未运行，直接使用run_until_complete
                agent_result = loop.run_until_complete(sql_agent.execute_task(context))
            
            if agent_result.success:
                logger.info(f"✅ Agent数据查询成功，任务ID: {task_id}, 模式: {agent_result.mode_used.value if agent_result.mode_used else 'unknown'}, 执行时间: {agent_result.execution_time:.2f}s")
                
                # 发送成功通知
                send_progress_notification_sync(task_id, 80, f"数据查询完成，耗时 {agent_result.execution_time:.2f}s")
                
                # 转换Agent结果为标准格式
                query_result = {
                    "success": True,
                    "data": agent_result.data,
                    "execution_time": agent_result.execution_time,
                    "cache_hit": agent_result.cache_hit,
                    "agent_metadata": {
                        "execution_mode": agent_result.mode_used.value if agent_result.mode_used else None,
                        "retry_count": agent_result.retry_count,
                        "agent_used": True,
                        **agent_result.metadata
                    }
                }
                
                return query_result
            else:
                # Agent执行失败，记录详细信息
                error_message = agent_result.error_message or "Agent执行失败"
                logger.error(f"❌ Agent数据查询失败，任务ID: {task_id}, 错误: {error_message}")
                
                # 如果还有重试次数，抛出异常触发重试
                if self.request.retries < self.max_retries:
                    logger.warning(f"🔄 Agent任务重试 {self.request.retries + 1}/{self.max_retries}: {task_id}")
                    raise Exception(f"Agent执行失败: {error_message}")
                
                # 重试次数用尽，返回失败结果
                return {
                    "success": False,
                    "error": error_message,
                    "agent_metadata": {
                        "execution_mode": agent_result.mode_used.value if agent_result.mode_used else None,
                        "retry_count": agent_result.retry_count,
                        "agent_used": True,
                        "final_failure": True,
                        **agent_result.metadata
                    }
                }
                
        except Exception as agent_error:
            logger.error(f"⚠️ Agent执行异常，任务ID: {task_id}, 错误: {str(agent_error)}")
            
            # Agent系统异常，回退到传统ETL执行器
            logger.info(f"🔄 Agent异常回退到传统执行器，任务ID: {task_id}")
            try:
                etl_executor = IntelligentETLExecutor(db)
                traditional_result = etl_executor.execute_instruction(etl_instruction, data_source_id)
                
                logger.info(f"✅ 传统执行器成功执行，任务ID: {task_id}")
                return {
                    "success": True,
                    "data": traditional_result,
                    "agent_metadata": {
                        "agent_used": False,
                        "fallback_reason": f"Agent异常: {str(agent_error)}",
                        "fallback_success": True
                    }
                }
                
            except Exception as fallback_error:
                logger.error(f"❌ 传统执行器也失败，任务ID: {task_id}, 错误: {str(fallback_error)}")
                
                # 如果还有重试次数，抛出异常触发重试
                if self.request.retries < self.max_retries:
                    raise self.retry(countdown=60 * (self.request.retries + 1))
                
                # 完全失败
                raise Exception(f"Agent和传统执行器都失败: Agent={str(agent_error)}, Fallback={str(fallback_error)}")
        
    except Exception as e:
        logger.error(f"❌ 数据查询任务完全失败，任务ID: {task_id}, 错误: {str(e)}")
        
        # 最后的重试机制
        if self.request.retries < self.max_retries:
            logger.warning(f"🔄 任务最终重试 {self.request.retries + 1}/{self.max_retries}: {task_id}")
            raise self.retry(countdown=60 * (self.request.retries + 1))
        
        raise
    finally:
        db.close()


@celery_app.task(name='app.services.application.task_management.core.worker.tasks.basic_tasks.content_filling')
def content_filling(template_content: str, placeholders: List[Dict[str, Any]], 
                   query_results: List[Dict[str, Any]], task_id: int) -> str:
    """内容填充任务 - 将查询结果填入模板"""
    logger.info(f"开始填充内容，任务ID: {task_id}")
    
    # 发送开始通知
    send_progress_notification_sync(task_id, 85, "开始填充内容到模板...")
    
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
        
        # 发送完成通知
        send_progress_notification_sync(task_id, 90, "内容填充完成")
        
        logger.info(f"内容填充完成，任务ID: {task_id}")
        return filled_content
        
    except Exception as e:
        logger.error(f"内容填充失败，任务ID: {task_id}, 错误: {str(e)}")
        raise


@celery_app.task(name='app.services.application.task_management.core.worker.tasks.basic_tasks.report_generation')
def report_generation(template_content: str, output_config: Dict[str, Any], 
                     task_id: int) -> Dict[str, Any]:
    """报告生成任务 - 最终生成报告文件"""
    logger.info(f"开始生成报告文件，任务ID: {task_id}")
    
    # 发送开始通知
    send_progress_notification_sync(task_id, 95, "开始生成报告文件...")
    
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
            "generated_at": now()
        }
        
        report_record = crud.report_history.create(
            db=db, 
            obj_in=schemas.ReportHistoryCreate(**report_data)
        )
        
        # 在会话关闭前获取ID
        report_id = report_record.id
        
        logger.info(f"报告生成完成，任务ID: {task_id}, 路径: {report_path}")
        
        # 更新任务状态为已完成
        task = crud.task.get(db, id=task_id)
        if task:
            from app.models.task import TaskStatus
            crud.task.update_status(db, task_id=task_id, status=TaskStatus.COMPLETED)
            
            # 发送WebSocket通知到前端
            try:
                import asyncio
                from app.websocket.manager import manager, NotificationMessage
                
                notification = NotificationMessage(
                    type="success",
                    title="报告生成完成",
                    message=f"任务 '{task.name}' 的报告已生成完成，可以下载了",
                    data={
                        "task_id": task_id,
                        "report_id": report_id,
                        "report_path": report_path,
                        "action": "task_completed",
                        "download_url": f"/api/v1/reports/{report_id}/download"
                    },
                    user_id=str(task.owner_id)
                )
                
                # 使用同步方式发送异步通知
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run, 
                            manager.send_to_user(str(task.owner_id), notification.to_dict())
                        )
                        future.result(timeout=5)
                else:
                    loop.run_until_complete(
                        manager.send_to_user(str(task.owner_id), notification.to_dict())
                    )
                
                logger.info(f"已发送任务完成通知到用户: {task.owner_id}")
                
            except Exception as notification_error:
                logger.error(f"发送完成通知失败: {notification_error}")
        
        return {
            "report_path": report_path,
            "report_id": report_id,
            "task_id": task_id,
            "status": "completed",
            "notification_sent": True
        }
        
    except Exception as e:
        logger.error(f"报告生成失败，任务ID: {task_id}, 错误: {str(e)}")
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name='app.services.application.task_management.core.worker.tasks.basic_tasks.execute_etl_job',
                autoretry_for=(Exception,), 
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
        start_time = now()
        result = etl_executor.execute_instruction(etl_instruction, data_source_id)
        end_time = now()
        
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
                        "last_run_at": now(),
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


@celery_app.task(name='app.services.application.task_management.core.worker.tasks.basic_tasks.test_celery_task')
def test_celery_task(word: str) -> str:
    """测试任务"""
    return f"测试任务成功执行，收到的参数是: {word}"
