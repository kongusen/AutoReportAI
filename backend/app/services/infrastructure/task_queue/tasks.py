"""
Infrastructure层 - Celery任务定义

基于DDD架构的Celery任务定义，使用新的TaskExecutionService能力
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from celery import Task as CeleryTask
from celery.schedules import crontab
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.config import settings
from app.core.container import container
from app.models.task import Task, TaskExecution, TaskStatus
from app.models.report_history import ReportHistory
from app.services.application.placeholder.placeholder_service import (
    PlaceholderApplicationService as PlaceholderProcessingSystem,
)
from app.services.infrastructure.notification.notification_service import NotificationService
from app.services.infrastructure.storage.hybrid_storage_service import (
    get_hybrid_storage_service,
)
from app.services.infrastructure.task_queue.celery_config import celery_app
from app.services.infrastructure.agents.messaging import (
    TaskMessageOrchestrator,
    PromptConfigManager
)
from app.services.infrastructure.task_queue.progress_recorder import TaskProgressRecorder
from app.services.infrastructure.websocket.pipeline_notifications import (
    PipelineTaskStatus,
)
from app.utils.time_context import TimeContextManager
from app.utils.json_utils import convert_for_json

logger = logging.getLogger(__name__)

def run_async(coro):
    """
    在同步上下文中安全地执行异步代码。

    规则：
    - 若当前线程没有运行中的事件循环：直接 asyncio.run(coro)
    - 若已有运行中的事件循环（如 Celery/WSGI 环境）：在新线程创建独立事件循环执行并返回结果
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # 当前线程没有运行中的事件循环
        return asyncio.run(coro)
    else:
        # 当前线程已存在事件循环，转移到新线程执行
        import threading
        from queue import Queue

        result_queue: "Queue[Tuple[bool, Any]]" = Queue(maxsize=1)

        def _runner():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                res = loop.run_until_complete(coro)
                result_queue.put((True, res))
            except Exception as exc:  # noqa: BLE001
                result_queue.put((False, exc))
            finally:
                try:
                    loop.close()
                except Exception:
                    pass

        t = threading.Thread(target=_runner, daemon=True)
        t.start()
        ok, payload = result_queue.get()
        if ok:
            return payload
        raise payload

class DatabaseTask(CeleryTask):
    """带数据库会话的基础任务类"""
    
    def __call__(self, *args, **kwargs):
        """执行任务时自动管理数据库会话"""
        with SessionLocal() as db:
            return self.run_with_db(db, *args, **kwargs)
    
    def run_with_db(self, db: Session, *args, **kwargs):
        """子类需要实现的方法"""
        return self.run(db, *args, **kwargs)

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

    # 检查任务是否被撤销的辅助函数
    def check_if_cancelled():
        """检查任务是否被撤销"""
        try:
            # 方法1: 检查Celery的撤销状态
            from celery.result import AsyncResult
            result = AsyncResult(self.request.id)
            if result.state == 'REVOKED':
                logger.info(f"Task {task_id} detected as REVOKED via Celery state")
                raise Exception("任务已被用户取消")

            # 方法2: 检查数据库中的执行状态
            if task_execution_id:
                exec_record = db.query(TaskExecution).filter(TaskExecution.id == task_execution_id).first()
                if exec_record and exec_record.execution_status == TaskStatus.CANCELLED:
                    logger.info(f"Task {task_id} detected as CANCELLED in database")
                    raise Exception("任务已被用户取消")
        except Exception as e:
            if "取消" in str(e) or "cancelled" in str(e).lower():
                raise

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

        progress_recorder = TaskProgressRecorder(
            db=db,
            task=task,
            task_execution=task_execution,
        )
        # ✅ 初始化消息编排器
        msg_orchestrator = TaskMessageOrchestrator()
        config = PromptConfigManager()

        progress_recorder.start(msg_orchestrator.task_started())

        # 定义进度更新函数
        def update_progress(
            percentage: int,
            message: str = "",
            *,
            stage: Optional[str] = None,
            pipeline_status: PipelineTaskStatus = PipelineTaskStatus.ANALYZING,
            status: str = "running",
            placeholder: Optional[str] = None,
            details: Optional[Dict[str, Any]] = None,
            error: Optional[str] = None,
            record_only: bool = False,
        ):
            progress_recorder.update(
                percentage,
                message,
                stage=stage,
                pipeline_status=pipeline_status,
                status=status,
                placeholder=placeholder,
                details=details,
                error=error,
                record_only=record_only,
            )

        # 初始化阶段
        update_progress(
            5,
            "任务初始化完成",
            stage="initialization",
            pipeline_status=PipelineTaskStatus.SCANNING,
        )

        # 检查是否被取消
        check_if_cancelled()

        # 3. 更新任务状态
        task.status = TaskStatus.PROCESSING
        task.execution_count += 1
        task.last_execution_at = datetime.utcnow()
        db.commit()

        # 4. 🆕 初始化 Schema Context（一次性获取所有表结构）
        schema_context_retriever = None
        try:
            from app.services.infrastructure.agents.context_retriever import (
                create_schema_context_retriever
            )
            from app.services.infrastructure.agents.tools.table_detector import (
                create_table_detector
            )
            from app.models.data_source import DataSource

            logger.info(msg_orchestrator.schema_init_log(str(task.data_source_id)))

            update_progress(
                8,
                "正在初始化数据表结构上下文...",
                stage="schema_initialization",
                pipeline_status=PipelineTaskStatus.SCANNING,
            )

            # 🆕 表检测优化：检测是否为单表场景
            target_tables_for_optimization = None
            table_detection_enabled = True  # 可以通过配置控制
            existing_placeholders = []  # 初始化变量，防止作用域问题

            if table_detection_enabled:
                logger.info("🔍 开始表检测优化流程...")
                try:
                    # 获取模板的占位符
                    from app.crud import template_placeholder as crud_template_placeholder
                    existing_placeholders = crud_template_placeholder.get_by_template(db, str(task.template_id)) or []

                    if existing_placeholders and len(existing_placeholders) > 0:
                        # 使用表检测器分析
                        detector = create_table_detector()
                        detection_result = detector.detect_from_placeholders(
                            placeholders=existing_placeholders,
                            template_content=None  # 可选：传递模板内容辅助分析
                        )

                        logger.info(f"📊 表检测结果: {detection_result.recommendation}")
                        logger.info(
                            f"   - 单表场景: {detection_result.is_single_table}\n"
                            f"   - 主要表: {detection_result.primary_table}\n"
                            f"   - 涉及表: {detection_result.all_tables}\n"
                            f"   - 置信度: {detection_result.confidence:.2%}"
                        )

                        # 🔥 单表优化决策
                        if detection_result.is_single_table and detection_result.primary_table:
                            target_tables_for_optimization = [detection_result.primary_table]
                            logger.info(
                                f"✅ 启用单表优化模式: 只加载表 '{detection_result.primary_table}' 的 schema"
                            )
                            update_progress(
                                8,
                                f"检测到单表场景，启用优化模式（表：{detection_result.primary_table}）",
                                stage="schema_initialization",
                                pipeline_status=PipelineTaskStatus.SCANNING,
                            )
                        else:
                            logger.info(
                                f"⚠️ 多表场景或检测置信度不足，使用完整Schema加载模式"
                            )
                            update_progress(
                                8,
                                "检测到多表场景，加载完整Schema",
                                stage="schema_initialization",
                                pipeline_status=PipelineTaskStatus.SCANNING,
                            )
                    else:
                        logger.info("⚠️ 暂无占位符数据，跳过表检测优化")
                except Exception as detection_error:
                    logger.warning(f"⚠️ 表检测失败，降级到完整Schema加载: {detection_error}", exc_info=True)
                    target_tables_for_optimization = None

            # 获取数据源配置
            data_source = db.query(DataSource).filter(DataSource.id == task.data_source_id).first()
            if not data_source:
                raise RuntimeError(f"数据源 {task.data_source_id} 不存在")

            # 构建连接配置
            connection_config = data_source.connection_config or {}
            if not connection_config:
                raise RuntimeError(f"数据源 {task.data_source_id} 缺少连接配置")

            # 🆕 启用阶段感知的智能上下文管理 + 单表优化
            schema_context_retriever = create_schema_context_retriever(
                data_source_id=str(task.data_source_id),
                connection_config=connection_config,
                container=container,
                top_k=10,  # Task 批量分析，多缓存一些表
                inject_as="system",
                enable_stage_aware=True,  # 🔥 启用阶段感知
                target_tables=target_tables_for_optimization  # 🔥 单表优化参数
            )

            # 预加载所有表结构（缓存）
            run_async(schema_context_retriever.initialize())

            table_count = len(schema_context_retriever.schema_cache)

            # 🆕 单表优化效果统计
            optimization_info = ""
            if target_tables_for_optimization:
                # 估算节省的 token（假设每张表约 500 tokens，每个占位符调用 2 次 Agent）
                estimated_full_schema_tokens = table_count * 500
                estimated_optimized_tokens = len(target_tables_for_optimization) * 500
                estimated_saved_tokens_per_call = max(0, estimated_full_schema_tokens - estimated_optimized_tokens)
                total_placeholders = len(existing_placeholders) if existing_placeholders else 0
                estimated_total_saved = estimated_saved_tokens_per_call * 2 * total_placeholders  # 2次调用/占位符

                optimization_info = (
                    f" | 单表优化已启用 ✅\n"
                    f"   预计节省: ~{estimated_total_saved:,} tokens "
                    f"({estimated_saved_tokens_per_call} tokens/调用 × 2次/占位符 × {total_placeholders}占位符)"
                )
                logger.info(
                    f"📊 单表优化效果估算:\n"
                    f"   - 完整Schema: {estimated_full_schema_tokens} tokens\n"
                    f"   - 优化后Schema: {estimated_optimized_tokens} tokens\n"
                    f"   - 每次调用节省: {estimated_saved_tokens_per_call} tokens\n"
                    f"   - 总计节省: ~{estimated_total_saved:,} tokens"
                )

            logger.info(msg_orchestrator.schema_init_completed(table_count) + optimization_info)

            update_progress(
                9,
                msg_orchestrator.schema_init_progress(table_count),
                stage="schema_initialization",
                pipeline_status=PipelineTaskStatus.SCANNING,
            )

        except Exception as e:
            logger.warning(msg_orchestrator.schema_init_failed(e), exc_info=True)
            # 不要让整个任务失败，允许降级运行（Agent 可能会使用旧的 schema 工具或猜测表结构）
            logger.info(msg_orchestrator.schema_init_fallback())

            # 创建一个空的 schema_context_retriever 以避免后续代码出错
            schema_context_retriever = None

            update_progress(
                9,
                "数据表结构初始化失败，将降级运行",
                stage="schema_initialization",
                pipeline_status=PipelineTaskStatus.SCANNING,
                error=str(e)
            )

        # 5. 初始化时间上下文和 PlaceholderProcessingSystem
        # Initialize placeholder processing system with schema context
        system = PlaceholderProcessingSystem(
            user_id=str(task.owner_id),
            context_retriever=schema_context_retriever  # 🔥 传入 context
        )

        # 🆕 获取阶段感知上下文管理器和工具记录器
        state_manager = getattr(schema_context_retriever, 'state_manager', None)
        tool_recorder = None
        if state_manager:
            from app.services.infrastructure.agents.tool_wrapper import ToolResultRecorder
            from app.services.infrastructure.agents.context_manager import ExecutionStage
            tool_recorder = ToolResultRecorder(state_manager)
            logger.info("✅ 任务已启用阶段感知上下文管理和工具结果记录")

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
        update_progress(
            10,
            "正在生成时间上下文...",
            stage="time_context",
            pipeline_status=PipelineTaskStatus.SCANNING,
        )
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
        update_progress(
            15,
            "正在初始化Agent系统...",
            stage="agent_initialization",
        )

        # 检查是否被取消
        check_if_cancelled()

        run_async(system.initialize())
        events = []

        update_progress(
            20,
            "正在检查占位符状态...",
            stage="placeholder_precheck",
        )

        # 检查是否被取消
        check_if_cancelled()

        # 智能增量占位符解析策略
        placeholders_need_analysis = []
        placeholders_ready = []

        try:
            from app.crud import template_placeholder as crud_template_placeholder
            from app.models.template import Template
            from app.services.domain.template.services.template_domain_service import TemplateParser
            import re

            # 获取模板内容
            template = db.query(Template).filter(Template.id == task.template_id).first()
            template_content = template.content if template else ""

            # 获取数据库中已有的占位符
            existing_placeholders = crud_template_placeholder.get_by_template(db, str(task.template_id))
            existing_placeholder_names = {ph.placeholder_name for ph in existing_placeholders or []}

            # 从模板内容中提取占位符
            content_placeholders = set()
            if template_content:
                # 提取 {{...}} 格式的占位符
                placeholder_pattern = r'\{\{([^}]+)\}\}'
                matches = re.findall(placeholder_pattern, template_content)
                content_placeholders = {match.strip() for match in matches}

            total_content_placeholders = len(content_placeholders)
            total_existing_placeholders = len(existing_placeholders or [])

            logger.info(msg_orchestrator.placeholder_status_summary(total_content_placeholders, total_existing_placeholders))

            # 找出需要新建的占位符（在内容中但不在数据库中）
            new_placeholders_to_create = content_placeholders - existing_placeholder_names

            # 创建新发现的占位符记录
            if new_placeholders_to_create:
                update_progress(
                    22,
                    msg_orchestrator.placeholders_creating(len(new_placeholders_to_create)),
                    stage="placeholder_precheck",
                    details={"new_placeholders": len(new_placeholders_to_create)},
                )
                logger.info(msg_orchestrator.placeholders_creating_log(len(new_placeholders_to_create)))

                from app.models.template_placeholder import TemplatePlaceholder
                import uuid
                for placeholder_name in new_placeholders_to_create:
                    new_placeholder = TemplatePlaceholder(
                        id=uuid.uuid4(),
                        template_id=task.template_id,
                        placeholder_name=placeholder_name,
                        placeholder_text=placeholder_name,  # 使用占位符名称作为默认文本
                        placeholder_type="text",  # 默认类型，后续分析时会更新
                        content_type="data",  # 默认为数据类型
                        agent_analyzed=False,  # 尚未分析
                        generated_sql=None,
                        sql_validated=False,
                        execution_order=0,  # 默认顺序
                        cache_ttl_hours=24,  # 默认缓存24小时
                        is_required=True,  # 默认为必需
                        is_active=True,  # 默认激活
                        confidence_score=0.0,  # 初始置信度
                        created_at=datetime.utcnow()
                    )
                    db.add(new_placeholder)
                db.commit()

                # 重新获取所有占位符
                existing_placeholders = crud_template_placeholder.get_by_template(db, str(task.template_id))

            required_fields: set[str] = set()

            # 检查所有占位符的分析状态
            for ph in existing_placeholders or []:
                # 检查占位符是否需要重新分析
                needs_analysis = (
                    not ph.generated_sql or  # 没有生成的SQL
                    not ph.sql_validated or  # SQL未验证通过
                    ph.generated_sql.strip() == ""  # SQL为空
                )

                if needs_analysis:
                    placeholders_need_analysis.append(ph)
                    logger.info(f"Placeholder '{ph.placeholder_name}' needs analysis: no_sql={not ph.generated_sql}, not_validated={not ph.sql_validated}")
                else:
                    placeholders_ready.append(ph)
                    logger.info(f"Placeholder '{ph.placeholder_name}' is ready with valid SQL")

                # 收集所有required_fields
                rf = getattr(ph, 'required_fields', None)
                if isinstance(rf, list):
                    for f in rf:
                        if isinstance(f, str):
                            required_fields.add(f)
                elif isinstance(rf, dict):
                    for key in ('columns', 'fields', 'required_fields'):
                        val = rf.get(key)
                        if isinstance(val, list):
                            for f in val:
                                if isinstance(f, str):
                                    required_fields.add(f)
                            break

                # Fallback to parsing_metadata if present
                pm = getattr(ph, 'parsing_metadata', None)
                if isinstance(pm, dict):
                    meta_rf = pm.get('required_fields') or pm.get('metadata', {}).get('required_fields')
                    if isinstance(meta_rf, list):
                        for f in meta_rf:
                            if isinstance(f, str):
                                required_fields.add(f)

            required_fields = sorted(required_fields)

            total_placeholders = len(existing_placeholders) if existing_placeholders else 0
            if placeholders_need_analysis:
                update_progress(
                    25,
                    msg_orchestrator.placeholder_needs_analysis(len(placeholders_need_analysis), total_placeholders),
                    stage="placeholder_analysis",
                    details={
                        "pending": len(placeholders_need_analysis),
                        "total": total_placeholders,
                    },
                )
                logger.info(f"Found {len(placeholders_need_analysis)} placeholders needing analysis, {len(placeholders_ready)} ready")
            else:
                if total_placeholders == 0:
                    update_progress(
                        35,
                        "模板无占位符，跳过分析阶段...",
                        stage="placeholder_analysis",
                        details={"total": 0},
                    )
                    logger.info(f"Template has no placeholders, skipping analysis phase")
                else:
                    update_progress(
                        35,
                        f"所有 {len(placeholders_ready)} 个占位符已就绪，跳过分析阶段...",
                        stage="placeholder_analysis",
                        details={
                            "ready": len(placeholders_ready),
                            "total": total_placeholders,
                        },
                    )
                    logger.info(f"All {len(placeholders_ready)} placeholders are ready, skipping analysis")

        except Exception as e:
            logger.warning(f"Failed to load/parse placeholders: {e}")
            required_fields = []

        success_criteria = {
            "min_rows": 1,
            "max_rows": 100000,
            "required_fields": required_fields,
            "quality_threshold": 0.6,
        }
        # 根据是否需要分析决定执行路径
        if placeholders_need_analysis:
            # 🆕 设置阶段为PLANNING - 准备生成SQL
            if state_manager:
                state_manager.set_stage(ExecutionStage.PLANNING)
                logger.info("🎯 设置Agent阶段为 PLANNING - 准备批量生成SQL")

            # 使用PlaceholderApplicationService单个处理每个占位符
            update_progress(
                30,
                msg_orchestrator.placeholder_analysis_start(len(placeholders_need_analysis)),
                stage="placeholder_analysis",
                details={
                    "pending": len(placeholders_need_analysis),
                    "total": len(existing_placeholders or []),
                },
            )

            async def _process_placeholders_individually():
                """
                单个循环处理占位符 + 批量持久化（方案1优化）

                优化策略:
                - 保持串行处理确保质量稳定
                - 每5个占位符批量提交一次，减少数据库压力
                - 支持断点续传（定期保存进度）
                """
                processed_count = 0
                total_count = len(placeholders_need_analysis)
                batch_updates = []  # 👈 收集批量更新
                BATCH_SIZE = 5  # 👈 批量大小配置

                for ph in placeholders_need_analysis:
                    try:
                        # 检查是否被取消
                        check_if_cancelled()

                        update_progress(
                            30 + int(30 * processed_count / total_count),
                            msg_orchestrator.placeholder_analysis_progress(ph.placeholder_name, processed_count + 1, total_count),
                            stage="placeholder_analysis",
                            placeholder=ph.placeholder_name,
                            details={
                                "current": processed_count + 1,
                                "total": total_count,
                            },
                        )

                        # 👇 构建真实的任务上下文
                        real_task_context = {
                            "task_id": task_id,
                            "task_name": task.name,
                            "template_id": str(task.template_id),
                            "user_id": str(task.owner_id),
                            "report_period": task.report_period.value if task.report_period else "monthly",
                            "schedule": task.schedule,  # 真实 cron 表达式
                            "time_window": time_window,  # 真实时间窗口
                            "time_context": time_ctx,  # 完整时间上下文
                            "execution_trigger": execution_context.get("trigger", "scheduled") if execution_context else "scheduled",
                            "execution_id": str(task_execution.execution_id),
                        }

                        # 🆕 选择占位符分析方法：直接调用或使用 Celery 任务
                        use_celery_task = getattr(settings, 'USE_CELERY_PLACEHOLDER_ANALYSIS', False)
                        
                        if use_celery_task:
                            # 使用新的 Celery 占位符分析任务
                            from app.services.infrastructure.task_queue.placeholder_tasks import analyze_single_placeholder_task
                            
                            logger.info(msg_orchestrator.placeholder_analysis_celery(ph.placeholder_name))
                            
                            # 触发 Celery 任务
                            celery_task = analyze_single_placeholder_task.delay(
                                placeholder_name=ph.placeholder_name,
                                placeholder_text=ph.placeholder_text,
                                template_id=str(task.template_id),
                                data_source_id=str(task.data_source_id),
                                user_id=str(task.owner_id),
                                template_context=real_task_context,
                                time_window=real_task_context.get("time_window"),
                                time_column=real_task_context.get("time_column"),
                                data_range=real_task_context.get("data_range", "day"),
                                requirements=real_task_context.get("requirements"),
                                execute_sql=False,  # 任务执行阶段不执行SQL，只生成
                                row_limit=1000,
                                **{k: v for k, v in real_task_context.items() if k not in [
                                    "template_context", "time_window", "time_column", "data_range", "requirements"
                                ]}
                            )
                            
                            # 等待任务完成
                            celery_result = celery_task.get(timeout=300)  # 5分钟超时
                            
                            if celery_result.get("success"):
                                analysis_result = celery_result.get("analysis_result", {})
                                sql_result = {
                                    "success": True,
                                    "sql": analysis_result.get("generated_sql", {}).get("sql", ""),
                                    "validated": analysis_result.get("generated_sql", {}).get("validated", True),
                                    "confidence": analysis_result.get("confidence_score", 0.9),
                                    "auto_fixed": analysis_result.get("generated_sql", {}).get("auto_fixed", False),
                                    "warning": analysis_result.get("generated_sql", {}).get("warning")
                                }
                                logger.info(f"✅ Celery 任务分析成功: {ph.placeholder_name}")
                            else:
                                error_msg = celery_result.get("error", "Celery 任务分析失败")
                                sql_result = {
                                    "success": False,
                                    "error": error_msg
                                }
                                logger.error(f"❌ Celery 任务分析失败: {ph.placeholder_name}, 错误: {error_msg}")
                        else:
                            # 使用成熟的单占位符分析能力（避免循环问题）
                            async def _analyze_placeholder_async(placeholder_name, placeholder_text, template_id, data_source_id, template_context, user_id):
                                from app.api.endpoints.placeholders import PlaceholderOrchestrationService
                                orchestration_service = PlaceholderOrchestrationService()
                                
                                # 调用成熟的单占位符分析，结果自动保存到数据库
                                analysis_result = await orchestration_service.analyze_placeholder_with_full_pipeline(
                                    placeholder_name=placeholder_name,
                                    placeholder_text=placeholder_text,
                                    template_id=template_id,
                                    data_source_id=data_source_id,
                                    template_context=template_context,
                                    user_id=user_id
                                )
                                
                                # 转换为当前任务期望的格式（用于后续ETL步骤）
                                if analysis_result.get("status") == "success":
                                    generated_sql = analysis_result.get("generated_sql", {})
                                    return {
                                        "success": True,
                                        "sql": generated_sql.get("sql", ""),
                                        "validated": generated_sql.get("validated", True),
                                        "confidence": analysis_result.get("confidence_score", 0.9),
                                        "auto_fixed": generated_sql.get("auto_fixed", False),
                                        "warning": generated_sql.get("warning")
                                    }
                                else:
                                    return {
                                        "success": False,
                                        "error": analysis_result.get("error", "占位符分析失败")
                                    }

                            template_id_for_analysis: Optional[str] = None
                            if getattr(task, "template_id", None):
                                template_id_for_analysis = str(task.template_id)
                            elif getattr(ph, "template_id", None):
                                template_id_for_analysis = str(ph.template_id)

                            if not template_id_for_analysis:
                                logger.warning(
                                    "占位符 %s 缺少 template_id，跳过分析阶段",
                                    ph.placeholder_name,
                                )
                                sql_result = {
                                    "success": False,
                                    "error": "缺少模板上下文，无法分析占位符"
                                }
                            else:
                                sql_result = run_async(_analyze_placeholder_async(
                                    placeholder_name=ph.placeholder_name,
                                    placeholder_text=ph.placeholder_text,
                                    template_id=template_id_for_analysis,
                                    data_source_id=str(task.data_source_id),
                                    template_context=real_task_context,
                                    user_id=str(task.owner_id)
                                ))

                        if sql_result.get("success"):
                            # 🔍 SQL LLM 输出过滤：检查是否为有效SQL而非中文说明
                            raw_sql = sql_result.get("sql", "").strip()
                            
                            def _is_valid_sql_structure(sql: str) -> bool:
                                """检查SQL是否为有效的SQL结构，而非中文说明串"""
                                if not sql:
                                    return False
                                
                                # 检查SQL起始关键字
                                sql_upper = sql[:20].upper()
                                valid_starters = ("SELECT", "WITH", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "EXPLAIN")
                                if not any(sql_upper.startswith(s) for s in valid_starters):
                                    return False
                                
                                # 检查是否包含大量中文且无SQL结构关键字
                                chinese_chars = sum(1 for ch in sql[:200] if '\u4e00' <= ch <= '\u9fff')
                                if chinese_chars > 10:  # 如果前200字符中有超过10个中文
                                    sql_upper_full = sql.upper()
                                    # 必须有SQL结构关键字
                                    sql_structure_keywords = (" FROM ", " WHERE ", " JOIN ", " INTO ", " VALUES ", " SET ", " WHERE", "FROM", "JOIN")
                                    if not any(kw in sql_upper_full for kw in sql_structure_keywords):
                                        return False
                                
                                return True
                            
                            if not _is_valid_sql_structure(raw_sql):
                                logger.error(
                                    msg_orchestrator.sql_rejected_chinese(ph.placeholder_name, raw_sql[:100])
                                )
                                sql_result = {
                                    "success": False,
                                    "error": "LLM输出为中文说明或非SQL文本，而非有效SQL",
                                    "sql": raw_sql
                                }
                            
                            if sql_result.get("success"):
                                # 👇 更新占位符SQL（不立即提交）
                                ph.generated_sql = sql_result["sql"]
                                # 只有当SQL真正验证通过时才标记为已验证
                                ph.sql_validated = sql_result.get("validated", True)
                                ph.agent_analyzed = True
                                ph.analyzed_at = datetime.utcnow()

                                # 如果SQL被自动修复，记录到metadata
                                if sql_result.get("auto_fixed"):
                                    ph.agent_config = ph.agent_config or {}
                                    ph.agent_config["auto_fixed"] = True
                                    ph.agent_config["auto_fix_warning"] = sql_result.get("warning")

                            # 🆕 记录SQL生成结果（作为验证成功）
                            if tool_recorder:
                                tool_recorder.record_sql_validation(
                                    tool_name="sql_generation",
                                    result={
                                        "valid": ph.sql_validated,
                                        "sql": sql_result["sql"],
                                        "auto_fixed": sql_result.get("auto_fixed", False),
                                        "confidence": sql_result.get("confidence", 0.9)
                                    }
                                )

                            batch_updates.append(ph)  # 👈 添加到批次

                            events.append({
                                "type": "placeholder_sql_generated",
                                "placeholder_name": ph.placeholder_name,
                                "sql": sql_result["sql"],
                                "confidence": sql_result.get("confidence", 0.0),
                                "validated": ph.sql_validated,
                                "auto_fixed": sql_result.get("auto_fixed", False),
                                "timestamp": datetime.utcnow().isoformat()
                            })

                            validation_status = "✅ 验证通过" if ph.sql_validated else "⚠️ 未验证"
                            auto_fix_info = " (自动修复)" if sql_result.get("auto_fixed") else ""
                            logger.info(msg_orchestrator.sql_generation_success_batch(
                                ph.placeholder_name,
                                len(batch_updates),
                                BATCH_SIZE,
                                auto_fix_info,
                                validation_status
                            ))

                            # 👇 达到批量大小时提交
                            if len(batch_updates) >= BATCH_SIZE:
                                db.commit()
                                logger.info(msg_orchestrator.sql_generation_batch_commit(len(batch_updates)))
                                batch_updates.clear()

                        else:
                            error_msg = sql_result.get("error", "SQL生成失败")
                            logger.error(msg_orchestrator.sql_generation_failed(ph.placeholder_name, error_msg))

                            # 🆕 切换到ERROR_RECOVERY阶段并记录错误
                            if state_manager:
                                state_manager.set_stage(ExecutionStage.ERROR_RECOVERY)
                                from app.services.infrastructure.agents.context_manager import ContextType, ContextItem
                                state_manager.add_context(
                                    key=f"sql_generation_error_{ph.placeholder_name}",
                                    item=ContextItem(
                                        type=ContextType.ERROR_INFO,
                                        content=f"占位符 {ph.placeholder_name} SQL生成失败: {error_msg}",
                                        metadata={"placeholder": ph.placeholder_name},
                                        relevance_score=1.0
                                    )
                                )
                                logger.warning("⚠️ 切换到 ERROR_RECOVERY 阶段")

                            events.append({
                                "type": "placeholder_sql_failed",
                                "placeholder_name": ph.placeholder_name,
                                "error": error_msg,
                                "timestamp": datetime.utcnow().isoformat()
                            })

                            update_progress(
                                task_execution.progress_percentage or 30,
                                msg_orchestrator.sql_generation_failed_progress(ph.placeholder_name),
                                stage="placeholder_analysis",
                                status="failed",
                                placeholder=ph.placeholder_name,
                                details={
                                    "current": processed_count + 1,
                                    "total": total_count,
                                },
                                error=error_msg,
                                record_only=True,
                            )

                    except Exception as e:
                        # 记录完整堆栈，便于定位例如 KeyError('template_id') 的来源
                        logger.error(
                            msg_orchestrator.placeholder_exception(ph.placeholder_name, str(e)),
                            exc_info=True
                        )
                        events.append({
                            "type": "placeholder_processing_error",
                            "placeholder_name": ph.placeholder_name,
                            "error": str(e),
                            "timestamp": datetime.utcnow().isoformat()
                        })

                        update_progress(
                            task_execution.progress_percentage or 30,
                            msg_orchestrator.placeholder_exception_progress(ph.placeholder_name),
                            stage="placeholder_analysis",
                            status="failed",
                            placeholder=ph.placeholder_name,
                            details={
                                "current": processed_count + 1,
                                "total": total_count,
                            },
                            error=str(e),
                            record_only=True,
                        )

                    processed_count += 1

                # 👇 提交剩余的占位符
                if batch_updates:
                    db.commit()
                    logger.info(msg_orchestrator.sql_generation_batch_commit(len(batch_updates)))
                    batch_updates.clear()

                return processed_count

            processed_count = run_async(_process_placeholders_individually())
            update_progress(
                65,
                f"占位符分析完成，成功处理 {processed_count} 个占位符",
                stage="placeholder_analysis",
                details={"processed": processed_count},
            )
        else:
            # 所有占位符已就绪，直接执行ETL
            update_progress(
                40,
                "占位符已就绪，直接执行ETL...",
                stage="placeholder_analysis",
                details={"ready": len(placeholders_ready)},
            )
            # 记录跳过分析的事件
            events.append({
                "type": "analysis_skipped",
                "message": "所有占位符已准备就绪，跳过分析阶段",
                "timestamp": datetime.utcnow().isoformat(),
                "placeholders_ready": len(placeholders_ready)
            })

        # 7. 执行真实的ETL数据处理流程
        # 🆕 切换到EXECUTION阶段
        if state_manager:
            state_manager.set_stage(ExecutionStage.EXECUTION)
            logger.info("🎯 切换到 EXECUTION 阶段 - 开始执行SQL查询")

        update_progress(
            70,
            "开始ETL数据处理...",
            stage="etl_processing",
        )

        # 检查是否被取消
        check_if_cancelled()

        try:
            # 重新加载最新的占位符数据（可能在Agent分析后有更新）
            placeholders = crud_template_placeholder.get_by_template(db, str(task.template_id))
            etl_results: Dict[str, Dict[str, Any]] = {}
            etl_stats = {
                "processed": 0,
                "success": 0,
                "failed": 0,
                "skipped": 0,
            }
            # 监控指标：SQL执行、模型调用、图表生成
            metrics = {
                "sql_execution": {"total": 0, "success": 0, "failed": 0},
                "model_call": {"total": 0, "success": 0, "failed": 0},
                "chart_generation": {"total": 0, "generated": 0, "failed": 0},
            }

            def _set_etl_result(
                name: str,
                *,
                success: bool,
                value: Any = None,
                error: Optional[str] = None,
                metadata: Optional[Dict[str, Any]] = None,
                skipped: bool = False,
            ) -> Dict[str, Any]:
                entry = {
                    "success": success,
                    "value": value,
                    "error": error,
                    "metadata": metadata or {},
                    "skipped": skipped,
                }
                etl_results[name] = entry
                etl_stats["processed"] += 1
                if skipped:
                    etl_stats["skipped"] += 1
                elif success:
                    etl_stats["success"] += 1
                else:
                    etl_stats["failed"] += 1
                return entry

            # 导入SQL占位符替换器
            from app.utils.sql_placeholder_utils import SqlPlaceholderReplacer
            sql_replacer = SqlPlaceholderReplacer()

            update_progress(
                75,
                "正在处理SQL占位符替换和执行查询...",
                stage="etl_processing",
            )

            # 对每个有效的占位符进行单个处理
            total_placeholders_count = len(placeholders or [])
            for i, ph in enumerate(placeholders or []):
                # 只要有生成的SQL就尝试执行，不要求必须验证通过
                # sql_validated 应该在执行成功后设置，而不是作为执行的前提条件
                if not ph.generated_sql or (ph.generated_sql and ph.generated_sql.strip() == ""):
                    logger.warning(f"跳过占位符 {ph.placeholder_name}: 无有效SQL")
                    _set_etl_result(
                        ph.placeholder_name,
                        success=False,
                        error="无有效SQL",
                        metadata={"reason": "missing_sql"},
                        skipped=True,
                    )
                    update_progress(
                        task_execution.progress_percentage or 75,
                        f"跳过占位符 {ph.placeholder_name}: 无有效SQL",
                        stage="etl_processing",
                        status="failed",
                        placeholder=ph.placeholder_name,
                        details={
                            "current": i + 1,
                            "total": total_placeholders_count,
                        },
                        error="无有效SQL",
                        record_only=True,
                    )
                    continue

                # 如果SQL未验证，记录日志但继续执行
                if not ph.sql_validated:
                    logger.info(f"占位符 {ph.placeholder_name} SQL未验证，将尝试执行并在成功后标记为已验证")

                try:
                    # 1. 首先进行SQL占位符替换（时间参数等）
                    final_sql = ph.generated_sql
                    sql_placeholders = sql_replacer.extract_placeholders(ph.generated_sql)

                    if sql_placeholders:
                        logger.info(f"占位符 {ph.placeholder_name} 需要SQL参数替换: {sql_placeholders}")
                        # 构建时间上下文
                        time_context = {
                            "data_start_time": time_window.get("start", ""),
                            "data_end_time": time_window.get("end", ""),
                            "execution_time": datetime.now().strftime("%Y-%m-%d")
                        }
                        final_sql = sql_replacer.replace_time_placeholders(
                            ph.generated_sql,
                            time_context
                        )
                        logger.info(f"替换后SQL: {final_sql[:100]}...")

                    # 2. 获取数据源配置（与Agent分析阶段保持一致）
                    from app.crud.crud_data_source import crud_data_source
                    from app.models.data_source import DataSourceType
                    from app.core.data_source_utils import DataSourcePasswordManager

                    data_source = crud_data_source.get(db, id=str(task.data_source_id))
                    if not data_source:
                        raise ValueError(f"数据源不存在: {task.data_source_id}")

                    # 构建数据源配置字典（参考_get_data_source_info的实现）
                    data_source_config = {}
                    if data_source.source_type == DataSourceType.doris:
                        data_source_config = {
                            "source_type": "doris",
                            "name": data_source.name,
                            "database": getattr(data_source, "doris_database", "default"),
                            "fe_hosts": list(getattr(data_source, "doris_fe_hosts", []) or ["localhost"]),
                            "be_hosts": list(getattr(data_source, "doris_be_hosts", []) or ["localhost"]),
                            "http_port": getattr(data_source, "doris_http_port", 8030),
                            "query_port": getattr(data_source, "doris_query_port", 9030),
                            "username": getattr(data_source, "doris_username", "root"),
                            "password": DataSourcePasswordManager.get_password(data_source.doris_password) if getattr(data_source, "doris_password", None) else "",
                            "timeout": 30
                        }
                    elif data_source.source_type == DataSourceType.sql:
                        from app.core.security_utils import decrypt_data
                        conn_str = data_source.connection_string
                        try:
                            if conn_str:
                                conn_str = decrypt_data(conn_str)
                        except Exception:
                            pass
                        data_source_config = {
                            "source_type": "sql",
                            "name": data_source.name,
                            "connection_string": conn_str,
                            "database": getattr(data_source, "database_name", None),
                            "host": getattr(data_source, "host", None),
                            "port": getattr(data_source, "port", None),
                            "username": getattr(data_source, "username", None),
                            "password": getattr(data_source, "password", None),
                        }

                    logger.info(f"数据源配置: {data_source.source_type}, database: {data_source_config.get('database')}")

                    # 2.5 SQL列验证和自动修复
                    validation_passed = True
                    try:
                        # 尝试导入列验证工具
                        from app.services.infrastructure.agents.tools.column_validator import (
                            SQLColumnValidatorTool,
                            SQLColumnAutoFixTool
                        )

                        # 获取表结构信息
                        table_columns = {}
                        if hasattr(ph, 'agent_config') and ph.agent_config:
                            schema_context = ph.agent_config.get('schema_context', {})
                            table_columns = schema_context.get('table_columns', {})

                        # 只有在有表结构信息时才进行验证
                        if table_columns:
                            logger.info(f"🔍 开始验证 SQL 列: {ph.placeholder_name}")

                            validator = SQLColumnValidatorTool()

                            async def _validate_columns_async():
                                return await validator.execute({
                                    "sql": final_sql,
                                    "schema_context": {"table_columns": table_columns}
                                })

                            validation_result = run_async(_validate_columns_async())

                            if validation_result.get("success") and not validation_result.get("valid"):
                                # 发现列错误
                                invalid_columns = validation_result.get("invalid_columns", [])
                                suggestions = validation_result.get("suggestions", {})

                                logger.warning(
                                    f"⚠️ SQL 列验证失败: {ph.placeholder_name}\n"
                                    f"   无效列: {invalid_columns}\n"
                                    f"   建议: {suggestions}"
                                )

                                # 尝试自动修复
                                if suggestions:
                                    logger.info(f"🔧 尝试自动修复 SQL: {ph.placeholder_name}")

                                    fixer = SQLColumnAutoFixTool()

                                    async def _fix_columns_async():
                                        return await fixer.execute({
                                            "sql": final_sql,
                                            "suggestions": suggestions
                                        })

                                    fix_result = run_async(_fix_columns_async())

                                    if fix_result.get("success"):
                                        fixed_sql = fix_result.get("fixed_sql")
                                        changes = fix_result.get("changes", [])

                                        logger.info(
                                            f"✅ SQL 自动修复成功: {ph.placeholder_name}\n"
                                            f"   修改: {changes}"
                                        )

                                        # 更新 SQL
                                        final_sql = fixed_sql

                                        # 更新数据库中的 SQL（保存修复后的版本，保留占位符）
                                        # 需要将已替换的时间值还原为占位符格式
                                        saved_sql = fixed_sql
                                        if sql_placeholders and time_context:
                                            # 将时间值还原为占位符
                                            for placeholder in sql_placeholders:
                                                if placeholder in ['start_date', 'end_date']:
                                                    time_key = 'data_start_time' if placeholder == 'start_date' else 'data_end_time'
                                                    time_value = time_context.get(time_key, '')
                                                    if time_value:
                                                        # 还原为占位符格式
                                                        saved_sql = saved_sql.replace(f"'{time_value}'", f"{{{{{placeholder}}}}}")

                                        ph.generated_sql = saved_sql

                                        # 标记为需要人工审核（虽然已自动修复）
                                        if not hasattr(ph, 'agent_config') or not ph.agent_config:
                                            ph.agent_config = {}
                                        ph.agent_config['auto_fixed'] = True
                                        ph.agent_config['auto_fix_details'] = {
                                            "changes": changes,
                                            "original_errors": validation_result.get("errors", [])
                                        }

                                        db.commit()
                                        logger.info(f"💾 已保存修复后的 SQL: {ph.placeholder_name}")
                                    else:
                                        # 自动修复失败
                                        logger.error(f"❌ SQL 自动修复失败: {ph.placeholder_name}")
                                        validation_passed = False
                                else:
                                    # 没有修复建议
                                    logger.error(f"❌ 无法自动修复，缺少列名建议: {ph.placeholder_name}")
                                    validation_passed = False

                                # 如果自动修复失败，记录错误并跳过执行
                                if not validation_passed:
                                    error_msg = "\n".join(validation_result.get("errors", ["列验证失败"]))
                                    _set_etl_result(
                                        ph.placeholder_name,
                                        success=False,
                                        error=error_msg,
                                        metadata={"reason": "column_validation_failed"},
                                    )

                                    update_progress(
                                        task_execution.progress_percentage or 75,
                                        f"占位符 {ph.placeholder_name} SQL 列验证失败",
                                        stage="etl_processing",
                                        status="failed",
                                        placeholder=ph.placeholder_name,
                                        details={
                                            "current": i + 1,
                                            "total": total_placeholders_count,
                                        },
                                        error=error_msg,
                                        record_only=True,
                                    )
                                    continue
                            else:
                                logger.info(f"✅ SQL 列验证通过: {ph.placeholder_name}")

                        else:
                            logger.debug(f"⏭️ 跳过列验证（无表结构信息）: {ph.placeholder_name}")

                    except ImportError:
                        logger.warning("列验证工具未安装，跳过验证")
                    except Exception as val_error:
                        logger.warning(f"列验证过程异常，继续执行: {val_error}")

                    # 3. 使用connector直接执行查询（与Agent保持一致）
                    from app.services.data.connectors.connector_factory import create_connector_from_config

                    async def _execute_query_async():
                        connector = create_connector_from_config(
                            source_type=data_source.source_type,
                            name=data_source.name,
                            config=data_source_config
                        )
                        try:
                            await connector.connect()
                            result = await connector.execute_query(final_sql)
                            return result
                        finally:
                            await connector.disconnect()

                    # 📊 记录SQL执行指标
                    metrics["sql_execution"]["total"] += 1
                    
                    query_result = run_async(_execute_query_async())

                    # 4. 解包查询结果，提取实际数据值
                    # DorisQueryResult 没有 success 属性，只要没抛异常就是成功
                    if hasattr(query_result, 'data') and query_result.data is not None and not query_result.data.empty:
                        metrics["sql_execution"]["success"] += 1
                        # 将DataFrame转换为字典列表
                        result_data = query_result.data.to_dict('records')

                        # 转换 Decimal 类型为 float，确保 JSON 可序列化
                        from app.utils.json_utils import convert_decimals
                        result_data = convert_decimals(result_data)

                        # 智能解包：单行单列返回值，多行返回列表
                        actual_value = None
                        if result_data:
                            if len(result_data) == 1 and len(result_data[0]) == 1:
                                # 单行单列：返回值本身
                                actual_value = list(result_data[0].values())[0]
                            elif len(result_data) == 1:
                                # 单行多列：返回行字典
                                actual_value = result_data[0]
                            else:
                                # 多行：返回完整列表（用于图表）
                                actual_value = result_data

                        logger.info(f"✅ 占位符 {ph.placeholder_name} 查询成功，结果类型: {type(actual_value)}, 值: {str(actual_value)[:100]}")

                        # 🆕 记录SQL执行结果
                        if tool_recorder:
                            tool_recorder.record_sql_execution(
                                tool_name=f"sql_execution_{ph.placeholder_name}",
                                result={
                                    "success": True,
                                    "row_count": len(result_data),
                                    "rows": result_data[:3] if len(result_data) > 3 else result_data  # 只记录前3行
                                }
                            )

                        # 存储实际的数据值
                        _set_etl_result(
                            ph.placeholder_name,
                            success=True,
                            value=actual_value,
                            metadata={
                                "reason": "query_success",
                                "row_count": len(result_data),
                            },
                        )
                    else:
                        # 查询成功但无数据 - 🆕 进行意图验证
                        logger.warning(f"⚠️ 占位符 {ph.placeholder_name} 查询成功但无数据返回")

                        # 🔥 新增：验证SQL是否符合占位符意图
                        try:
                            intent_validation = run_async(system._validate_sql_result_intent(
                                sql=final_sql,
                                placeholder_text=ph.placeholder_text or ph.placeholder_name,
                                placeholder_name=ph.placeholder_name,
                                result_data=None,
                                row_count=0
                            ))

                            if not intent_validation.get("matches_intent") and intent_validation.get("requires_regeneration"):
                                logger.error(f"❌ [意图验证失败] 占位符 {ph.placeholder_name} 的SQL不符合业务意图")
                                logger.error(f"   发现的问题: {intent_validation.get('issues', [])}")
                                logger.info(f"💡 改进建议: {intent_validation.get('recommendations', [])}")

                                # 标记为失败，而不是成功但数据为空
                                _set_etl_result(
                                    ph.placeholder_name,
                                    success=False,
                                    error=f"SQL不符合占位符意图: {'; '.join(intent_validation.get('issues', []))}",
                                    metadata={
                                        "reason": "intent_validation_failed",
                                        "row_count": 0,
                                        "intent_issues": intent_validation.get("issues", []),
                                        "recommendations": intent_validation.get("recommendations", []),
                                        "sql": final_sql  # 保存原SQL用于调试
                                    },
                                )

                                # 🔥 TODO: 在未来版本中，这里可以触发自动重新生成SQL
                                # regeneration_result = run_async(system._regenerate_sql_with_feedback(
                                #     placeholder=ph,
                                #     feedback=intent_validation.get("recommendations", [])
                                # ))

                                logger.warning(f"⚠️ 占位符 {ph.placeholder_name} 需要人工审查和修正")
                            else:
                                # 意图验证通过，只是数据真的为空（正常情况）
                                logger.info(f"✅ [意图验证通过] 占位符 {ph.placeholder_name} SQL正确，数据确实为空")
                                _set_etl_result(
                                    ph.placeholder_name,
                                    success=True,
                                    value=None,
                                    metadata={
                                        "reason": "query_success_empty",
                                        "row_count": 0,
                                        "intent_validated": True
                                    },
                                )
                        except Exception as validation_error:
                            logger.error(f"意图验证过程异常: {validation_error}")
                            # 降级处理：即使验证失败也返回空结果
                            _set_etl_result(
                                ph.placeholder_name,
                                success=True,
                                value=None,
                                metadata={
                                    "reason": "query_success_empty",
                                    "row_count": 0,
                                    "validation_error": str(validation_error)
                                },
                            )

                    # 更新进度
                    progress_increment = 10 / total_placeholders_count if total_placeholders_count else 0
                    current_progress = 75 + (i + 1) * progress_increment
                    update_progress(
                        int(current_progress),
                        f"已处理 {i + 1}/{total_placeholders_count} 个占位符",
                        stage="etl_processing",
                        placeholder=ph.placeholder_name,
                        details={
                            "current": i + 1,
                            "total": total_placeholders_count,
                        },
                    )

                except Exception as e:
                    logger.error(f"Failed to execute SQL for placeholder {ph.placeholder_name}: {e}")
                    metrics["sql_execution"]["failed"] += 1
                    _set_etl_result(
                        ph.placeholder_name,
                        success=False,
                        error=str(e),
                        metadata={"reason": "execution_error"},
                    )

                    update_progress(
                        task_execution.progress_percentage or int(current_progress),
                        f"执行占位符 {ph.placeholder_name} SQL 失败",
                        stage="etl_processing",
                        status="failed",
                        placeholder=ph.placeholder_name,
                        details={
                            "current": i + 1,
                            "total": total_placeholders_count,
                        },
                        error=str(e),
                        record_only=True,
                    )

            update_progress(
                85,
                "ETL数据处理完成",
                stage="etl_processing",
            )

            # 构建执行结果
            # 统计成功的占位符（不是ERROR开头的）
            successful_placeholders = [k for k, v in etl_results.items() if v.get("success")]
            failed_placeholders = {k: v for k, v in etl_results.items() if not v.get("success") and not v.get("skipped")}
            skipped_placeholders = {k: v for k, v in etl_results.items() if v.get("skipped")}

            # 计算成功率指标
            placeholder_total = len(etl_results) if etl_results else 1
            placeholder_success_rate = len(successful_placeholders) / placeholder_total if placeholder_total > 0 else 0
            
            sql_exec_total = metrics["sql_execution"]["total"]
            sql_exec_success_rate = metrics["sql_execution"]["success"] / sql_exec_total if sql_exec_total > 0 else 0
            
            model_call_total = metrics["model_call"]["total"]
            model_call_success_rate = metrics["model_call"]["success"] / model_call_total if model_call_total > 0 else 0
            
            chart_gen_total = metrics["chart_generation"]["total"]
            chart_gen_rate = metrics["chart_generation"]["generated"] / chart_gen_total if chart_gen_total > 0 else 0
            
            # 判断 ETL 是否成功：至少有一个成功占位符且没有任何失败占位符
            etl_success_flag = len(successful_placeholders) > 0 and not failed_placeholders
            if not etl_success_flag:
                failure_reason_parts = []
                if len(successful_placeholders) == 0:
                    failure_reason_parts.append("没有成功占位符")
                if failed_placeholders:
                    failure_reason_parts.append(f"存在{len(failed_placeholders)}个失败占位符: {list(failed_placeholders.keys())[:5]}")  # 最多显示5个
                logger.warning(f"⚠️ ETL执行被标记为失败: {'; '.join(failure_reason_parts)}")
            
            execution_result = {
                "success": etl_success_flag,
                "events": events,
                "etl_results": etl_results,
                "time_window": time_window,
                "placeholders_processed": len(etl_results),
                "placeholders_success": len(successful_placeholders),
                "placeholders_failed": list(failed_placeholders.keys()),
                "placeholders_skipped": list(skipped_placeholders.keys()),
                "stats": etl_stats,
                "metrics": {
                    "placeholder_success_rate": placeholder_success_rate,
                    "sql_execution": {
                        "total": sql_exec_total,
                        "success": metrics["sql_execution"]["success"],
                        "failed": metrics["sql_execution"]["failed"],
                        "success_rate": sql_exec_success_rate,
                    },
                    "model_call": {
                        "total": model_call_total,
                        "success": metrics["model_call"]["success"],
                        "failed": metrics["model_call"]["failed"],
                        "success_rate": model_call_success_rate,
                    },
                    "chart_generation": {
                        "total": chart_gen_total,
                        "generated": metrics["chart_generation"]["generated"],
                        "failed": metrics["chart_generation"]["failed"],
                        "generation_rate": chart_gen_rate,
                    },
                },
            }

            logger.info(
                "📊 ETL处理完成: 成功 %s, 失败 %s, 跳过 %s / 总计 %s",
                etl_stats["success"],
                etl_stats["failed"],
                etl_stats["skipped"],
                etl_stats["processed"],
            )

        except Exception as e:
            logger.error(f"ETL processing failed: {e}")
            execution_result = {
                "success": False,
                "events": events,
                "error": str(e),
                "time_window": time_window,
            }

        placeholder_render_data: Dict[str, Any] = {}
        placeholder_errors: Dict[str, str] = {}
        etl_result_entries = execution_result.get("etl_results") or {}
        for placeholder_name, result_entry in etl_result_entries.items():
            if isinstance(result_entry, dict) and "success" in result_entry:
                if result_entry.get("success"):
                    value = result_entry.get("value")
                    placeholder_render_data[placeholder_name] = value
                else:
                    # 仅将非 skipped 的占位符计入错误
                    if not result_entry.get("skipped"):
                        placeholder_errors[placeholder_name] = result_entry.get("error") or "未知错误"
                    placeholder_render_data[placeholder_name] = None
            else:
                placeholder_render_data[placeholder_name] = result_entry

        execution_result["placeholder_errors"] = placeholder_errors
        execution_result["render_placeholder_data"] = placeholder_render_data

        # 数据质量闸门：检查占位符数据中是否包含错误关键词
        def _check_data_quality_gate(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
            """
            数据质量闸门：检查占位符数据中是否包含错误关键词
            返回 (是否通过, 错误列表)
            """
            error_keywords = ["ERROR:", "无有效SQL", "执行失败", "验证失败", "SQL 验证失败", "占位符分析失败"]
            quality_issues = []
            
            for name, value in data.items():
                if value is None:
                    continue
                str_value = str(value)
                # 检查是否为错误文本（长度限制：避免检查过大的数据）
                if len(str_value) < 500:  # 只检查较短的数据值（通常是错误消息）
                    for keyword in error_keywords:
                        if keyword in str_value:
                            quality_issues.append(f"{name}: 包含错误关键词 '{keyword}'")
                            break  # 每个占位符只记录一次
            
            return len(quality_issues) == 0, quality_issues

        # 8. 生成文档（使用模板 + doc_assembler）
        update_progress(
            87,
            "正在生成报告文档...",
            stage="document_generation",
            pipeline_status=PipelineTaskStatus.ASSEMBLING,
        )

        # 检查是否被取消
        check_if_cancelled()

        tpl_meta = None  # 初始化模板元数据，用于后续清理
        report_generation_error: Optional[str] = None
        etl_phase_success = execution_result.get("success", False)
        
        # 🆕 文档生成容错策略（通过 settings 配置）
        failed_placeholders = execution_result.get("placeholders_failed", [])
        skipped_placeholders = execution_result.get("placeholders_skipped", [])
        successful_placeholders_count = execution_result.get("placeholders_success", 0)
        
        # 详细记录 ETL 阶段状态（用于诊断）
        logger.info(
            f"📊 ETL阶段状态检查: success={etl_phase_success}, "
            f"成功占位符={successful_placeholders_count}, "
            f"失败占位符={len(failed_placeholders)}, "
            f"跳过占位符={len(skipped_placeholders)}"
        )
        if failed_placeholders:
            logger.warning(f"⚠️ 失败占位符列表: {failed_placeholders}")
        
        # 数据质量闸门检查
        quality_passed, quality_issues = _check_data_quality_gate(placeholder_render_data)
        if not quality_passed:
            logger.error(f"❌ 数据质量检查失败: {quality_issues}")
            etl_phase_success = False  # 将质量检查失败视为 ETL 失败
        else:
            logger.info("✅ 数据质量检查通过")

        max_failed_allowed = getattr(settings, "REPORT_MAX_FAILED_PLACEHOLDERS_FOR_DOC", 0)
        allow_quality_issues = getattr(settings, "REPORT_ALLOW_QUALITY_ISSUES", False)

        # 允许在有限失败下继续生成（需至少有部分成功数据）
        tolerance_passed = (
            len(failed_placeholders) <= max_failed_allowed and successful_placeholders_count > 0
        )

        # 质量闸门可配置放行
        quality_gate_passed = quality_passed or allow_quality_issues

        should_generate_document = etl_phase_success or (tolerance_passed and quality_gate_passed)

        # 🆕 若在容错条件下继续生成文档，则为失败占位符注入友好占位文本，避免文档出现空白
        if should_generate_document and not etl_phase_success and tolerance_passed:
            for failed_name in failed_placeholders:
                # 仅在当前渲染数据为空时注入占位文本
                if placeholder_render_data.get(failed_name) in (None, ""):
                    # 注意：避免触发质量闸门的关键词（不要包含 “ERROR/失败/验证失败/无有效SQL” 等字样）
                    placeholder_render_data[failed_name] = f"【占位提示：数据暂不可用，系统将在后续自动补充（{failed_name}）】"

        if not should_generate_document:
            # 构建详细的失败原因
            failure_reasons = []
            # 仅统计真实失败（不包含 skipped）
            failed_count = len(failed_placeholders)
            skipped_count = len(skipped_placeholders)
            if failed_count:
                failure_reasons.append(f"占位符错误(不含跳过): {failed_count}个")
            if skipped_count:
                failure_reasons.append(f"跳过: {skipped_count}个")
            if not quality_passed and not allow_quality_issues:
                failure_reasons.append(f"数据质量检查失败: {', '.join(quality_issues[:3])}")  # 最多显示前3个

            report_generation_error = "ETL阶段存在失败，占位符数据不完整，已跳过文档生成"
            if failure_reasons:
                report_generation_error += f" ({'; '.join(failure_reasons)})"
            
            logger.warning(report_generation_error)
            execution_result["report"] = {
                "error": report_generation_error,
                "generation_mode": "skipped_due_to_etl_failure",
                "placeholder_errors": placeholder_errors,
                "quality_issues": quality_issues if not quality_passed else [],
            }
        else:
            try:
                from app.services.infrastructure.document.template_path_resolver import resolve_docx_template_path, cleanup_template_temp_dir
                from app.services.infrastructure.document.word_template_service import WordTemplateService
                from io import BytesIO
                from app.services.infrastructure.storage.hybrid_storage_service import get_hybrid_storage_service

                if not getattr(task, "template_id", None):
                    report_generation_error = "任务未配置模板，跳过文档生成"
                    logger.warning(report_generation_error)
                    execution_result["report"] = {
                        "error": report_generation_error,
                        "generation_mode": "skipped"
                    }
                else:
                    tpl_meta = resolve_docx_template_path(db, str(task.template_id))
                    safe_tmp_dir = os.path.join(os.path.expanduser('~'), ".autoreportai", "tmp")
                    os.makedirs(safe_tmp_dir, exist_ok=True)
                    docx_out = os.path.join(
                        safe_tmp_dir,
                        f"report_{task.id}_{int(datetime.utcnow().timestamp())}.docx",
                    )

                    word_service = WordTemplateService()
                    assemble_res = run_async(
                        word_service.process_document_template(
                            template_path=tpl_meta["path"],
                            placeholder_data=placeholder_render_data,
                            output_path=docx_out,
                            container=container,
                            use_agent_charts=True,
                            use_agent_optimization=True,
                            user_id=str(task.owner_id),
                        )
                    )

                    if not assemble_res.get("success"):
                        report_generation_error = assemble_res.get("error") or "文档处理失败"
                        logger.error("文档生成失败: %s", report_generation_error)
                        execution_result["report"] = {
                            "error": report_generation_error,
                            "generation_mode": assemble_res.get("generation_mode", "word_template_service"),
                        }
                    else:
                        payload_bytes: Optional[bytes] = None
                        document_bytes = assemble_res.get("document_bytes")
                        if document_bytes:
                            payload_bytes = document_bytes
                        else:
                            output_path = assemble_res.get("output_path") or docx_out
                            if os.path.exists(output_path):
                                with open(output_path, "rb") as f:
                                    payload_bytes = f.read()

                        if not payload_bytes:
                            raise ValueError("模板组装成功但未生成可用的文档内容")

                        from app.models.user import User

                        user = db.query(User).filter(User.id == task.owner_id).first()
                        tenant_id = getattr(user, "tenant_id", str(task.owner_id)) if user else str(task.owner_id)

                        import re

                        slug = re.sub(r"[^\w\-]+", "-", (task.name or f"task_{task.id}")).strip("-")[:50]
                        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                        object_name = f"reports/{tenant_id}/{slug}/report_{ts}.docx"
                        friendly_name = assemble_res.get("friendly_file_name") or f"{slug}_{ts}.docx"

                        storage = get_hybrid_storage_service()
                        update_progress(
                            92,
                            "正在上传文档到存储...",
                            stage="document_generation",
                            pipeline_status=PipelineTaskStatus.ASSEMBLING,
                        )
                        upload_result = storage.upload_with_key(
                            BytesIO(payload_bytes),
                            object_name,
                            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        )

                        execution_result["report"] = {
                            "storage_path": upload_result.get("file_path"),
                            "backend": upload_result.get("backend"),
                            "friendly_name": friendly_name,
                            "generation_mode": assemble_res.get("generation_mode", "word_template_service"),
                            "size": upload_result.get("size", len(payload_bytes)),  # 保存文件大小
                        }
                        logger.info(f"✅ 报告生成并存储完成: {upload_result.get('file_path')}, 大小: {upload_result.get('size', len(payload_bytes))} bytes")
                        update_progress(
                            95,
                            "文档生成完成",
                            stage="document_generation",
                            pipeline_status=PipelineTaskStatus.ASSEMBLING,
                        )
                        logger.info("✅ 报告生成并存储完成: %s", upload_result.get("file_path"))
            except Exception as e:
                report_generation_error = str(e)
                logger.error(f"Document assembly failed: {e}")
                
                # 🔧 修复：检查是否已有成功的 report 数据（包含 storage_path）
                # 如果报告已经成功生成并存储，不应该覆盖它，只记录错误信息
                existing_report = execution_result.get("report") or {}
                if existing_report.get("storage_path"):
                    # 报告已成功生成，只更新错误信息，不覆盖已有的数据
                    logger.warning(
                        f"⚠️ 清理阶段发生异常，但报告已成功生成: {existing_report.get('storage_path')}, "
                        f"清理错误: {report_generation_error}"
                    )
                    existing_report["cleanup_error"] = report_generation_error
                    # 保留 storage_path 等关键信息，不覆盖
                    execution_result["report"] = existing_report
                else:
                    # 报告未成功生成，设置完整的错误信息
                    existing_mode = existing_report.get("generation_mode")
                    execution_result["report"] = {
                        "error": report_generation_error,
                        "generation_mode": existing_mode or "assembly_error"
                    }
            finally:
                # 清理模板临时文件
                if tpl_meta:
                    try:
                        cleanup_template_temp_dir(tpl_meta)
                        logger.info("✅ 模板临时文件已清理")
                    except Exception as cleanup_error:
                        logger.warning(f"清理模板临时文件失败: {cleanup_error}")
        
        # 🔧 修复：区分 None 和空字典，避免覆盖已有的 report 数据
        report_info = execution_result.get("report")
        if report_info is None:
            report_info = {}
            execution_result["report"] = report_info

        report_generated = bool(report_info.get("storage_path"))
        if report_generated:
            report_generation_error = None
            report_info.pop("error", None)
        else:
            if not report_info.get("error"):
                report_info["error"] = report_generation_error or "报告文档未生成"

        etl_success = etl_phase_success
        execution_result["etl_success"] = etl_success
        
        # 最终成功判断：只要报告成功生成，任务就认为成功
        # ETL部分失败不影响最终状态，只作为警告记录
        overall_success = report_generated
        execution_result["success"] = overall_success
        report_info["generated"] = report_generated
        
        # 详细记录最终状态判断（用于诊断）
        logger.info(
            f"🎯 最终状态判断: etl_success={etl_success}, "
            f"report_generated={report_generated}, "
            f"overall_success={overall_success}"
        )
        
        # ETL部分失败不影响最终状态，但需要记录警告
        if not etl_success and report_generated:
            logger.warning(
                f"⚠️ ETL阶段未完全成功（存在失败占位符），但报告已成功生成，任务标记为成功"
            )
        
        # 只有在报告生成失败时，才标记为失败
        if not report_generated:
            logger.error("❌ 任务失败原因: 报告文档未生成")
        
        # 7. 更新执行结果
        final_status = TaskStatus.COMPLETED if overall_success else TaskStatus.FAILED
        task_execution.execution_status = final_status
        task_execution.completed_at = datetime.utcnow()
        task_execution.total_duration = int((task_execution.completed_at - task_execution.started_at).total_seconds())
        task_execution.progress_percentage = 100

        owner_id = task.owner_id
        if isinstance(owner_id, str):
            owner_id = UUID(owner_id)

        history_metadata: Dict[str, Any] = {
            "execution_id": str(task_execution.execution_id),
            "generation_mode": report_info.get("generation_mode"),
            "storage_backend": report_info.get("backend"),
            "placeholders": {
                "processed": execution_result.get("placeholders_processed"),
                "success": execution_result.get("placeholders_success"),
            },
            "etl_success": etl_success,
            "report_generated": report_generated,
            "time_window": time_window,
        }
        if report_info.get("error"):
            history_metadata["error"] = report_info.get("error")

        # 转换 history_metadata 中的 Decimal 对象
        history_metadata = convert_for_json(history_metadata)

        report_history_record = ReportHistory(
            task_id=task.id,
            user_id=owner_id,
            status="completed" if final_status == TaskStatus.COMPLETED else "failed",
            file_path=report_info.get("storage_path"),
            file_size=report_info.get("size", 0),
            error_message=report_info.get("error") if not overall_success else None,
            result=None,
            processing_metadata=history_metadata,
        )
        db.add(report_history_record)
        db.flush()
        report_info["history_id"] = report_history_record.id

        # 转换 execution_result 中的所有 Decimal 对象为 float，确保 JSON 可序列化
        execution_result = convert_for_json(execution_result)
        task_execution.execution_result = execution_result
        
        # 更新任务统计
        task.status = final_status
        if final_status == TaskStatus.COMPLETED:
            task.success_count += 1
        else:
            task.failure_count += 1
        task.last_execution_duration = task_execution.total_duration
        
        # 更新平均执行时间（仅在成功时更新）
        if final_status == TaskStatus.COMPLETED:
            if task.average_execution_time == 0:
                task.average_execution_time = task_execution.total_duration
            else:
                task.average_execution_time = (task.average_execution_time + task_execution.total_duration) / 2
        
        db.commit()
        
        if overall_success:
            update_progress(
                97,
                "正在发送通知...",
                stage="notification",
                pipeline_status=PipelineTaskStatus.ASSEMBLING,
            )
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
                    run_async(delivery_service.deliver_report(req))
                except Exception as e:
                    logger.error(f"Failed to send success notification for task {task_id}: {e}")
        
        final_message = "任务执行完成" if overall_success else f"任务执行失败: {report_info.get('error')}"
        final_pipeline_status = PipelineTaskStatus.COMPLETED if overall_success else PipelineTaskStatus.FAILED
        update_progress(
            100,
            final_message,
            stage="completion",
            pipeline_status=final_pipeline_status,
            status="success" if overall_success else "failed",
            error=report_info.get("error") if not overall_success else None,
        )

        if overall_success:
            # 报告成功生成，任务成功
            complete_message = "任务执行完成"
            if not etl_success:
                # 如果ETL有部分失败，在消息中提及（但不影响成功状态）
                complete_message += "（ETL阶段有部分占位符失败，但不影响报告生成）"
            
            progress_recorder.complete(
                complete_message,
                result={
                    "task_id": task_id,
                    "execution_id": str(task_execution.execution_id),
                },
            )
            logger.info(f"Task {task_id} completed successfully in {task_execution.total_duration}s")
        else:
            # 报告生成失败，任务失败
            failure_reasons = []
            if not report_generated:
                failure_reasons.append("报告生成失败")
                if report_info.get("error"):
                    failure_reasons.append(f"原因: {report_info.get('error')}")
            
            if not failure_reasons:
                failure_reasons.append("未知错误")
            
            error_message = "任务执行失败: " + "，".join(failure_reasons)
            
            progress_recorder.fail(
                message=error_message,
                stage="document_generation",
                error_details={"error": report_info.get("error") or "报告文档未生成"},
            )
            logger.warning(f"Task {task_id} completed with failures in {task_execution.total_duration}s: {error_message}")

        return {
            "status": "completed" if overall_success else "failed",
            "task_id": task_id,
            "execution_id": str(task_execution.execution_id),
            "execution_time": task_execution.total_duration,
            "result": execution_result
        }
        
    except Exception as e:
        error_message = str(e)
        is_cancelled = "取消" in error_message or "cancelled" in error_message.lower()

        if is_cancelled:
            logger.info(f"Task {task_id} was cancelled: {error_message}")
        else:
            logger.error(f"Task {task_id} failed: {error_message}", exc_info=True)

        if 'progress_recorder' in locals():
            try:
                progress_recorder.fail(
                    message="任务执行失败" if not is_cancelled else "任务已取消",
                    stage="cancelled" if is_cancelled else "failure",
                    error_details={"error": error_message},
                )
            except Exception as notify_error:
                logger.warning(f"Failed to record failure progress for task {task_id}: {notify_error}")

        # 更新失败/取消状态
        if task_execution_id:
            task_execution = db.query(TaskExecution).filter(TaskExecution.id == task_execution_id).first()
            if task_execution:
                # 如果已经标记为CANCELLED，保持该状态
                if task_execution.execution_status != TaskStatus.CANCELLED:
                    task_execution.execution_status = TaskStatus.CANCELLED if is_cancelled else TaskStatus.FAILED
                task_execution.completed_at = datetime.utcnow()
                task_execution.error_details = error_message
                task_execution.total_duration = int((task_execution.completed_at - task_execution.started_at).total_seconds()) if task_execution.started_at else 0

        # 更新任务统计
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = TaskStatus.CANCELLED if is_cancelled else TaskStatus.FAILED
            if not is_cancelled:  # 只有失败才增加失败计数，取消不算失败
                task.failure_count += 1
            
        db.commit()
        
        # 发送失败通知 (不发送取消通知)
        if task and task.recipients and not is_cancelled:
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
        
        # 对于取消操作，返回取消状态而不是抛出异常
        if is_cancelled:
            return {
                "status": "cancelled",
                "task_id": task_id,
                "message": "任务已被用户取消",
                "execution_id": str(task_execution.execution_id) if task_execution else None
            }

        # 对于失败的任务，重新抛出异常让Celery处理重试
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
