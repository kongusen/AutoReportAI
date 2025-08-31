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


# ServiceCoordinator已删除，使用新的工作流系统


def create_intelligent_placeholder_workflow(config=None):
    """创建智能占位符工作流"""
    from app.services.application.workflows.intelligent_placeholder_workflow import IntelligentPlaceholderWorkflow
    return IntelligentPlaceholderWorkflow(config=config)


def create_enhanced_report_generation_workflow(placeholder_orchestrator=None, config=None):
    """创建增强报告生成工作流"""
    from app.services.application.workflows.enhanced_report_generation_workflow import EnhancedReportGenerationWorkflow
    return EnhancedReportGenerationWorkflow(placeholder_orchestrator=placeholder_orchestrator, config=config)


def create_context_aware_task_service(orchestrator=None, execution_strategy=None):
    """创建上下文感知任务服务"""
    from app.services.application.workflows.context_aware_task_service import ContextAwareTaskService
    return ContextAwareTaskService(orchestrator=orchestrator, execution_strategy=execution_strategy)


def create_template_debug_workflow(placeholder_orchestrator=None):
    """创建模板调试工作流"""
    from app.services.application.workflows.template_debug_workflow import TemplateDebugWorkflow
    return TemplateDebugWorkflow(placeholder_orchestrator=placeholder_orchestrator)


def create_placeholder_sql_agent(db: Session, user_id: Optional[str] = None):
    """创建占位符SQL分析代理 - 已迁移到新的LegacyMigrationService"""
    # 使用新的迁移适配器
    from app.services.application.workflows.legacy_placeholder_migration import get_legacy_migration_service
    migration_service = get_legacy_migration_service()
    return migration_service.get_adapter(db_session=db, session_key=user_id or "default")


def create_multi_database_agent(db: Session, user_id: Optional[str] = None):
    """创建多数据库智能代理的工厂方法（向后兼容）"""
    return create_placeholder_sql_agent(db, user_id)


def create_context_aware_agent_registry():
    """创建上下文感知的Agent注册表 - 已迁移到新的架构"""
    # 使用新的LLM Agent集成系统
    from app.services.llm_agents.integration.agents_integration import get_agents_integration
    return get_agents_integration()


