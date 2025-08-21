from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.services.application.orchestration.service_coordinator import ServiceCoordinator, CoordinatorConfig


@dataclass
class WorkflowResult:
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None


class PlaceholderWorkflow:
    """占位符处理工作流（应用层）"""

    def __init__(self, db: Session, user_id: Optional[str] = None, config: Optional[CoordinatorConfig] = None):
        self.coordinator = ServiceCoordinator(db, user_id=user_id, config=config)

    async def execute(self, template_id: str, data_source_id: str, user_id: str, execution_context: Optional[Dict[str, Any]] = None) -> WorkflowResult:
        try:
            result = await self.coordinator.run_two_phase(
                template_id=template_id,
                data_source_id=data_source_id,
                user_id=user_id,
                execution_context=execution_context,
            )
            return WorkflowResult(success=result.get("success", False), data=result, error=result.get("error"))
        except Exception as e:
            return WorkflowResult(success=False, data={}, error=str(e))

    async def execute_for_task(self, task_id: int, user_id: str, force_reanalyze: bool = False, execution_context: Optional[Dict[str, Any]] = None) -> WorkflowResult:
        """根据 task_id 自动解析 template/data_source 并执行两阶段流程"""
        try:
            # 懒导入避免循环依赖
            from app import crud
            task = crud.task.get(self.coordinator.db, id=task_id)
            if not task:
                return WorkflowResult(success=False, data={}, error=f"任务不存在: {task_id}")

            # 可动态调整re-analyze
            if force_reanalyze:
                self.coordinator.config.force_reanalyze = True

            return await self.execute(
                template_id=str(task.template_id),
                data_source_id=str(task.data_source_id),
                user_id=user_id,
                execution_context=execution_context,
            )
        except Exception as e:
            return WorkflowResult(success=False, data={}, error=str(e))


