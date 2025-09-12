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


def create_enhanced_template_parser(db: Session, user_id: str):
    """创建 EnhancedTemplateParser 的中立工厂方法。"""
    if not user_id:
        raise ValueError("user_id is required for Enhanced Template Parser")
    
    # 使用新的Claude Code架构模板解析服务
    # Service orchestrator has been migrated to agents system
    from app.services.infrastructure.agents import execute_agent_task
    
    # Return a compatibility wrapper for agents system
    class AgentsTemplateParserWrapper:
        def __init__(self, user_id: str):
            self.user_id = user_id
        
        async def parse_template_structure(self, template_content: str):
            # Use agents system for template parsing
            return await execute_agent_task(
                task_name="template_parsing",
                task_description="Parse template structure",
                context_data={
                    "template_content": template_content,
                    "user_id": self.user_id
                }
            )
    
    return AgentsTemplateParserWrapper(user_id)


def create_intelligent_placeholder_workflow(user_id: str, config=None):
    """创建智能占位符工作流"""
    if not user_id:
        raise ValueError("user_id is required for Intelligent Placeholder Workflow")
    
    from app.services.application.workflows.intelligent_placeholder_workflow import IntelligentPlaceholderWorkflow
    return IntelligentPlaceholderWorkflow(user_id=user_id, config=config)


def create_enhanced_report_generation_workflow(user_id: str, placeholder_orchestrator=None, config=None):
    """创建增强报告生成工作流"""
    if not user_id:
        raise ValueError("user_id is required for Enhanced Report Generation Workflow")
    
    from app.services.application.workflows.enhanced_report_generation_workflow import EnhancedReportGenerationWorkflow
    return EnhancedReportGenerationWorkflow(user_id=user_id, placeholder_orchestrator=placeholder_orchestrator, config=config)


def create_context_aware_task_service(user_id: str, orchestrator=None, execution_strategy=None):
    """创建上下文感知任务服务"""
    if not user_id:
        raise ValueError("user_id is required for Context Aware Task Service")
    
    from app.services.application.workflows.context_aware_task_service import ContextAwareTaskService
    return ContextAwareTaskService(user_id=user_id, orchestrator=orchestrator, execution_strategy=execution_strategy)


def create_template_debug_workflow(user_id: str, placeholder_orchestrator=None):
    """创建模板调试工作流"""
    if not user_id:
        raise ValueError("user_id is required for Template Debug Workflow")
    
    from app.services.application.workflows.template_debug_workflow import TemplateDebugWorkflow
    return TemplateDebugWorkflow(user_id=user_id, placeholder_orchestrator=placeholder_orchestrator)


# === 现代化纯数据库驱动工厂 ===

def create_pure_database_schema_analysis_service(db: Session, user_id: str):
    """创建纯数据库驱动的Schema分析服务"""
    if not user_id:
        raise ValueError("user_id is required for Schema Analysis Service")
    
    from app.services.data.schemas.schema_analysis_service import create_schema_analysis_service
    return create_schema_analysis_service(db, user_id)


def create_service_orchestrator(user_id: str = None):
    """创建新的Claude Code架构ServiceOrchestrator实例 - 已迁移到agents系统"""
    # Service orchestrator has been migrated to agents system
    from app.services.infrastructure.agents import execute_agent_task
    
    # Return a compatibility wrapper for agents system
    class AgentsServiceOrchestratorWrapper:
        def __init__(self, user_id: str = None):
            self.user_id = user_id
        
        async def orchestrate_task(self, task_name: str, task_description: str, context_data: dict):
            # Use agents system for orchestration
            return await execute_agent_task(
                task_name=task_name,
                task_description=task_description,
                context_data=context_data
            )
    
    return AgentsServiceOrchestratorWrapper(user_id)


def create_user_etl_service(user_id: str):
    """创建用户专属的ETL服务"""
    if not user_id:
        raise ValueError("user_id is required for User ETL Service")
    
    from app.services.data.processing.etl.etl_service import create_etl_service
    return create_etl_service(user_id)


def create_intelligent_etl_executor(db: Session, user_id: str):
    """创建用户专属的智能ETL执行器"""
    if not user_id:
        raise ValueError("user_id is required for Intelligent ETL Executor")
    
    from app.services.data.processing.etl.intelligent_etl_executor import create_intelligent_etl_executor as create_etl_executor_impl
    return create_etl_executor_impl(db, user_id)


def create_query_optimizer(user_id: str):
    """创建用户专属的查询优化器"""
    if not user_id:
        raise ValueError("user_id is required for Query Optimizer")
    
    from app.services.data.processing.query_optimizer import create_query_optimizer as create_optimizer_impl
    return create_optimizer_impl(user_id)


def create_schema_aware_analysis_service(db: Session, user_id: str):
    """创建用户专属的Schema感知分析服务"""
    if not user_id:
        raise ValueError("user_id is required for Schema Aware Analysis Service")
    
    from app.services.data.processing.schema_aware_analysis import create_schema_aware_analysis_service as create_analysis_impl
    return create_analysis_impl(db, user_id)


def create_data_analysis_service(db: Session, user_id: str = None):
    """创建数据分析服务"""
    from app.services.data.processing.analysis import create_data_analysis_service as create_analysis_service_impl
    return create_analysis_service_impl(db, user_id)


def create_ai_tools_integration_service(user_id: str):
    """创建AI工具集成服务"""
    if not user_id:
        raise ValueError("user_id is required for AI Tools Integration Service")
    
    # AI tools integration has been migrated to agents system
    from app.services.infrastructure.agents.tools import get_tool_registry
    
    # Return a compatibility wrapper for the migrated system
    class AgentsToolsIntegration:
        def __init__(self, user_id: str):
            self.user_id = user_id
            self.tool_registry = get_tool_registry()
        
        def get_available_tools(self):
            return self.tool_registry.get_all_tools()
    
    return AgentsToolsIntegration(user_id)


# === 任务服务工厂 ===

def create_task_application_service(user_id: str = None):
    """创建任务应用服务"""
    from app.services.application.tasks.task_application_service import TaskApplicationService
    return TaskApplicationService()


def create_task_execution_service(user_id: str):
    """创建任务执行服务"""
    if not user_id:
        raise ValueError("user_id is required for Task Execution Service")
    
    from app.services.application.tasks.task_execution_service import TaskExecutionService
    return TaskExecutionService(user_id=user_id)


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
    "create_service_orchestrator",  # 新的Claude Code架构 
    "create_user_etl_service",
    
    # 数据处理服务工厂
    "create_intelligent_etl_executor",
    "create_query_optimizer", 
    "create_schema_aware_analysis_service",
    "create_data_analysis_service",
    
    # AI工具集成服务
    "create_ai_tools_integration_service",
    
    # 任务服务工厂
    "create_task_application_service",
    "create_task_execution_service",
]