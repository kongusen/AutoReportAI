from __future__ import annotations

import time
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app import crud, schemas
from app.services.domain.template.enhanced_template_parser import EnhancedTemplateParser
from app.services.application.orchestration.cached_agent_orchestrator import CachedAgentOrchestrator
from app.services.report_generation.word_generator_service import WordGeneratorService
from app.services.application.task_management.execution.two_phase_pipeline import (
    PipelineConfiguration,
    ExecutionMode,
    PipelinePhase,
    PhaseResult,
)

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationContext:
    task_id: int
    user_id: str
    template_id: str
    data_source_id: str
    task: Any
    template: Any
    data_source: Any
    pipeline_config: PipelineConfiguration
    execution_context: Optional[Dict[str, Any]] = None


class TwoPhaseOrchestrator:
    def __init__(self, db: Session, config: Optional[PipelineConfiguration] = None):
        self.db = db
        self.config = config or PipelineConfiguration()

    async def initialize(self, task_id: int, user_id: str, template_id: Optional[str], data_source_id: Optional[str], execution_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            task = crud.task.get(self.db, id=task_id)
            if not task:
                return {"success": False, "error": f"任务不存在: {task_id}"}
            final_template_id = template_id or str(task.template_id)
            final_data_source_id = data_source_id or str(task.data_source_id)
            template = crud.template.get(self.db, id=final_template_id)
            data_source = crud.data_source.get(self.db, id=final_data_source_id)
            if not template:
                return {"success": False, "error": f"模板不存在: {final_template_id}"}
            if not data_source:
                return {"success": False, "error": f"数据源不存在: {final_data_source_id}"}

            context = OrchestrationContext(
                task_id=task_id,
                user_id=user_id,
                template_id=final_template_id,
                data_source_id=final_data_source_id,
                task=task,
                template=template,
                data_source=data_source,
                pipeline_config=self.config,
                execution_context=execution_context,
            )
            return {"success": True, "context": context}
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return {"success": False, "error": str(e)}

    async def run_phase_1(self, ctx: OrchestrationContext) -> PhaseResult:
        start_time = time.time()
        try:
            template_parser = EnhancedTemplateParser(self.db)
            parse_result = await template_parser.parse_and_store_template_placeholders(
                ctx.template_id, ctx.template.content, self.config.force_reanalyze
            )
            if not parse_result.get("success"):
                return PhaseResult(PipelinePhase.PHASE_1_ANALYSIS, False, time.time() - start_time, error=parse_result.get("error"))

            analysis_result = {"success": True, "message": "无需Agent分析"}
            if parse_result.get("requires_agent_analysis", 0) > 0:
                cached = CachedAgentOrchestrator(self.db, user_id=ctx.user_id)
                analysis_result = await cached._execute_phase1_analysis(
                    ctx.template_id, ctx.data_source_id, self.config.force_reanalyze, ctx.execution_context
                )
                if not analysis_result.get("success"):
                    return PhaseResult(PipelinePhase.PHASE_1_ANALYSIS, False, time.time() - start_time, error=analysis_result.get("error"))

            readiness = await template_parser.check_template_ready_for_execution(ctx.template_id)
            return PhaseResult(
                PipelinePhase.PHASE_1_ANALYSIS,
                True,
                time.time() - start_time,
                data={
                    "parse_result": parse_result,
                    "analysis_result": analysis_result,
                    "readiness_check": readiness,
                    "template_ready": readiness.get("ready"),
                },
                metadata={
                    "total_placeholders": parse_result.get("total_placeholders", 0),
                    "analyzed_placeholders": analysis_result.get("analyzed_placeholders", 0),
                    "template_ready": readiness.get("ready"),
                },
            )
        except Exception as e:
            return PhaseResult(PipelinePhase.PHASE_1_ANALYSIS, False, time.time() - start_time, error=str(e))

    async def run_phase_2(self, ctx: OrchestrationContext) -> PhaseResult:
        start_time = time.time()
        try:
            cached = CachedAgentOrchestrator(self.db, user_id=ctx.user_id)
            extraction_result = await cached._execute_phase2_extraction_and_generation(
                ctx.template_id, ctx.data_source_id, ctx.user_id, ctx.execution_context
            )
            if not extraction_result.get("success"):
                return PhaseResult(PipelinePhase.PHASE_2_EXECUTION, False, time.time() - start_time, error=extraction_result.get("error"))

            word_generator = WordGeneratorService()
            template_content = getattr(ctx.template, 'content', '') or ''
            template_type = getattr(ctx.template, 'template_type', 'docx')
            output_format = template_type if template_type in ['docx', 'xlsx', 'txt', 'html'] else 'docx'
            try:
                report_path = word_generator.generate_report_from_template(
                    template_content=template_content,
                    placeholder_values=extraction_result.get("placeholder_values", {}),
                    title=ctx.task.name,
                    format=output_format
                )
            except Exception:
                report_path = word_generator.generate_report(
                    content=extraction_result.get("processed_content", "报告生成失败"),
                    title=ctx.task.name,
                    format=output_format
                )

            # 使用新的数据库会话避免事务问题
            from app.db.session import get_db_session
            report_id = None
            try:
                with get_db_session() as new_db:
                    report_data = {
                        "task_id": ctx.task_id,
                        "user_id": ctx.user_id,
                        "file_path": report_path,
                        "status": "completed",
                        "result": f"报告生成成功",
                        "processing_metadata": {}  # 使用空字典而不是None
                    }
                    report_record = crud.report_history.create(new_db, obj_in=schemas.ReportHistoryCreate(**report_data))
                    new_db.commit()
                    report_id = report_record.id  # 在会话关闭前获取ID
            except Exception as db_error:
                logger.error(f"创建报告历史记录失败: {db_error}")
                report_id = None
            
            return PhaseResult(
                PipelinePhase.PHASE_2_EXECUTION,
                True,
                time.time() - start_time,
                data={
                    "extraction_result": extraction_result,
                    "report_path": report_path,
                    "report_id": report_id,
                    "processed_content": extraction_result.get("processed_content", "报告生成成功"),
                },
                metadata={
                    "cache_hit_rate": extraction_result.get("cache_hit_rate", 0),
                    "processed_placeholders": extraction_result.get("processed_placeholders", 0),
                    "total_placeholders": extraction_result.get("total_placeholders", 0),
                }
            )
        except Exception as e:
            return PhaseResult(PipelinePhase.PHASE_2_EXECUTION, False, time.time() - start_time, error=str(e))


