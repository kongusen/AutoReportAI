from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.services.application.task_management.execution.two_phase_pipeline import (
    PipelineConfiguration,
    ExecutionMode,
)
from app.services.application.orchestration.two_phase_orchestrator import TwoPhaseOrchestrator


@dataclass
class TwoPhaseWorkflowResult:
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None


class TwoPhaseReportWorkflow:
    """两阶段报告生成工作流（应用层包装）

    目前委托给现有的 TwoPhasePipeline 执行，后续将逐步内聚迁移实现细节到应用层。
    """

    def __init__(self, db: Session, config: Optional[PipelineConfiguration] = None):
        self.db = db
        self.config = config or PipelineConfiguration(execution_mode=ExecutionMode.SMART_EXECUTION)
        self._orchestrator = TwoPhaseOrchestrator(self.db, self.config)

    async def execute_for_task(
        self,
        task_id: int,
        user_id: str,
        execution_context: Optional[Dict[str, Any]] = None,
    ) -> TwoPhaseWorkflowResult:
        init_res = await self._orchestrator.initialize(task_id, user_id, None, None, execution_context)
        if not init_res.get("success"):
            return TwoPhaseWorkflowResult(success=False, data={}, error=init_res.get("error"))
        ctx = init_res["context"]
        # 智能模式暂按 FULL_PIPELINE 执行（后续抽取智能选择）
        phase1 = await self._orchestrator.run_phase_1(ctx)
        if not phase1.success:
            return TwoPhaseWorkflowResult(success=False, data={"phase1": phase1.__dict__}, error=phase1.error)
        phase2 = await self._orchestrator.run_phase_2(ctx)
        success = phase2.success
        result = {
            "phase_results": {
                "phase_1_analysis": phase1.__dict__,
                "phase_2_execution": phase2.__dict__,
            },
            "final_output": phase2.data,
            "report_path": phase2.data.get("report_path") if phase2.data else None,
            "cache_statistics": phase2.metadata,
            "performance_metrics": {
                "total_execution_time": (phase1.execution_time + phase2.execution_time),
            },
        }
        return TwoPhaseWorkflowResult(
            success=success,
            data=result,
            error=phase2.error if not success else None,
        )


