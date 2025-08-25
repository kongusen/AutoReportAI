"""
Two-Phase Report Generation Pipeline

基于Template → Placeholder → Agent → ETL架构的两阶段报告生成流水线

阶段1: 模板分析和占位符处理 (Template → Placeholder → Agent分析)
阶段2: 数据提取和报告生成 (ETL → Report)
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from uuid import uuid4
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app import crud, schemas
from app.models.template import Template
from app.models.data_source import DataSource
from app.models.task import Task
from app.crud.crud_task import crud_task
from app.services.domain.template.enhanced_template_parser import EnhancedTemplateParser
# Import the real CachedAgentOrchestrator
from app.services.application.orchestration.cached_agent_orchestrator import CachedAgentOrchestrator
from app.services.domain.reporting.word_generator_service import WordGeneratorService
from app.services.infrastructure.notification.notification_service import NotificationService
from ..core.progress_manager import update_task_progress_dict

logger = logging.getLogger(__name__)


class PipelinePhase(Enum):
    """流水线阶段"""
    PHASE_1_ANALYSIS = "phase_1_analysis"     # 阶段1: 模板分析和Agent处理
    PHASE_2_EXECUTION = "phase_2_execution"   # 阶段2: 数据提取和报告生成
    COMPLETE = "complete"                     # 完成


class ExecutionMode(Enum):
    """执行模式"""
    FULL_PIPELINE = "full_pipeline"           # 完整两阶段流水线
    PHASE_1_ONLY = "phase_1_only"            # 仅执行阶段1
    PHASE_2_ONLY = "phase_2_only"            # 仅执行阶段2(基于已有分析)
    SMART_EXECUTION = "smart_execution"      # 智能执行(根据状态决定)


@dataclass
class PipelineConfiguration:
    """流水线配置"""
    execution_mode: ExecutionMode = ExecutionMode.SMART_EXECUTION
    force_reanalyze: bool = False
    enable_caching: bool = True
    cache_ttl_hours: int = 24
    optimization_level: str = "standard"
    batch_size: int = 1000
    timeout_seconds: int = 600
    enable_progress_tracking: bool = True
    enable_notifications: bool = True
    custom_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PhaseResult:
    """阶段执行结果"""
    phase: PipelinePhase
    success: bool
    execution_time: float
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """完整流水线结果"""
    pipeline_id: str
    success: bool
    total_execution_time: float
    phase_results: Dict[PipelinePhase, PhaseResult] = field(default_factory=dict)
    final_output: Optional[Dict[str, Any]] = None
    report_path: Optional[str] = None
    cache_statistics: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class TwoPhasePipeline:
    """两阶段报告生成流水线"""
    
    def __init__(self, config: PipelineConfiguration = None):
        self.config = config or PipelineConfiguration()
        self.pipeline_id = str(uuid4())
        
    async def execute(
        self,
        task_id: int,
        user_id: str,
        template_id: Optional[str] = None,
        data_source_id: Optional[str] = None,
        db: Optional[Session] = None,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> PipelineResult:
        """
        执行两阶段流水线
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            template_id: 模板ID (可选，从任务中获取)
            data_source_id: 数据源ID (可选，从任务中获取)
            db: 数据库会话 (可选，自动创建)
        """
        start_time = time.time()
        should_close_db = False
        
        if db is None:
            db = SessionLocal()
            should_close_db = True
            
        try:
            logger.info(f"开始两阶段流水线执行 - Pipeline ID: {self.pipeline_id}, Task ID: {task_id}")
            
            # 设置初始进度状态
            if self.config.enable_progress_tracking:
                self._update_progress(task_id, user_id, "processing", 0, "开始两阶段流水线执行")
            
            # 1. 初始化和验证
            initialization_result = await self._initialize_pipeline(
                task_id, user_id, template_id, data_source_id, db, execution_context
            )
            
            if not initialization_result["success"]:
                return PipelineResult(
                    pipeline_id=self.pipeline_id,
                    success=False,
                    total_execution_time=time.time() - start_time,
                    error=initialization_result["error"]
                )
            
            context = initialization_result["context"]
            
            # 2. 根据执行模式选择流程
            if self.config.execution_mode == ExecutionMode.SMART_EXECUTION:
                execution_mode = await self._determine_smart_execution_mode(context, db)
            else:
                execution_mode = self.config.execution_mode
            
            logger.info(f"使用执行模式: {execution_mode.value}")
            
            # 3. 执行流水线阶段
            phase_results = {}
            
            if execution_mode in [ExecutionMode.FULL_PIPELINE, ExecutionMode.PHASE_1_ONLY]:
                # 执行阶段1: 模板分析和Agent处理
                phase1_result = await self._execute_phase_1(context, db)
                phase_results[PipelinePhase.PHASE_1_ANALYSIS] = phase1_result
                
                if not phase1_result.success and execution_mode == ExecutionMode.FULL_PIPELINE:
                    total_time = time.time() - start_time
                    # 更新任务执行统计 - 失败（阶段1失败）
                    try:
                        crud_task.update_execution_stats(
                            db=db,
                            task_id=task_id,
                            success=False,
                            execution_time=total_time
                        )
                        logger.info(f"阶段1失败统计更新成功 - 任务ID: {task_id}")
                    except Exception as stats_error:
                        logger.error(f"更新阶段1失败统计失败: {stats_error}")
                    
                    return PipelineResult(
                        pipeline_id=self.pipeline_id,
                        success=False,
                        total_execution_time=total_time,
                        phase_results=phase_results,
                        error=f"阶段1执行失败: {phase1_result.error}"
                    )
            
            if execution_mode in [ExecutionMode.FULL_PIPELINE, ExecutionMode.PHASE_2_ONLY]:
                # 执行阶段2: 数据提取和报告生成
                phase2_result = await self._execute_phase_2(context, db)
                phase_results[PipelinePhase.PHASE_2_EXECUTION] = phase2_result
                
                if not phase2_result.success:
                    total_time = time.time() - start_time
                    # 更新任务执行统计 - 失败（阶段2失败）
                    try:
                        crud_task.update_execution_stats(
                            db=db,
                            task_id=task_id,
                            success=False,
                            execution_time=total_time
                        )
                        logger.info(f"阶段2失败统计更新成功 - 任务ID: {task_id}")
                    except Exception as stats_error:
                        logger.error(f"更新阶段2失败统计失败: {stats_error}")
                    
                    return PipelineResult(
                        pipeline_id=self.pipeline_id,
                        success=False,
                        total_execution_time=total_time,
                        phase_results=phase_results,
                        error=f"阶段2执行失败: {phase2_result.error}"
                    )
            
            # 4. 生成最终结果
            final_result = await self._finalize_pipeline(context, phase_results, db)
            
            total_time = time.time() - start_time
            logger.info(f"两阶段流水线执行完成 - Pipeline ID: {self.pipeline_id}, 总耗时: {total_time:.2f}秒")
            
            # 更新任务执行统计 - 成功
            try:
                crud_task.update_execution_stats(
                    db=db,
                    task_id=task_id,
                    success=True,
                    execution_time=total_time
                )
                logger.info(f"任务统计更新成功 - 任务ID: {task_id}, 执行时间: {total_time:.2f}秒")
            except Exception as stats_error:
                logger.error(f"更新任务统计失败: {stats_error}")
            
            return PipelineResult(
                pipeline_id=self.pipeline_id,
                success=True,
                total_execution_time=total_time,
                phase_results=phase_results,
                final_output=final_result["data"],
                report_path=final_result.get("report_path"),
                cache_statistics=final_result.get("cache_statistics", {}),
                performance_metrics=self._calculate_performance_metrics(phase_results, total_time)
            )
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"两阶段流水线执行失败 - Pipeline ID: {self.pipeline_id}: {e}")
            
            # 更新失败状态
            if self.config.enable_progress_tracking:
                self._update_progress(task_id, user_id, "failed", 0, f"流水线执行失败: {str(e)}")
            
            # 更新任务执行统计 - 失败
            try:
                crud_task.update_execution_stats(
                    db=db,
                    task_id=task_id,
                    success=False,
                    execution_time=total_time
                )
                logger.info(f"任务失败统计更新成功 - 任务ID: {task_id}, 执行时间: {total_time:.2f}秒")
            except Exception as stats_error:
                logger.error(f"更新任务失败统计失败: {stats_error}")
            
            # 创建失败的报告记录
            try:
                report_data = {
                    "task_id": task_id,
                    "user_id": user_id,
                    "file_path": None,  # 失败时没有文件
                    "status": "failed",
                    "result": f"流水线执行失败: {str(e)}"
                }
                
                crud.report_history.create(
                    db=db,
                    obj_in=schemas.ReportHistoryCreate(**report_data)
                )
                logger.info(f"已创建失败报告记录 - 任务ID: {task_id}")
            except Exception as record_error:
                logger.warning(f"创建失败报告记录失败: {record_error}")
            
            return PipelineResult(
                pipeline_id=self.pipeline_id,
                success=False,
                total_execution_time=total_time,
                error=str(e)
            )
            
        finally:
            if should_close_db:
                db.close()
    
    async def _initialize_pipeline(
        self,
        task_id: int,
        user_id: str,
        template_id: Optional[str],
        data_source_id: Optional[str],
        db: Session,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """初始化流水线"""
        try:
            if self.config.enable_progress_tracking:
                self._update_progress(task_id, user_id, "initializing", 5, "初始化两阶段流水线")
            
            # 获取任务信息
            task = crud.task.get(db, id=task_id)
            if not task:
                return {"success": False, "error": f"任务不存在: {task_id}"}
            
            # 获取模板和数据源ID
            final_template_id = template_id or str(task.template_id)
            final_data_source_id = data_source_id or str(task.data_source_id)
            
            # 验证模板和数据源
            template = crud.template.get(db, id=final_template_id)
            data_source = crud.data_source.get(db, id=final_data_source_id)
            
            if not template:
                return {"success": False, "error": f"模板不存在: {final_template_id}"}
            if not data_source:
                return {"success": False, "error": f"数据源不存在: {final_data_source_id}"}
            
            # 处理执行时间上下文
            processed_execution_context = self._process_execution_context(execution_context)
            
            context = {
                "task_id": task_id,
                "user_id": user_id,
                "template_id": final_template_id,
                "data_source_id": final_data_source_id,
                "task": task,
                "template": template,
                "data_source": data_source,
                "pipeline_config": self.config,
                "execution_context": processed_execution_context
            }
            
            logger.info(f"流水线初始化完成 - Template: {final_template_id}, DataSource: {final_data_source_id}")
            return {"success": True, "context": context}
            
        except Exception as e:
            logger.error(f"流水线初始化失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _process_execution_context(self, execution_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """处理和计算执行时间上下文"""
        if not execution_context:
            # 默认使用当前时间和月度周期
            from datetime import datetime
            now = datetime.now()
            execution_context = {
                "execution_time": now.isoformat(),
                "report_period": "monthly"
            }
        
        try:
            # 解析执行时间
            from datetime import datetime
            execution_time = datetime.fromisoformat(execution_context["execution_time"].replace('Z', '+00:00'))
            report_period = execution_context.get("report_period", "monthly")
            
            # 计算报告时间范围
            period_start, period_end = self._calculate_period_range(execution_time, report_period)
            
            # 生成SQL参数映射
            sql_parameters = self._generate_sql_parameters(execution_time, period_start, period_end, report_period)
            
            processed_context = {
                "execution_time": execution_time.isoformat(),
                "report_period": report_period,
                "period_start": period_start.isoformat() if period_start else None,
                "period_end": period_end.isoformat() if period_end else None,
                "sql_parameters": sql_parameters
            }
            
            logger.info(f"执行时间上下文已处理 - 时间: {execution_time}, 周期: {report_period}, 范围: {period_start} ~ {period_end}")
            return processed_context
            
        except Exception as e:
            logger.warning(f"处理执行时间上下文失败，使用默认值: {e}")
            from datetime import datetime
            now = datetime.now()
            return {
                "execution_time": now.isoformat(),
                "report_period": "monthly",
                "period_start": None,
                "period_end": None,
                "sql_parameters": {}
            }
    
    def _calculate_period_range(self, execution_time: datetime, report_period: str) -> tuple:
        """计算报告周期的起始和结束时间"""
        import calendar
        
        if report_period == "daily":
            # 日报：当天
            period_start = execution_time.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1) - timedelta(microseconds=1)
            
        elif report_period == "weekly":
            # 周报：本周一到周日
            days_since_monday = execution_time.weekday()
            period_start = execution_time - timedelta(days=days_since_monday)
            period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=7) - timedelta(microseconds=1)
            
        elif report_period == "monthly":
            # 月报：本月1号到月末
            period_start = execution_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if execution_time.month == 12:
                next_month = execution_time.replace(year=execution_time.year + 1, month=1, day=1)
            else:
                next_month = execution_time.replace(month=execution_time.month + 1, day=1)
            period_end = next_month - timedelta(microseconds=1)
            
        elif report_period == "yearly":
            # 年报：本年1月1号到12月31号
            period_start = execution_time.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            period_end = execution_time.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
            
        else:
            # 默认月报
            period_start = execution_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if execution_time.month == 12:
                next_month = execution_time.replace(year=execution_time.year + 1, month=1, day=1)
            else:
                next_month = execution_time.replace(month=execution_time.month + 1, day=1)
            period_end = next_month - timedelta(microseconds=1)
        
        return period_start, period_end
    
    def _generate_sql_parameters(self, execution_time: datetime, period_start: datetime, 
                                period_end: datetime, report_period: str) -> Dict[str, str]:
        """生成SQL参数映射，用于动态替换占位符"""
        
        parameters = {
            # 基础时间参数
            "${REPORT_DATE}": execution_time.strftime("%Y-%m-%d"),
            "${REPORT_DATETIME}": execution_time.strftime("%Y-%m-%d %H:%M:%S"),
            "${REPORT_TIMESTAMP}": str(int(execution_time.timestamp())),
            
            # 周期范围参数
            "${START_DATE}": period_start.strftime("%Y-%m-%d") if period_start else execution_time.strftime("%Y-%m-%d"),
            "${END_DATE}": period_end.strftime("%Y-%m-%d") if period_end else execution_time.strftime("%Y-%m-%d"),
            "${START_DATETIME}": period_start.strftime("%Y-%m-%d %H:%M:%S") if period_start else execution_time.strftime("%Y-%m-%d %H:%M:%S"),
            "${END_DATETIME}": period_end.strftime("%Y-%m-%d %H:%M:%S") if period_end else execution_time.strftime("%Y-%m-%d %H:%M:%S"),
            
            # 周期类型参数
            "${REPORT_PERIOD}": report_period,
            "${YEAR}": execution_time.strftime("%Y"),
            "${MONTH}": execution_time.strftime("%m"),
            "${DAY}": execution_time.strftime("%d"),
            "${HOUR}": execution_time.strftime("%H"),
            
            # 相对时间参数
            "${YESTERDAY}": (execution_time - timedelta(days=1)).strftime("%Y-%m-%d"),
            "${LAST_WEEK_START}": (period_start - timedelta(days=7)).strftime("%Y-%m-%d") if period_start else (execution_time - timedelta(days=7)).strftime("%Y-%m-%d"),
            "${LAST_MONTH_START}": self._get_last_month_start(execution_time).strftime("%Y-%m-%d"),
        }
        
        return parameters
    
    def _get_last_month_start(self, current_date: datetime) -> datetime:
        """获取上月第一天"""
        if current_date.month == 1:
            return current_date.replace(year=current_date.year - 1, month=12, day=1)
        else:
            return current_date.replace(month=current_date.month - 1, day=1)
    
    async def _determine_smart_execution_mode(
        self,
        context: Dict[str, Any],
        db: Session
    ) -> ExecutionMode:
        """智能确定执行模式"""
        try:
            template_id = context["template_id"]
            
            # 使用EnhancedTemplateParser检查模板准备状态
            template_parser = EnhancedTemplateParser(db)
            readiness_check = await template_parser.check_template_ready_for_execution(template_id)
            
            if readiness_check["ready"] and not self.config.force_reanalyze:
                # 模板已分析且准备就绪，只需执行阶段2
                logger.info("模板已分析，使用阶段2执行模式")
                return ExecutionMode.PHASE_2_ONLY
            else:
                # 需要完整的两阶段执行
                logger.info("模板需要分析，使用完整流水线模式")
                return ExecutionMode.FULL_PIPELINE
                
        except Exception as e:
            logger.warning(f"智能模式判断失败，降级到完整流水线: {e}")
            return ExecutionMode.FULL_PIPELINE
    
    async def _execute_phase_1(
        self,
        context: Dict[str, Any],
        db: Session
    ) -> PhaseResult:
        """
        执行阶段1: 模板分析和占位符处理
        Template → EnhancedTemplateParser (持久化占位符) → CachedAgentOrchestrator (Agent分析 + SQL生成)
        """
        start_time = time.time()
        task_id = context["task_id"]
        user_id = context["user_id"]
        template_id = context["template_id"]
        data_source_id = context["data_source_id"]
        template = context["template"]
        
        try:
            if self.config.enable_progress_tracking:
                self._update_progress(task_id, user_id, "analyzing", 15, "阶段1: 模板分析和Agent处理")
            
            logger.info(f"开始阶段1执行 - Template: {template_id}")
            
            # 1. 增强模板解析和占位符持久化
            self._update_progress(task_id, user_id, "analyzing", 20, "解析模板占位符")
            
            template_parser = EnhancedTemplateParser(db)
            parse_result = await template_parser.parse_and_store_template_placeholders(
                template_id, template.content, self.config.force_reanalyze
            )
            
            if not parse_result["success"]:
                return PhaseResult(
                    phase=PipelinePhase.PHASE_1_ANALYSIS,
                    success=False,
                    execution_time=time.time() - start_time,
                    error=f"模板解析失败: {parse_result.get('error')}"
                )
            
            # 2. Agent分析和SQL生成
            if parse_result["requires_agent_analysis"] > 0:
                self._update_progress(task_id, user_id, "analyzing", 30, f"Agent分析 {parse_result['requires_agent_analysis']} 个占位符")
                
                cached_orchestrator = CachedAgentOrchestrator(db, user_id=user_id)
                # 从上下文中获取执行时间信息
                execution_context = context.get("execution_context")
                analysis_result = await cached_orchestrator._execute_phase1_analysis(
                    template_id, data_source_id, self.config.force_reanalyze, execution_context
                )
                
                if not analysis_result["success"]:
                    return PhaseResult(
                        phase=PipelinePhase.PHASE_1_ANALYSIS,
                        success=False,
                        execution_time=time.time() - start_time,
                        error=f"Agent分析失败: {analysis_result.get('error')}"
                    )
            else:
                analysis_result = {"success": True, "message": "无需Agent分析"}
            
            # 3. 验证分析结果
            self._update_progress(task_id, user_id, "analyzing", 40, "验证分析结果")
            
            final_readiness = await template_parser.check_template_ready_for_execution(template_id)
            
            execution_time = time.time() - start_time
            
            phase1_data = {
                "parse_result": parse_result,
                "analysis_result": analysis_result,
                "readiness_check": final_readiness,
                "template_ready": final_readiness["ready"]
            }
            
            logger.info(f"阶段1执行完成 - 耗时: {execution_time:.2f}秒, 模板就绪: {final_readiness['ready']}")
            
            return PhaseResult(
                phase=PipelinePhase.PHASE_1_ANALYSIS,
                success=True,
                execution_time=execution_time,
                data=phase1_data,
                metadata={
                    "total_placeholders": parse_result["total_placeholders"],
                    "analyzed_placeholders": analysis_result.get("analyzed_placeholders", 0),
                    "template_ready": final_readiness["ready"]
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"阶段1执行失败: {e}")
            
            # 更新失败状态
            if self.config.enable_progress_tracking:
                self._update_progress(task_id, user_id, "failed", 0, f"阶段1执行失败: {str(e)}")
            
            # 创建失败的报告记录
            try:
                report_data = {
                    "task_id": task_id,
                    "user_id": context["user_id"],
                    "file_path": None,  # 失败时没有文件
                    "status": "failed",
                    "result": f"模板分析失败: {str(e)}"
                }
                
                crud.report_history.create(
                    db=db,
                    obj_in=schemas.ReportHistoryCreate(**report_data)
                )
                logger.info(f"已创建失败报告记录 - 任务ID: {task_id}")
            except Exception as record_error:
                logger.warning(f"创建失败报告记录失败: {record_error}")
            
            return PhaseResult(
                phase=PipelinePhase.PHASE_1_ANALYSIS,
                success=False,
                execution_time=execution_time,
                error=str(e)
            )
    
    async def _execute_phase_2(
        self,
        context: Dict[str, Any],
        db: Session
    ) -> PhaseResult:
        """
        执行阶段2: 数据提取和报告生成
        数据提取 (优先使用缓存) → Report
        """
        start_time = time.time()
        task_id = context["task_id"]
        user_id = context["user_id"]
        template_id = context["template_id"]
        data_source_id = context["data_source_id"]
        task = context["task"]
        template = context["template"]
        
        try:
            if self.config.enable_progress_tracking:
                self._update_progress(task_id, user_id, "extracting", 50, "阶段2: 数据提取和报告生成")
            
            logger.info(f"开始阶段2执行 - Template: {template_id}")
            
            # 1. 缓存优先的数据提取
            self._update_progress(task_id, user_id, "extracting", 60, "提取占位符数据")
            
            # 使用独立的数据库会话创建编排器
            from app.db.session import get_db_session
            with get_db_session() as orchestrator_db:
                cached_orchestrator = CachedAgentOrchestrator(orchestrator_db, user_id=user_id)
                # 从上下文中获取执行时间信息
                execution_context = context.get("execution_context")
                extraction_result = await cached_orchestrator._execute_phase2_extraction_and_generation(
                    template_id, data_source_id, user_id, execution_context
                )
            
            if not extraction_result["success"]:
                return PhaseResult(
                    phase=PipelinePhase.PHASE_2_EXECUTION,
                    success=False,
                    execution_time=time.time() - start_time,
                    error=f"数据提取失败: {extraction_result.get('error')}"
                )
            
            # 2. 生成最终报告
            self._update_progress(task_id, user_id, "generating", 80, "生成Word文档")
            
            word_generator = WordGeneratorService()
            
            # 使用基于模板的生成方法
            try:
                # 获取占位符值字典
                placeholder_values = extraction_result.get("placeholder_values", {})
                
                # 获取模板类型和内容，确保格式一致性
                template_content = getattr(template, 'content', '') or ''
                template_type = getattr(template, 'template_type', 'docx')
                
                # 根据模板类型确定输出格式
                output_format = template_type if template_type in ['docx', 'xlsx', 'txt', 'html'] else 'docx'
                
                # 使用模板生成报告，保持格式一致
                report_path = word_generator.generate_report_from_template(
                    template_content=template_content,
                    placeholder_values=placeholder_values,
                    title=task.name,
                    format=output_format
                )
                logger.info(f"使用模板生成报告成功 (格式: {output_format}): {report_path}")
            except Exception as template_error:
                logger.warning(f"模板生成失败，降级到普通生成: {template_error}")
                # 降级到普通生成，但保持格式一致
                template_type = getattr(template, 'template_type', 'docx')
                output_format = template_type if template_type in ['docx', 'xlsx', 'txt', 'html'] else 'docx'
                
                report_path = word_generator.generate_report(
                    content=extraction_result.get("processed_content", "报告生成失败"),
                    title=task.name,
                    format=output_format
                )
                logger.info(f"降级生成报告完成 (格式: {output_format}): {report_path}")
            
            # 3. 保存报告记录
            self._update_progress(task_id, user_id, "finalizing", 90, "保存报告记录")
            
            execution_time = time.time() - start_time
            
            # 生成报告摘要而不是完整的模板内容
            placeholder_count = extraction_result.get("processed_placeholders", 0)
            total_placeholders = extraction_result.get("total_placeholders", 0)
            cache_hit_rate = extraction_result.get("cache_hit_rate", 0)
            
            report_summary = f"报告生成成功。处理了 {placeholder_count}/{total_placeholders} 个占位符，缓存命中率: {cache_hit_rate:.1f}%"
            
            report_data = {
                "task_id": task_id,
                "user_id": context["user_id"],
                "file_path": report_path,
                "status": "completed",
                "result": report_summary,
                "processing_metadata": {}  # 使用空字典而不是None
            }
            
            # 使用独立的数据库会话避免事务问题
            from app.db.session import get_db_session
            report_id = None
            try:
                with get_db_session() as new_db:
                    report_record = crud.report_history.create(
                        db=new_db,
                        obj_in=schemas.ReportHistoryCreate(**report_data)
                    )
                    new_db.commit()
                    report_id = report_record.id  # 在会话关闭前获取ID
                    logger.info(f"成功创建报告历史记录 - ID: {report_id}")
            except Exception as db_error:
                logger.error(f"创建报告历史记录失败: {db_error}")
                # 即使数据库操作失败，也不影响报告生成的成功
                report_id = None
            
            phase2_data = {
                "extraction_result": extraction_result,
                "report_path": report_path,
                "report_id": report_id,
                "processed_content": extraction_result.get("processed_content", "报告生成成功")
            }
            
            cache_stats = {
                "cache_hit_rate": extraction_result.get("cache_hit_rate", 0),
                "processed_placeholders": extraction_result.get("processed_placeholders", 0),
                "total_placeholders": extraction_result.get("total_placeholders", 0)
            }
            
            logger.info(f"阶段2执行完成 - 耗时: {execution_time:.2f}秒, 缓存命中率: {cache_stats['cache_hit_rate']:.1f}%")
            
            # 即使数据库操作失败，报告生成仍然是成功的
            success = True
            if report_id is None:
                logger.warning("报告历史记录保存失败，但报告生成成功")
            
            return PhaseResult(
                phase=PipelinePhase.PHASE_2_EXECUTION,
                success=success,
                execution_time=execution_time,
                data=phase2_data,
                metadata=cache_stats
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"阶段2执行失败: {e}")
            
            # 更新失败状态
            if self.config.enable_progress_tracking:
                self._update_progress(task_id, user_id, "failed", 0, f"阶段2执行失败: {str(e)}")
            
            # 创建失败的报告记录 - 使用独立的数据库会话
            try:
                from app.db.session import get_db_session
                with get_db_session() as new_db:
                    report_data = {
                        "task_id": task_id,
                        "user_id": context["user_id"],
                        "file_path": None,  # 失败时没有文件
                        "status": "failed",
                        "result": f"报告生成失败: {str(e)}"
                    }
                    
                    crud.report_history.create(
                        db=new_db,
                        obj_in=schemas.ReportHistoryCreate(**report_data)
                    )
                    new_db.commit()
                    logger.info(f"已创建失败报告记录 - 任务ID: {task_id}")
            except Exception as record_error:
                logger.warning(f"创建失败报告记录失败: {record_error}")
            
            return PhaseResult(
                phase=PipelinePhase.PHASE_2_EXECUTION,
                success=False,
                execution_time=execution_time,
                error=str(e)
            )
    
    async def _finalize_pipeline(
        self,
        context: Dict[str, Any],
        phase_results: Dict[PipelinePhase, PhaseResult],
        db: Session
    ) -> Dict[str, Any]:
        """完成流水线并生成最终结果"""
        task_id = context["task_id"]
        user_id = context["user_id"]
        
        try:
            if self.config.enable_progress_tracking:
                self._update_progress(task_id, user_id, "completed", 100, "两阶段流水线执行完成")
            
            # 从阶段2结果中提取最终数据
            phase2_result = phase_results.get(PipelinePhase.PHASE_2_EXECUTION)
            if phase2_result and phase2_result.success:
                final_data = phase2_result.data
                cache_statistics = phase2_result.metadata
                
                # 发送成功通知
                if self.config.enable_notifications:
                    try:
                        notification_service = NotificationService()
                        await notification_service.send_task_completion_notification(
                            task_id=task_id,
                            report_path=final_data.get("report_path"),
                            user_id=user_id
                        )
                    except Exception as notify_error:
                        logger.warning(f"发送成功通知失败: {notify_error}")
                
                return {
                    "success": True,
                    "data": final_data,
                    "report_path": final_data.get("report_path"),
                    "cache_statistics": cache_statistics
                }
            else:
                return {
                    "success": False,
                    "error": "阶段2未成功执行"
                }
                
        except Exception as e:
            logger.error(f"流水线完成处理失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_performance_metrics(
        self,
        phase_results: Dict[PipelinePhase, PhaseResult],
        total_time: float
    ) -> Dict[str, Any]:
        """计算性能指标"""
        metrics = {
            "total_execution_time": total_time,
            "phase_breakdown": {}
        }
        
        total_phase_time = 0
        for phase, result in phase_results.items():
            metrics["phase_breakdown"][phase.value] = {
                "execution_time": result.execution_time,
                "success": result.success,
                "percentage": (result.execution_time / total_time * 100) if total_time > 0 else 0
            }
            total_phase_time += result.execution_time
        
        # 计算效率指标
        metrics["overhead_time"] = total_time - total_phase_time
        metrics["efficiency"] = (total_phase_time / total_time * 100) if total_time > 0 else 0
        
        # 从阶段2提取缓存指标
        phase2_result = phase_results.get(PipelinePhase.PHASE_2_EXECUTION)
        if phase2_result and phase2_result.success:
            metrics["cache_performance"] = phase2_result.metadata
        
        return metrics
    
    def _update_progress(self, task_id: int, user_id: str, status: str, progress: int, message: str):
        """更新任务进度"""
        if self.config.enable_progress_tracking:
            status_data = {
                "status": status,
                "progress": progress,
                "message": message,
                "current_step": message,
                "pipeline_id": self.pipeline_id,
                "pipeline_type": "two_phase",
                "user_id": user_id
            }
            update_task_progress_dict(task_id, status_data)
            
            # 尝试发送WebSocket通知（异步方式）
            try:
                import asyncio
                from app.services.infrastructure.notification.notification_service import NotificationService
                
                async def send_websocket_notification():
                    try:
                        notification_service = NotificationService()
                        await notification_service.send_task_progress_update(task_id, status_data)
                    except Exception as e:
                        logger.debug(f"WebSocket通知发送失败: {e}")
                
                # 尝试在现有事件循环中运行
                try:
                    loop = asyncio.get_running_loop()
                    # 创建任务但不等待
                    loop.create_task(send_websocket_notification())
                except RuntimeError:
                    # 没有运行的事件循环，跳过WebSocket通知
                    pass
            except Exception as e:
                logger.debug(f"WebSocket通知初始化失败: {e}")


# 便捷函数
async def execute_two_phase_pipeline(
    task_id: int,
    user_id: str,
    config: Optional[PipelineConfiguration] = None,
    execution_context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> PipelineResult:
    """执行两阶段流水线的便捷函数"""
    pipeline = TwoPhasePipeline(config or PipelineConfiguration())
    return await pipeline.execute(task_id, user_id, execution_context=execution_context, **kwargs)


def create_pipeline_config(
    execution_mode: ExecutionMode = ExecutionMode.SMART_EXECUTION,
    force_reanalyze: bool = False,
    enable_caching: bool = True,
    **kwargs
) -> PipelineConfiguration:
    """创建流水线配置的便捷函数"""
    return PipelineConfiguration(
        execution_mode=execution_mode,
        force_reanalyze=force_reanalyze,
        enable_caching=enable_caching,
        **kwargs
    )