"""
任务执行服务 - 完整的报告生成流水线

集成所有组件，提供完整的任务执行流程：
1. 占位符验证和修复
2. ETL数据处理
3. 图表生成
4. Word文档导出
5. 文件存储和邮件发送
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    VALIDATING = "validating"
    PROCESSING = "processing"
    GENERATING = "generating"
    EXPORTING = "exporting"
    DELIVERING = "delivering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskExecutionRequest:
    """任务执行请求"""
    task_id: str
    template_id: str
    data_source_ids: List[str]
    user_id: str
    execution_context: Dict[str, Any]
    time_context: Optional[Dict[str, Any]] = None
    output_format: str = "docx"
    delivery_config: Optional[Dict[str, Any]] = None
    
    
@dataclass
class TaskExecutionResult:
    """任务执行结果"""
    task_id: str
    status: TaskStatus
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_seconds: float = 0.0
    artifacts: Optional[Dict[str, str]] = None  # 生成的文件路径


class TaskExecutionService:
    """
    任务执行服务
    
    提供完整的报告生成任务执行流水线，集成：
    - 占位符验证和修复服务
    - ETL数据处理服务
    - 图表生成服务
    - 文档导出服务
    - 文件存储和邮件服务
    """
    
    def __init__(self, user_id: str = None):
        # user_id made optional for compatibility with new architecture
        self.user_id = user_id
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        # Import TimeContextManager here to avoid circular imports
        from app.utils.time_context import TimeContextManager
        from app.utils.sql_placeholder_utils import SqlPlaceholderReplacer
        self.time_context_manager = TimeContextManager()
        self.sql_replacer = SqlPlaceholderReplacer()
        
    async def execute_task(self, request: TaskExecutionRequest) -> TaskExecutionResult:
        """
        执行完整任务流程
        
        Args:
            request: 任务执行请求
            
        Returns:
            任务执行结果
        """
        start_time = datetime.now()
        task_id = request.task_id
        
        logger.info(f"开始执行任务: {task_id}")
        
        # 初始化任务状态
        self.active_tasks[task_id] = {
            "status": TaskStatus.PENDING,
            "start_time": start_time,
            "current_step": "初始化",
            "progress": 0.0
        }
        
        # 新版：直接委托给 Agents 流水线，保持接口不变
        return await self._execute_with_agents(request, start_time)

        
        try:
            # Step 1: 占位符验证和修复
            await self._update_task_status(task_id, TaskStatus.VALIDATING, "验证和修复占位符", 10.0)
            placeholder_results = await self._validate_and_repair_placeholders(request)
            
            if not placeholder_results["success"]:
                return self._create_error_result(request, "占位符验证失败", placeholder_results["error"])
            
            # Step 2: ETL数据处理
            await self._update_task_status(task_id, TaskStatus.PROCESSING, "ETL数据处理", 30.0)
            etl_results = await self._execute_etl_pipeline(request, placeholder_results["data"])
            
            if not etl_results["success"]:
                return self._create_error_result(request, "ETL处理失败", etl_results["error"])
            
            # Step 3: 图表生成
            await self._update_task_status(task_id, TaskStatus.GENERATING, "生成图表", 50.0)
            chart_results = await self._generate_charts(request, etl_results["data"])
            
            if not chart_results["success"]:
                return self._create_error_result(request, "图表生成失败", chart_results["error"])
            
            # Step 4: 文档导出
            await self._update_task_status(task_id, TaskStatus.EXPORTING, "导出文档", 70.0)
            export_results = await self._export_document(request, {
                "placeholder_data": placeholder_results["data"],
                "etl_data": etl_results["data"],
                "chart_data": chart_results["data"]
            })
            
            if not export_results["success"]:
                return self._create_error_result(request, "文档导出失败", export_results["error"])
            
            # Step 5: 文件存储和邮件发送
            await self._update_task_status(task_id, TaskStatus.DELIVERING, "存储和发送", 90.0)
            delivery_results = await self._deliver_report(request, export_results["data"])
            
            if not delivery_results["success"]:
                return self._create_error_result(request, "报告投递失败", delivery_results["error"])
            
            # 完成任务
            await self._update_task_status(task_id, TaskStatus.COMPLETED, "任务完成", 100.0)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 清理任务状态
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            
            logger.info(f"任务执行完成: {task_id}, 耗时: {execution_time:.2f}秒")
            
            return TaskExecutionResult(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                success=True,
                message="任务执行成功",
                data={
                    "placeholder_results": placeholder_results["data"],
                    "etl_results": etl_results["data"],
                    "chart_results": chart_results["data"],
                    "export_results": export_results["data"],
                    "delivery_results": delivery_results["data"]
                },
                execution_time_seconds=execution_time,
                artifacts=export_results["data"].get("artifacts", {})
            )
            
        except Exception as e:
            logger.error(f"任务执行异常: {task_id}, 错误: {e}")
            return self._create_error_result(request, "任务执行异常", str(e))

    async def execute_with_persistence(self, request: TaskExecutionRequest) -> TaskExecutionResult:
        """
        执行任务（包含完整的ETL数据持久化）

        核心流程：
        1. 准备占位符
        2. 执行ETL
        3. 持久化ETL数据 ← 新增
        4. 生成报告
        5. 统一commit ← 关键

        Args:
            request: 任务执行请求

        Returns:
            任务执行结果
        """
        from app.db.session import get_db_session
        from app.services.data.persistence.etl_persistence_service import ETLPersistenceService

        start_time = datetime.now()
        task_id = request.task_id

        # 生成批次ID
        batch_id = ETLPersistenceService.generate_batch_id()

        logger.info(f"🚀 开始执行任务（持久化模式）: {task_id}, batch_id={batch_id}")

        # 初始化任务状态
        self.active_tasks[task_id] = {
            "status": TaskStatus.PENDING,
            "start_time": start_time,
            "current_step": "初始化",
            "progress": 0.0,
            "batch_id": batch_id
        }

        with get_db_session() as db:
            try:
                # Step 1: 准备占位符数据
                await self._update_task_status(task_id, TaskStatus.VALIDATING, "准备占位符数据", 10.0)
                placeholder_data = await self._prepare_placeholder_data(request)
                logger.info(f"✅ 占位符准备完成: {len(placeholder_data.get('placeholder_sql_map', {}))} 个")

                # Step 2: 执行ETL数据提取
                await self._update_task_status(task_id, TaskStatus.PROCESSING, "ETL数据提取", 30.0)
                etl_result = await self._execute_etl_pipeline(request, placeholder_data)

                if not etl_result.get("success"):
                    raise Exception(f"ETL执行失败: {etl_result.get('error')}")

                etl_data = etl_result.get("data", {})
                logger.info(f"✅ ETL执行完成")

                # 🔑 Step 3: 持久化ETL结果（新增）
                await self._update_task_status(task_id, TaskStatus.PROCESSING, "持久化ETL数据", 50.0)
                persistence_service = ETLPersistenceService(db)
                persistence_result = await persistence_service.persist_etl_results(
                    template_id=request.template_id,
                    etl_results=etl_data,
                    batch_id=batch_id,
                    time_context=request.time_context or {}
                )

                logger.info(f"✅ {persistence_result['message']}")

                # Step 4: 生成报告
                await self._update_task_status(task_id, TaskStatus.GENERATING, "生成报告", 70.0)
                report_result = await self._generate_report(request, etl_data)

                if not report_result.get("success"):
                    raise Exception(f"报告生成失败: {report_result.get('error')}")

                logger.info(f"✅ 报告生成完成")

                # 🔑 Step 5: 统一提交事务
                db.commit()
                await self._update_task_status(task_id, TaskStatus.COMPLETED, "任务完成", 100.0)
                logger.info(f"✅ 事务提交成功: batch_id={batch_id}")

                execution_time = (datetime.now() - start_time).total_seconds()

                # 清理任务状态
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]

                logger.info(f"✅ 任务执行完成: {task_id}, 耗时: {execution_time:.2f}秒")

                return TaskExecutionResult(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    success=True,
                    message="任务执行成功",
                    data={
                        "batch_id": batch_id,
                        "etl_saved_count": persistence_result["saved_count"],
                        "etl_failed_count": persistence_result["failed_count"],
                        "report_result": report_result,
                    },
                    execution_time_seconds=execution_time,
                    artifacts=report_result.get("artifacts", {})
                )

            except Exception as e:
                # 🔑 统一回滚
                db.rollback()
                await self._update_task_status(task_id, TaskStatus.FAILED, f"任务失败: {str(e)}", 0.0)
                logger.error(f"❌ 任务执行失败，已回滚: {task_id}, {e}")
                logger.exception(e)

                # 清理任务状态
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]

                execution_time = (datetime.now() - start_time).total_seconds()

                return TaskExecutionResult(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    success=False,
                    message="任务执行失败",
                    error=str(e),
                    execution_time_seconds=execution_time,
                    data={"batch_id": batch_id}
                )

    async def execute_task_complete(self, request: TaskExecutionRequest) -> TaskExecutionResult:
        """
        完整的任务执行（不使用Agent流水线，保留完整流程）

        与execute_task的区别：
        - execute_task: 使用新的Agent流水线（_execute_with_agents）
        - execute_task_complete: 保留完整的旧流程
        - execute_with_persistence: 新流程 + ETL持久化
        """
        start_time = datetime.now()
        task_id = request.task_id

        logger.info(f"开始执行任务（完整流程）: {task_id}")

        # 初始化任务状态
        self.active_tasks[task_id] = {
            "status": TaskStatus.PENDING,
            "start_time": start_time,
            "current_step": "初始化",
            "progress": 0.0
        }


    async def _execute_with_agents(self, request: TaskExecutionRequest, start_time: datetime) -> TaskExecutionResult:
        """使用 PlaceholderProcessingSystem 的 ReAct 流水线执行任务（新架构）"""
        task_id = request.task_id
        try:
            # 时间窗口 - 使用简化的时间上下文
            if request.time_context and request.time_context.get("data_start_time") and request.time_context.get("data_end_time"):
                # 使用请求中的时间上下文
                period_start_date = request.time_context.get("data_start_time")
                period_end_date = request.time_context.get("data_end_time")
            else:
                # 生成新的时间上下文
                schedule = request.execution_context.get("schedule") if request.execution_context else None
                if schedule:
                    time_ctx = self.time_context_manager.build_task_time_context(cron_expression=schedule)
                    period_start_date = time_ctx.get("data_start_time")
                    period_end_date = time_ctx.get("data_end_time")
                else:
                    # 默认使用昨天
                    yesterday = datetime.now() - timedelta(days=1)
                    period_start_date = yesterday.strftime('%Y-%m-%d')
                    period_end_date = yesterday.strftime('%Y-%m-%d')

            time_window = {"start": f"{period_start_date} 00:00:00", "end": f"{period_end_date} 23:59:59"}

            # 更新状态
            await self._update_task_status(task_id, TaskStatus.PROCESSING, "Agents流水线执行", 50.0)

            from app.services.application.placeholder import PlaceholderApplicationService as PlaceholderProcessingSystem
            system = PlaceholderProcessingSystem(user_id=request.user_id)
            await system.initialize()

            success_criteria = {
                "min_rows": 1,
                "max_rows": 100000,
                "required_fields": request.execution_context.get("required_fields", []) if request.execution_context else [],
                "quality_threshold": request.execution_context.get("quality_threshold", 0.6) if request.execution_context else 0.6,
            }
            objective = request.execution_context.get("objective") if request.execution_context else f"任务[{task_id}]数据准备与分析"

            events: List[Dict[str, Any]] = []
            async for ev in system.run_task_with_agent(
                task_objective=objective,
                success_criteria=success_criteria,
                data_source_id=(request.data_source_ids[0] if request.data_source_ids else None),
                time_window=time_window,
                time_column=request.execution_context.get("time_column") if request.execution_context else None,
                max_attempts=request.execution_context.get("max_attempts", 3) if request.execution_context else 3,
            ):
                events.append(ev)

            final = next((e for e in reversed(events) if e.get("type") == "agent_session_complete"), None)
            success = bool(final and final.get("success"))

            await self._update_task_status(task_id, TaskStatus.COMPLETED if success else TaskStatus.FAILED, "完成", 100.0)
            duration = (datetime.now() - start_time).total_seconds()

            # 清理任务状态
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

            return TaskExecutionResult(
                task_id=task_id,
                status=TaskStatus.COMPLETED if success else TaskStatus.FAILED,
                success=success,
                message="任务执行成功" if success else "任务执行失败",
                data={"events": events, "final": final, "time_window": time_window},
                execution_time_seconds=duration,
            )
        except Exception as e:
            logger.error(f"Agents流水线执行异常: {e}")
            duration = (datetime.now() - start_time).total_seconds()
            return TaskExecutionResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                success=False,
                message="任务执行异常",
                error=str(e),
                execution_time_seconds=duration,
            )
    
    async def _validate_and_repair_placeholders(
        self, 
        request: TaskExecutionRequest
    ) -> Dict[str, Any]:
        """验证和修复占位符"""
        # 旧流程已迁移，由 Agents 流水线在执行阶段处理
        return {"success": True, "data": {}, "message": "migrated_to_agents"}
    
    async def _execute_etl_pipeline(
        self,
        request: TaskExecutionRequest,
        placeholder_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行ETL数据处理"""
        try:
            from app.services.data.processing.etl.etl_service import ETLService

            etl_service = ETLService(user_id=self.user_id)

            # 检查是否有模板化SQL映射
            placeholder_sql_map = placeholder_data.get("placeholder_sql_map")

            if placeholder_sql_map:
                # 使用模板化方法进行数据提取
                logger.info("使用模板化SQL执行ETL流水线")

                etl_results = {}
                for data_source_id in request.data_source_ids:
                    # 确定执行模式
                    execution_mode = request.execution_context.get("execution_mode", "production")
                    if request.execution_context.get("mode") == "validation_only":
                        execution_mode = "test"

                    # 构建时间上下文
                    time_context = {
                        "cron_expression": request.execution_context.get("cron_expression", "0 8 * * *"),
                        "execution_time": request.time_context.get("execution_time"),
                        "test_date": request.time_context.get("test_date"),
                        "additional_params": request.execution_context.get("additional_params", {})
                    }

                    # 使用模板化提取
                    extract_result = await etl_service.extract_data_with_templates(
                        data_source_id=data_source_id,
                        placeholder_sql_map=placeholder_sql_map,
                        time_context=time_context,
                        execution_mode=execution_mode
                    )

                    if extract_result.get("success"):
                        # 数据转换（如果需要）
                        transform_config = request.execution_context.get("transform_config", {})
                        if transform_config:
                            # 为每个成功提取的占位符应用转换
                            transformed_extractions = []
                            for extraction in extract_result["data"]["successful_extractions"]:
                                transform_result = await etl_service.transform_data(
                                    raw_data=extraction["data"],
                                    transformation_config=transform_config
                                )
                                extraction["transform_result"] = transform_result
                                transformed_extractions.append(extraction)
                            extract_result["data"]["successful_extractions"] = transformed_extractions

                        etl_results[data_source_id] = {
                            "extract": extract_result,
                            "method": "template_based"
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"模板化数据提取失败: {extract_result.get('error', '未知错误')}",
                            "data": None
                        }

                return {
                    "success": True,
                    "data": etl_results,
                    "method": "template_based",
                    "message": f"成功处理 {len(etl_results)} 个数据源的模板化数据"
                }
            else:
                # 回退到传统方法
                logger.info("使用传统方法执行ETL流水线")

                etl_results = {}
                for data_source_id in request.data_source_ids:
                    # 构建查询配置
                    query_config = {
                        "template_id": request.template_id,
                        "placeholder_data": placeholder_data,
                        "time_context": request.time_context,
                        "execution_context": request.execution_context
                    }

                    # 执行数据提取
                    extract_result = await etl_service.extract_data(
                        data_source_id=data_source_id,
                        query_config=query_config
                    )

                    if extract_result.get("success"):
                        # 数据转换
                        transform_result = await etl_service.transform_data(
                            raw_data=extract_result["data"],
                            transformation_config=request.execution_context.get("transform_config", {})
                        )

                        etl_results[data_source_id] = {
                            "extract": extract_result,
                            "transform": transform_result,
                            "method": "traditional"
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"数据提取失败: {extract_result.get('error', '未知错误')}",
                            "data": None
                        }

                return {
                    "success": True,
                    "data": etl_results,
                    "method": "traditional",
                    "message": f"成功处理 {len(etl_results)} 个数据源的数据"
                }

        except Exception as e:
            logger.error(f"ETL处理异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    async def _generate_charts(
        self, 
        request: TaskExecutionRequest,
        etl_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用TT递归生成图表（第二阶段）"""
        try:
            from app.services.infrastructure.agents import execute_chart_generation_tt
            
            # 1. 分析模板中的图表占位符
            chart_placeholders = await self._analyze_chart_placeholders(request.template_id)
            
            if not chart_placeholders:
                return {
                    "success": True,
                    "data": {"charts_generated": 0, "message": "未找到图表占位符"},
                    "message": "未找到图表占位符，跳过图表生成"
                }
            
            # 2. 使用TT递归为数据生成图表
            chart_results = []
            for placeholder in chart_placeholders:
                try:
                    chart_result = await execute_chart_generation_tt(
                        chart_placeholder=placeholder.get('description', ''),
                        etl_data=etl_data,
                        user_id=self.user_id,
                        context={
                            "template_id": request.template_id,
                            "placeholder_id": placeholder.get('id'),
                            "chart_type": placeholder.get('chart_type', 'auto'),
                            "etl_data_summary": self._summarize_etl_data(etl_data)
                        }
                    )
                    
                    chart_results.append({
                        "success": True,
                        "placeholder_id": placeholder.get('id'),
                        "chart_content": chart_result,
                        "generation_method": "tt_recursion"
                    })
                    
                except Exception as e:
                    logger.error(f"TT递归图表生成失败 - 占位符: {placeholder.get('id')}, 错误: {e}")
                    chart_results.append({
                        "success": False,
                        "placeholder_id": placeholder.get('id'),
                        "error": str(e),
                        "generation_method": "tt_recursion"
                    })
            
            # 3. 整理结果
            successful_charts = [r for r in chart_results if r.success]
            failed_charts = [r for r in chart_results if not r.success]
            
            chart_data = {
                "charts_generated": len(successful_charts),
                "failed_charts": len(failed_charts),
                "chart_results": chart_results,
                "chart_placeholders": chart_placeholders,
                "generation_method": "tt_recursion"
            }
            
            return {
                "success": True,
                "data": chart_data,
                "message": f"TT递归图表生成完成: 成功{len(successful_charts)}个, 失败{len(failed_charts)}个"
            }
            
        except Exception as e:
            logger.error(f"TT递归图表生成异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    async def _analyze_chart_placeholders(self, template_id: str) -> List[Dict[str, Any]]:
        """分析模板中的图表占位符"""
        try:
            with get_db_session() as db:
                from app.models.template import Template
                from uuid import UUID
                
                template = db.query(Template).filter(Template.id == UUID(template_id)).first()
                if not template:
                    return []
                
                # 简单的图表占位符分析（可以根据需要扩展）
                import re
                chart_patterns = [
                    r'\{chart:([^}]+)\}',
                    r'\{图表:([^}]+)\}',
                    r'\{chart_([^}]+)\}'
                ]
                
                placeholders = []
                for pattern in chart_patterns:
                    matches = re.findall(pattern, template.content or '')
                    for match in matches:
                        placeholders.append({
                            "id": f"chart_{len(placeholders)}",
                            "description": match,
                            "chart_type": "auto"
                        })
                
                return placeholders
                
        except Exception as e:
            logger.error(f"分析图表占位符失败: {e}")
            return []
    
    def _summarize_etl_data(self, etl_data: Dict[str, Any]) -> str:
        """总结ETL数据"""
        try:
            if not etl_data or not etl_data.get('data'):
                return "无数据"
            
            data = etl_data['data']
            if isinstance(data, list):
                return f"数据行数: {len(data)}, 列数: {len(data[0]) if data else 0}"
            elif isinstance(data, dict):
                return f"数据字段: {list(data.keys())}"
            else:
                return f"数据类型: {type(data)}"
                
        except Exception as e:
            return f"数据总结失败: {e}"
    
    async def _export_document(
        self, 
        request: TaskExecutionRequest,
        processed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """导出文档"""
        try:
            from app.services.infrastructure.document.word_export_service import (
                create_word_export_service, DocumentConfig, DocumentFormat
            )
            
            word_service = create_word_export_service(self.user_id)
            
            # 创建文档配置
            output_format = DocumentFormat.DOCX
            if request.output_format.lower() == "pdf":
                output_format = DocumentFormat.PDF
            elif request.output_format.lower() == "html":
                output_format = DocumentFormat.HTML
                
            doc_config = DocumentConfig(
                template_id=request.template_id,
                output_format=output_format,
                font_name="宋体",
                font_size=12,
                line_spacing=1.5
            )
            
            # 导出文档
            export_result = await word_service.export_report_document(
                template_id=request.template_id,
                placeholder_data=processed_data.get("placeholder_data", {}),
                etl_data=processed_data.get("etl_data", {}),
                chart_data=processed_data.get("chart_data", {}),
                config=doc_config
            )
            
            if export_result.success:
                export_data = {
                    "document_path": export_result.document_path,
                    "format": request.output_format,
                    "size_bytes": export_result.file_size_bytes,
                    "page_count": export_result.page_count,
                    "export_time_seconds": export_result.export_time_seconds,
                    "artifacts": {
                        "main_document": export_result.document_path,
                        "charts": processed_data.get("chart_data", {}).get("chart_files", [])
                    },
                    "metadata": export_result.metadata
                }
                
                return {
                    "success": True,
                    "data": export_data,
                    "message": f"成功导出文档: {export_result.document_path}"
                }
            else:
                return {
                    "success": False,
                    "error": export_result.error,
                    "data": None
                }
            
        except Exception as e:
            logger.error(f"文档导出异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    async def _deliver_report(
        self, 
        request: TaskExecutionRequest,
        export_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """投递报告（存储和发送邮件）"""
        try:
            from app.services.infrastructure.delivery.delivery_service import (
                create_delivery_service, DeliveryRequest, DeliveryMethod,
                StorageConfig, EmailConfig, NotificationConfig
            )
            
            delivery_service = create_delivery_service(self.user_id)
            
            # 准备文件列表
            files_to_deliver = []
            
            # 主文档
            if export_data.get("document_path"):
                files_to_deliver.append(export_data["document_path"])
            
            # 图表文件
            chart_files = export_data.get("artifacts", {}).get("charts", [])
            files_to_deliver.extend(chart_files)
            
            if not files_to_deliver:
                return {
                    "success": False,
                    "error": "没有文件可投递",
                    "data": None
                }
            
            # 构建投递配置
            delivery_config = request.delivery_config or {}
            
            # 存储配置
            storage_config = StorageConfig(
                bucket_name="reports",
                path_prefix=f"reports/{request.user_id}/",
                public_access=False,
                retention_days=90
            )
            
            # 邮件配置
            email_config = None
            if delivery_config.get("send_email", False):
                recipients = delivery_config.get("email_recipients", [])
                if recipients:
                    email_config = EmailConfig(
                        recipients=recipients,
                        subject=f"报告生成完成 - {request.template_id}",
                        body=delivery_config.get("email_body", ""),
                        attach_files=delivery_config.get("attach_files", True),
                        cc_recipients=delivery_config.get("cc_recipients"),
                        bcc_recipients=delivery_config.get("bcc_recipients")
                    )
            
            # 通知配置
            notification_config = NotificationConfig(
                channels=["system", "web"],
                message=f"报告生成完成：{request.template_id}",
                priority="normal"
            )
            
            # 确定投递方式
            delivery_method = DeliveryMethod.STORAGE_AND_EMAIL
            if email_config is None:
                delivery_method = DeliveryMethod.STORAGE_ONLY
            
            # 创建投递请求
            delivery_request = DeliveryRequest(
                task_id=request.task_id,
                user_id=request.user_id,
                files=files_to_deliver,
                delivery_method=delivery_method,
                storage_config=storage_config,
                email_config=email_config,
                notification_config=notification_config,
                metadata={
                    "template_id": request.template_id,
                    "execution_context": request.execution_context,
                    "export_metadata": export_data.get("metadata", {})
                }
            )
            
            # 执行投递
            delivery_result = await delivery_service.deliver_report(delivery_request)
            
            if delivery_result.success:
                return {
                    "success": True,
                    "data": {
                        "delivery_id": delivery_result.delivery_id,
                        "status": delivery_result.status.value,
                        "storage_result": delivery_result.storage_result,
                        "email_result": delivery_result.email_result,
                        "notification_result": delivery_result.notification_result,
                        "download_urls": delivery_result.download_urls,
                        "delivery_time_seconds": delivery_result.delivery_time_seconds
                    },
                    "message": delivery_result.message
                }
            else:
                return {
                    "success": False,
                    "error": delivery_result.error,
                    "data": {
                        "delivery_id": delivery_result.delivery_id,
                        "status": delivery_result.status.value
                    }
                }
            
        except Exception as e:
            logger.error(f"报告投递异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    async def _get_data_source_info(self, data_source_id: str) -> Dict[str, Any]:
        """获取数据源信息"""
        try:
            from app.crud import data_source as crud_data_source
            from app.db.session import SessionLocal
            
            db = SessionLocal()
            try:
                data_source = crud_data_source.get(db, id=data_source_id)
                if not data_source:
                    raise ValueError(f"数据源不存在: {data_source_id}")
                
                return {
                    "type": data_source.source_type.value if hasattr(data_source.source_type, 'value') else str(data_source.source_type),
                    "name": data_source.name,
                    "database": getattr(data_source, 'doris_database', 'unknown'),
                    "fe_hosts": getattr(data_source, 'doris_fe_hosts', ['localhost']),
                    "username": getattr(data_source, 'doris_username', 'root'),
                    "password": getattr(data_source, 'doris_password', ''),
                    "query_port": getattr(data_source, 'doris_query_port', 9030)
                }
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取数据源信息失败: {e}")
            return {"type": "unknown", "name": "unknown"}
    
    async def _update_task_status(
        self, 
        task_id: str, 
        status: TaskStatus, 
        step: str, 
        progress: float
    ):
        """更新任务状态"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].update({
                "status": status,
                "current_step": step,
                "progress": progress,
                "updated_at": datetime.now()
            })
        logger.debug(f"任务状态更新: {task_id} -> {status.value} ({progress}%): {step}")
    
    def _create_error_result(
        self, 
        request: TaskExecutionRequest, 
        message: str, 
        error: str
    ) -> TaskExecutionResult:
        """创建错误结果"""
        task_id = request.task_id
        
        # 更新任务状态为失败
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["status"] = TaskStatus.FAILED
            
        logger.error(f"任务执行失败: {task_id}, 错误: {error}")
        
        return TaskExecutionResult(
            task_id=task_id,
            status=TaskStatus.FAILED,
            success=False,
            message=message,
            error=error
        )
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return self.active_tasks.get(task_id)
    
    def list_active_tasks(self) -> List[Dict[str, Any]]:
        """列出活跃任务"""
        return [
            {
                "task_id": task_id,
                **task_info
            }
            for task_id, task_info in self.active_tasks.items()
        ]
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["status"] = TaskStatus.CANCELLED
            logger.info(f"任务已取消: {task_id}")
            return True
        return False

    def replace_sql_placeholders_in_task(self, sql: str, time_context: Dict[str, Any]) -> str:
        """
        在任务执行中替换SQL占位符

        Args:
            sql: 包含占位符的SQL (如: "WHERE dt BETWEEN {{start_date}} AND {{end_date}}")
            time_context: 时间上下文

        Returns:
            替换后的SQL (如: "WHERE dt BETWEEN '2025-09-27' AND '2025-09-27'")
        """
        try:
            replaced_sql = self.sql_replacer.replace_time_placeholders(sql, time_context)
            logger.info(f"SQL占位符替换完成，原SQL包含 {len(self.sql_replacer.extract_placeholders(sql))} 个占位符")
            return replaced_sql
        except Exception as e:
            logger.error(f"SQL占位符替换失败: {e}")
            return sql

    def generate_time_context_for_task(
        self,
        execution_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        为任务生成时间上下文 - 使用简化的占位符替换逻辑

        Args:
            execution_params: 任务执行参数，包含schedule (cron表达式)

        Returns:
            时间上下文字典，包含data_start_time和data_end_time用于占位符替换
        """
        try:
            schedule = execution_params.get("schedule")
            execution_time = None

            # 尝试解析执行时间
            if "execution_time" in execution_params:
                exec_time_str = execution_params["execution_time"]
                if isinstance(exec_time_str, str):
                    try:
                        execution_time = datetime.fromisoformat(exec_time_str.replace('Z', '+00:00'))
                    except ValueError:
                        logger.warning(f"Invalid execution_time format: {exec_time_str}")

            # 使用简化的时间上下文生成 - 直接基于cron和执行时间
            if schedule:
                time_context = self.time_context_manager.build_task_time_context(
                    cron_expression=schedule,
                    execution_time=execution_time
                )
                logger.info(f"Generated simplified time context for cron: {schedule}")
            else:
                # 回退到默认的每日上下文
                logger.warning("No schedule provided, using default daily context")
                time_context = self.time_context_manager.build_task_time_context(
                    cron_expression="0 0 * * *",  # 默认每日
                    execution_time=execution_time
                )

            return time_context

        except Exception as e:
            logger.error(f"Failed to generate time context: {e}")
            # 返回基础的时间上下文
            yesterday = datetime.now() - timedelta(days=1)
            return {
                "execution_time": datetime.now().isoformat(),
                "data_start_time": yesterday.strftime('%Y-%m-%d'),
                "data_end_time": yesterday.strftime('%Y-%m-%d'),
                "period": "daily",
                "fallback": True
            }
    
    def execute_complete_task_flow(
        self,
        execution_params: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        执行完整任务流程 - 新的入口方法
        
        Args:
            execution_params: 执行参数
            progress_callback: 进度回调函数
            
        Returns:
            执行结果
        """
        try:
            # 1. 生成时间上下文
            time_context = self.generate_time_context_for_task(execution_params)
            
            # 2. 构建TaskExecutionRequest
            request = TaskExecutionRequest(
                task_id=execution_params["task_id"],
                template_id=execution_params["template_id"],
                data_source_ids=[execution_params["data_source_id"]],
                user_id=execution_params["user_id"],
                execution_context=execution_params.get("execution_context", {}),
                time_context=time_context,
                output_format="docx",
                delivery_config={
                    "send_email": bool(execution_params.get("recipients")),
                    "email_recipients": execution_params.get("recipients", []),
                    "storage_path": f"reports/{execution_params['task_id']}"
                }
            )
            
            # 3. 运行异步执行（这需要在异步上下文中运行）
            import asyncio
            
            # 创建事件循环或使用现有的
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # 如果有进度回调，设置为任务状态更新回调
            if progress_callback:
                original_update = self._update_task_status
                async def wrapped_update(task_id, status, message, progress):
                    result = await original_update(task_id, status, message, progress)
                    progress_callback(int(progress), message, status.value if hasattr(status, 'value') else str(status))
                    return result
                self._update_task_status = wrapped_update
            
            # 执行任务
            if loop.is_running():
                # 如果循环已在运行，创建任务
                future = asyncio.create_task(self.execute_task(request))
                # 注意：在实际环境中，这需要特殊处理
                logger.warning("Event loop is running, task execution may need adjustment")
                result = {"success": False, "error": "Event loop running - task queued"}
            else:
                result = loop.run_until_complete(self.execute_task(request))
            
            # 转换结果格式
            if hasattr(result, 'success'):
                return {
                    "success": result.success,
                    "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
                    "message": result.message,
                    "data": result.data,
                    "artifacts": result.artifacts,
                    "execution_time": result.execution_time_seconds,
                    "error": result.error
                }
            else:
                return result
            
        except Exception as e:
            logger.error(f"Complete task flow execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "failed"
            }
    
    async def validate_all_placeholders(
        self,
        template_id: str,
        data_source_id: str,
        user_id: str,
        report_period: str = "monthly"
    ) -> Dict[str, Any]:
        """
        验证所有占位符 - 供外部调用
        
        Args:
            template_id: 模板ID
            data_source_id: 数据源ID  
            user_id: 用户ID
            report_period: 报告周期
            
        Returns:
            验证结果
        """
        try:
            # 生成时间上下文
            time_context = self.time_context_manager.generate_time_context(report_period)
            
            # 构建请求
            request = TaskExecutionRequest(
                task_id=f"validation_{datetime.now().timestamp()}",
                template_id=template_id,
                data_source_ids=[data_source_id],
                user_id=user_id,
                execution_context={"mode": "validation_only"},
                time_context=time_context
            )
            
            # 仅执行验证步骤
            validation_result = await self._validate_and_repair_placeholders(request)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Placeholder validation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# 工厂函数
def create_task_execution_service(user_id: str) -> TaskExecutionService:
    """创建任务执行服务实例"""
    return TaskExecutionService(user_id=user_id)
