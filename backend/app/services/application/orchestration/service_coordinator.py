from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session


@dataclass
class CoordinatorConfig:
    enable_caching: bool = True
    force_reanalyze: bool = False


class ServiceCoordinator:
    """应用层服务协调器

    负责跨领域服务的编排调用（模板占位符 → Agent → 数据 → 报告）。
    """

    def __init__(self, db: Session, user_id: Optional[str] = None, config: Optional[CoordinatorConfig] = None):
        self.db = db
        self.user_id = user_id
        self.config = config or CoordinatorConfig()

        # 延迟导入，避免循环依赖
        from app.services.application.factories import (
            create_enhanced_template_parser,
            create_agent_sql_analysis_service,
        )
        from app.services.agents.orchestration.cached_orchestrator import CachedAgentOrchestrator

        self.template_parser = create_enhanced_template_parser(db)
        self.sql_analysis_service = create_agent_sql_analysis_service(db, user_id)
        self.cached_orchestrator = CachedAgentOrchestrator(db, user_id=user_id)

    async def prepare_template(self, template_id: str, template_content: str, force_reparse: bool = False) -> Dict[str, Any]:
        return await self.template_parser.parse_and_store_template_placeholders(
            template_id, template_content, force_reparse
        )

    async def run_two_phase(self, template_id: str, data_source_id: str, user_id: str, execution_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self.cached_orchestrator.execute_two_phase_pipeline(
            template_id=template_id,
            data_source_id=data_source_id,
            user_id=user_id,
            force_reanalyze=self.config.force_reanalyze,
        )


