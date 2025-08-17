"""
Two-Phase Report Generation Pipeline

基于Template → Placeholder → Agent → ETL架构的两阶段报告生成流水线

阶段1: 模板分析和占位符处理 (Template → Placeholder → Agent分析)
阶段2: 数据提取和报告生成 (ETL → Report)
"""

import asyncio
import logging
import time
from datetime import datetime
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
from app.services.template.enhanced_template_parser import EnhancedTemplateParser
from app.services.agents.orchestration.cached_orchestrator import CachedAgentOrchestrator
from app.services.report_generation.word_generator_service import WordGeneratorService
from app.services.notification.notification_service import NotificationService
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
        db: Optional[Session] = None
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
            
            # 1. 初始化和验证
            initialization_result = await self._initialize_pipeline(
                task_id, user_id, template_id, data_source_id, db
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
                    return PipelineResult(
                        pipeline_id=self.pipeline_id,
                        success=False,
                        total_execution_time=time.time() - start_time,
                        phase_results=phase_results,
                        error=f"阶段1执行失败: {phase1_result.error}"
                    )
            
            if execution_mode in [ExecutionMode.FULL_PIPELINE, ExecutionMode.PHASE_2_ONLY]:
                # 执行阶段2: 数据提取和报告生成
                phase2_result = await self._execute_phase_2(context, db)
                phase_results[PipelinePhase.PHASE_2_EXECUTION] = phase2_result
                
                if not phase2_result.success:
                    return PipelineResult(
                        pipeline_id=self.pipeline_id,
                        success=False,
                        total_execution_time=time.time() - start_time,
                        phase_results=phase_results,
                        error=f"阶段2执行失败: {phase2_result.error}"
                    )
            
            # 4. 生成最终结果
            final_result = await self._finalize_pipeline(context, phase_results, db)
            
            total_time = time.time() - start_time
            logger.info(f"两阶段流水线执行完成 - Pipeline ID: {self.pipeline_id}, 总耗时: {total_time:.2f}秒")
            
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
        db: Session
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
            
            context = {
                "task_id": task_id,
                "user_id": user_id,
                "template_id": final_template_id,
                "data_source_id": final_data_source_id,
                "task": task,
                "template": template,
                "data_source": data_source,
                "pipeline_config": self.config
            }
            
            logger.info(f"流水线初始化完成 - Template: {final_template_id}, DataSource: {final_data_source_id}")
            return {"success": True, "context": context}
            
        except Exception as e:
            logger.error(f"流水线初始化失败: {e}")
            return {"success": False, "error": str(e)}
    
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
                
                cached_orchestrator = CachedAgentOrchestrator(db)
                analysis_result = await cached_orchestrator._execute_phase1_analysis(
                    template_id, data_source_id, self.config.force_reanalyze
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
        
        try:
            if self.config.enable_progress_tracking:
                self._update_progress(task_id, user_id, "extracting", 50, "阶段2: 数据提取和报告生成")
            
            logger.info(f"开始阶段2执行 - Template: {template_id}")
            
            # 1. 缓存优先的数据提取
            self._update_progress(task_id, user_id, "extracting", 60, "提取占位符数据")
            
            cached_orchestrator = CachedAgentOrchestrator(db)
            extraction_result = await cached_orchestrator._execute_phase2_extraction_and_generation(
                template_id, data_source_id, user_id
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
            report_path = word_generator.generate_report(
                content=extraction_result["processed_content"],
                title=task.name,
                format="docx"
            )
            
            # 3. 保存报告记录
            self._update_progress(task_id, user_id, "finalizing", 90, "保存报告记录")
            
            execution_time = time.time() - start_time
            
            report_data = {
                "task_id": task_id,
                "user_id": context["user_id"],
                "file_path": report_path,
                "status": "completed",
                "result": extraction_result["processed_content"]
            }
            
            report_record = crud.report_history.create(
                db=db,
                obj_in=schemas.ReportHistoryCreate(**report_data)
            )
            
            phase2_data = {
                "extraction_result": extraction_result,
                "report_path": report_path,
                "report_id": report_record.id,
                "processed_content": extraction_result["processed_content"]
            }
            
            cache_stats = {
                "cache_hit_rate": extraction_result.get("cache_hit_rate", 0),
                "processed_placeholders": extraction_result.get("processed_placeholders", 0),
                "total_placeholders": extraction_result.get("total_placeholders", 0)
            }
            
            logger.info(f"阶段2执行完成 - 耗时: {execution_time:.2f}秒, 缓存命中率: {cache_stats['cache_hit_rate']:.1f}%")
            
            return PhaseResult(
                phase=PipelinePhase.PHASE_2_EXECUTION,
                success=True,
                execution_time=execution_time,
                data=phase2_data,
                metadata=cache_stats
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"阶段2执行失败: {e}")
            
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
                        notification_service.send_task_completion_notification(
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


# 便捷函数
async def execute_two_phase_pipeline(
    task_id: int,
    user_id: str,
    config: Optional[PipelineConfiguration] = None,
    **kwargs
) -> PipelineResult:
    """执行两阶段流水线的便捷函数"""
    pipeline = TwoPhasePipeline(config or PipelineConfiguration())
    return await pipeline.execute(task_id, user_id, **kwargs)


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