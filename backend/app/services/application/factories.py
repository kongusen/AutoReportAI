"""
应用层中立工厂

为上层（如 orchestrator）提供与领域服务（如模板分析服务）之间的中立构造，
避免 `agents ↔ template` 直接互相引用。
"""

from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session


def create_agent_sql_analysis_service(db: Session, user_id: Optional[str] = None):
    """创建 AgentSQLAnalysisService 的中立工厂方法。

    通过此工厂避免在 orchestrator 中直接导入 template 下的实现，
    降低互相依赖风险。
    """
    # 延迟导入，避免在导入期触发循环依赖
    from app.services.domain.template.agent_sql_analysis_service import AgentSQLAnalysisService

    return AgentSQLAnalysisService(db, user_id=user_id)


def create_enhanced_template_parser(db: Session):
    """创建 EnhancedTemplateParser 的中立工厂方法。"""
    # 延迟导入，避免在导入期触发循环依赖
    from app.services.domain.template.enhanced_template_parser import EnhancedTemplateParser

    return EnhancedTemplateParser(db)


def create_service_coordinator(db: Session, user_id: Optional[str] = None):
    from app.services.application.orchestration.service_coordinator import ServiceCoordinator
    return ServiceCoordinator(db, user_id=user_id)


def create_placeholder_workflow(db: Session, user_id: Optional[str] = None):
    from app.services.application.workflows.placeholder_workflow import PlaceholderWorkflow
    return PlaceholderWorkflow(db, user_id=user_id)


def create_two_phase_report_workflow(db: Session):
    from app.services.application.workflows.two_phase_report_workflow import TwoPhaseReportWorkflow
    return TwoPhaseReportWorkflow(db)


def create_placeholder_sql_agent(db: Session, user_id: Optional[str] = None):
    """创建占位符SQL分析代理"""
    # 直接使用IAOP专业化代理
    from app.services.iaop.agents.specialized.sql_generation_agent import SQLGenerationAgent as PlaceholderSQLAnalyzer
    return PlaceholderSQLAnalyzer(db_session=db, user_id=user_id)


def create_multi_database_agent(db: Session, user_id: Optional[str] = None):
    """创建多数据库智能代理的工厂方法（向后兼容）"""
    return create_placeholder_sql_agent(db, user_id)


def create_context_aware_agent_registry():
    """创建上下文感知的Agent注册表"""
    # 直接使用IAOP核心系统
    from app.services.iaop.context.context_manager import IAOPContextManager
    from app.services.iaop.registry.agent_registry import IAOPAgentRegistry
    context_manager = get_context_manager()
    return get_agent_registry(context_manager)


