"""
应用层现代化工厂

为上层提供与领域服务之间的现代化构造，
移除向后兼容负担，专注于纯数据库驱动架构。
"""

from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session


def create_agent_sql_analysis_service(db: Session, user_id: str):
    """创建 AgentSQLAnalysisService 的现代化工厂方法。

    通过此工厂避免在 orchestrator 中直接导入 template 下的实现，
    降低互相依赖风险。
    要求user_id参数，与纯数据库驱动架构保持一致。
    """
    if not user_id:
        raise ValueError("user_id is required for Agent SQL Analysis Service")
    
    # 延迟导入，避免在导入期触发循环依赖
    from app.services.domain.template.agent_sql_analysis_service import AgentSQLAnalysisService

    return AgentSQLAnalysisService(db, user_id=user_id)


def create_enhanced_template_parser(db: Session):
    """创建 EnhancedTemplateParser 的中立工厂方法。"""
    # 延迟导入，避免在导入期触发循环依赖
    from app.services.domain.template.enhanced_template_parser import EnhancedTemplateParser

    return EnhancedTemplateParser(db)


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


# === 现代化纯数据库驱动工厂 ===

def create_pure_database_schema_analysis_service(db: Session, user_id: str):
    """创建纯数据库驱动的Schema分析服务"""
    if not user_id:
        raise ValueError("user_id is required for Schema Analysis Service")
    
    from app.services.data.schemas.schema_analysis_service import create_schema_analysis_service
    return create_schema_analysis_service(db, user_id)


def create_pure_database_react_agent(user_id: str):
    """创建纯数据库驱动的React智能代理"""
    if not user_id:
        raise ValueError("user_id is required for Pure Database React Agent")
    
    from app.services.infrastructure.ai.agents import create_pure_database_react_agent
    return create_pure_database_react_agent(user_id)


def create_user_etl_service(user_id: str):
    """创建用户专属的ETL服务"""
    if not user_id:
        raise ValueError("user_id is required for User ETL Service")
    
    from app.services.data.processing.etl.etl_service import ETLService
    return ETLService()


# === 导出列表 ===

__all__ = [
    # 传统工厂方法（保持API兼容性）
    "create_agent_sql_analysis_service",
    "create_enhanced_template_parser", 
    "create_intelligent_placeholder_workflow",
    "create_enhanced_report_generation_workflow",
    "create_context_aware_task_service",
    "create_template_debug_workflow",
    
    # 现代化纯数据库驱动工厂
    "create_pure_database_schema_analysis_service",
    "create_pure_database_react_agent", 
    "create_user_etl_service",
]