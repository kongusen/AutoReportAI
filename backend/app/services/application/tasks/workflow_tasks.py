"""
工作流任务 - React Agent系统
基于Celery的异步任务执行器
"""

from celery import current_app as celery_app
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name='tasks.application.workflow.generate_report_workflow')
def generate_report_workflow(
    self,
    task_id: str,
    data_source_ids: List[str],
    execution_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    生成报告工作流任务
    
    Args:
        task_id: 任务ID
        data_source_ids: 数据源ID列表
        execution_context: 执行上下文
    
    Returns:
        Dict[str, Any]: 执行结果
    """
    try:
        # 1) 加载任务与上下文
        from app.db.session import get_db_session
        from app import crud
        from app.services.application.facades.unified_service_facade import create_unified_service_facade

        now = datetime.now().isoformat()
        with get_db_session() as db:
            task_obj = crud.task.get(db, id=int(task_id))
            if not task_obj:
                raise ValueError(f"任务不存在: {task_id}")

            # 用户与资源
            user_id = str(task_obj.owner_id)
            template_id = str(task_obj.template_id)
            ds_id = str(task_obj.data_source_id)
            # 调度周期
            cron_expr = task_obj.schedule or (execution_context.get('cron_expression') if execution_context else None)

            logger.info(f"开始执行报告生成工作流 - 任务: {task_id}, 用户: {user_id}")

            # 更新状态
            self.update_state(state='PROGRESS', meta={'current_step': '初始化工作流', 'progress': 10, 'started_at': now})

            # 2) 执行组装（v2 流水线，按自然日/周/月/年）
            facade = create_unified_service_facade(db, user_id)
            import asyncio
            assembled = asyncio.run(
                facade.generate_report_v2(
                    template_id=template_id,
                    data_source_id=ds_id,
                    schedule={'cron_expression': cron_expr} if cron_expr else None,
                    execution_time=now,
                )
            )

            result = {
                'success': True,
                'task_id': task_id,
                'user_id': user_id,
                'template_id': template_id,
                'data_source_ids': data_source_ids or [ds_id],
                'execution_context': execution_context or {},
                'workflow_type': 'generate_report',
                'completed_at': datetime.now().isoformat(),
                'message': '报告流水线执行完成',
                'assembled': assembled,
            }

            logger.info(f"报告生成工作流完成 - 任务: {task_id}")
            return result
        
    except Exception as e:
        logger.error(f"报告生成工作流失败 - 任务: {task_id}, 错误: {e}")
        
        self.update_state(state='FAILURE', meta={'error': str(e), 'task_id': task_id, 'failed_at': datetime.now().isoformat()})
        
        return {
            'success': False,
            'task_id': task_id,
            'error': str(e),
            'failed_at': datetime.now().isoformat()
        }


@celery_app.task(bind=True, name='generate_report_orchestrated')
def generate_report_orchestrated(
    self,
    task_id: str,
    template_id: str,
    data_source_id: str,
    user_id: str,
    schedule: Optional[Dict[str, Any]] = None,
    skip_stages: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    使用 Orchestrator 的报告生成工作流 - 多阶段 Agent 编排

    Args:
        task_id: 任务ID
        template_id: 模板ID
        data_source_id: 数据源ID
        user_id: 用户ID
        schedule: 调度信息
        skip_stages: 要跳过的阶段列表

    Returns:
        Dict[str, Any]: 执行结果
    """
    try:
        logger.info(f"开始多阶段报告生成 - 任务: {task_id}, 模板: {template_id}")

        # 更新任务状态
        self.update_state(
            state='PROGRESS',
            meta={
                'current_step': '初始化 Orchestrator',
                'progress': 5,
                'started_at': datetime.now().isoformat()
            }
        )

        # 创建 Orchestrator
        import asyncio
        from app.services.infrastructure.agents import ReportGenerationOrchestrator, OrchestratorContext
        from app.core.container import Container

        async def run_orchestration():
            container = Container()
            orchestrator = ReportGenerationOrchestrator(container=container)

            # 创建执行上下文
            context = OrchestratorContext(
                template_id=template_id,
                data_source_id=data_source_id,
                user_id=user_id,
                schedule=schedule,
                execution_time=datetime.now(),
            )

            # 执行编排流程
            all_events = []
            async for event in orchestrator.execute(context, skip_stages=skip_stages):
                all_events.append(event)

                # 更新 Celery 任务状态
                if event.get("type") == "stage_started":
                    progress = (event.get("stage_index", 0) / event.get("total_stages", 6)) * 100
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'current_step': f"执行阶段: {event.get('stage_name')}",
                            'progress': progress,
                            'stage_index': event.get("stage_index"),
                        }
                    )

                elif event.get("type") == "orchestration_failed":
                    self.update_state(
                        state='FAILURE',
                        meta={
                            'error': event.get("error"),
                            'failed_stage': event.get("failed_stage"),
                        }
                    )

            return {
                "context": context,
                "events": all_events,
            }

        # 执行异步编排
        result_data = asyncio.run(run_orchestration())
        context = result_data["context"]
        events = result_data["events"]

        # 构建返回结果
        result = {
            'success': True,
            'task_id': task_id,
            'template_id': template_id,
            'data_source_id': data_source_id,
            'user_id': user_id,
            'workflow_type': 'orchestrated_report_generation',
            'completed_at': datetime.now().isoformat(),
            'stage_results': {
                name: stage.to_dict()
                for name, stage in context.stage_results.items()
            },
            'total_events': len(events),
        }

        logger.info(f"多阶段报告生成完成 - 任务: {task_id}")
        return result

    except Exception as e:
        logger.error(f"多阶段报告生成失败 - 任务: {task_id}, 错误: {e}", exc_info=True)

        self.update_state(
            state='FAILURE',
            meta={
                'error': str(e),
                'task_id': task_id,
                'failed_at': datetime.now().isoformat()
            }
        )

        return {
            'success': False,
            'task_id': task_id,
            'error': str(e),
            'failed_at': datetime.now().isoformat()
        }


@celery_app.task(bind=True, name='analyze_placeholder_workflow')
def analyze_placeholder_workflow(
    self,
    template_id: str,
    data_source_id: str,
    user_id: str,
    force_reanalyze: bool = False,
    existing_sql: str = None
) -> Dict[str, Any]:
    """
    占位符分析工作流任务 - 使用任务验证智能模式

    Args:
        template_id: 模板ID
        data_source_id: 数据源ID
        user_id: 用户ID
        force_reanalyze: 强制重新分析
        existing_sql: 现有SQL（如果存在）

    Returns:
        Dict[str, Any]: 分析结果
    """
    try:
        logger.info(f"开始占位符分析工作流 - 模板: {template_id}, 数据源: {data_source_id}")

        # 更新任务状态
        self.update_state(
            state='PROGRESS',
            meta={
                'current_step': '初始化Agent系统',
                'progress': 10,
                'started_at': datetime.now().isoformat()
            }
        )

        # 使用Agent系统进行占位符分析
        import asyncio
        from app.services.infrastructure.agents import AgentService
        from app.services.infrastructure.agents.types import AgentInput, PlaceholderSpec, SchemaInfo, TaskContext
        from app.core.container import Container
        from app.db.session import get_db_session

        async def run_analysis():
            # 创建Agent门面
            container = Container()
            agent_service = AgentService(container=container)

            # 获取数据源信息和模板信息
            with get_db_session() as db:
                from app.models.data_source import DataSource
                from app.models.template import Template
                from uuid import UUID

                data_source = db.query(DataSource).filter(DataSource.id == UUID(data_source_id)).first()
                template = db.query(Template).filter(Template.id == UUID(template_id)).first()

                if not data_source or not template:
                    raise ValueError(f"数据源或模板不存在: data_source={data_source_id}, template={template_id}")

            # 更新进度
            self.update_state(
                state='PROGRESS',
                meta={
                    'current_step': '构建分析上下文',
                    'progress': 30,
                    'data_source_name': data_source.name,
                    'template_name': template.name
                }
            )

            # 构建数据源连接配置
            data_source_config = {
                "id": str(data_source_id),
                "data_source_id": str(data_source_id),
                "source_type": data_source.source_type.value if hasattr(data_source.source_type, 'value') else str(data_source.source_type),
                "database": getattr(data_source, 'doris_database', 'default_db'),
                "host": data_source.doris_fe_hosts[0] if data_source.doris_fe_hosts else None,
                "port": getattr(data_source, 'doris_fe_http_port', 8030),
                "username": getattr(data_source, 'username', None),
                "password": getattr(data_source, 'password', None)
            }

            # 构建Agent输入
            agent_input = AgentInput(
                user_prompt=f"分析模板 {template.name} 的占位符，生成或验证对应的数据查询SQL",
                placeholder=PlaceholderSpec(
                    description=f"模板占位符分析 - {template.name}",
                    type="template_analysis"
                ),
                schema=SchemaInfo(
                    database_name=getattr(data_source, 'doris_database', 'default_db'),
                    host=data_source.doris_fe_hosts[0] if data_source.doris_fe_hosts else None,
                    port=getattr(data_source, 'doris_fe_http_port', 8030),
                    username=getattr(data_source, 'username', None),
                    password=getattr(data_source, 'password', None)
                ),
                context=TaskContext(
                    task_time=int(datetime.now().timestamp()),
                    timezone="Asia/Shanghai"
                ),
                data_source=data_source_config,
                task_driven_context={
                    "template_id": template_id,
                    "template_name": template.name,
                    "template_content": template.content[:1000] if template.content else "",
                    "data_source_id": data_source_id,
                    "data_source_name": data_source.name,
                    "data_source_type": data_source.source_type.value if hasattr(data_source.source_type, 'value') else str(data_source.source_type),
                    "current_sql": existing_sql,
                    "force_reanalyze": force_reanalyze,
                    "analysis_type": "placeholder_workflow"
                },
                user_id=user_id
            )

            # 更新进度
            self.update_state(
                state='PROGRESS',
                meta={
                    'current_step': '执行智能分析和验证',
                    'progress': 50,
                    'mode': 'task_validation_intelligent'
                }
            )

            # 🎯 使用任务验证智能模式 - 核心调用
            result = await agent_service.execute_task_validation(agent_input)

            return result

        # 执行异步分析
        analysis_result = asyncio.run(run_analysis())

        # 更新进度
        self.update_state(
            state='PROGRESS',
            meta={
                'current_step': '处理分析结果',
                'progress': 80,
                'agent_success': analysis_result.success
            }
        )

        # 构建返回结果
        if analysis_result.success:
            final_result = {
                'success': True,
                'template_id': template_id,
                'data_source_id': data_source_id,
                'user_id': user_id,
                'force_reanalyze': force_reanalyze,
                'analysis_completed_at': datetime.now().isoformat(),
                'sql_content': analysis_result.result,
                'validation_info': analysis_result.metadata,
                'generation_method': analysis_result.metadata.get('generation_method', 'validation'),
                'time_updated': analysis_result.metadata.get('time_updated', False),
                'fallback_reason': analysis_result.metadata.get('fallback_reason'),
                'placeholders_analyzed': True,
                'sql_generated': True,
                'validation_passed': True,
                'message': f'占位符分析完成 - 方法: {analysis_result.metadata.get("generation_method", "validation")}'
            }
        else:
            final_result = {
                'success': False,
                'template_id': template_id,
                'data_source_id': data_source_id,
                'user_id': user_id,
                'error': analysis_result.metadata.get('error', '未知错误'),
                'validation_info': analysis_result.metadata,
                'failed_at': datetime.now().isoformat(),
                'message': 'Agent占位符分析失败'
            }

        logger.info(f"占位符分析工作流完成 - 模板: {template_id}, 成功: {analysis_result.success}")

        return final_result

    except Exception as e:
        logger.error(f"占位符分析工作流失败 - 模板: {template_id}, 错误: {e}")

        self.update_state(
            state='FAILURE',
            meta={
                'error': str(e),
                'template_id': template_id,
                'failed_at': datetime.now().isoformat()
            }
        )

        return {
            'success': False,
            'template_id': template_id,
            'error': str(e),
            'failed_at': datetime.now().isoformat()
        }
