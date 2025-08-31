"""
工作流集成模块 - DAG架构下已被智能代理系统替代
Legacy workflows disabled in favor of DAG-based agent orchestration
"""

# 在DAG架构下，这些workflow已被agents系统的DAG编排替代
# 直接使用 IntelligentPlaceholderService + Agents DAG 即可
# 
# Legacy imports disabled:
# from .intelligent_placeholder_workflow import IntelligentPlaceholderWorkflow
# from .context_aware_task_service import ContextAwareTaskService
# from .enhanced_report_generation_workflow import EnhancedReportGenerationWorkflow
# from .template_debug_workflow import TemplateDebugWorkflow

# 推荐的新架构使用方式：
# from app.services.domain.placeholder import IntelligentPlaceholderService
# from app.services.agents import execute_placeholder_with_context

__all__ = [
    # 'IntelligentPlaceholderWorkflow',  # Replaced by DAG agents
    # 'ContextAwareTaskService',        # Replaced by DAG agents
    # 'EnhancedReportGenerationWorkflow',  # Replaced by DAG agents 
    # 'TemplateDebugWorkflow'           # Replaced by DAG agents
]

def get_migration_info():
    """
    获取从workflow到DAG架构的迁移信息
    """
    return {
        "status": "migrated_to_dag",
        "old_workflows": [
            "IntelligentPlaceholderWorkflow",
            "ContextAwareTaskService", 
            "EnhancedReportGenerationWorkflow",
            "TemplateDebugWorkflow"
        ],
        "new_architecture": {
            "entry_point": "IntelligentPlaceholderService",
            "orchestration": "Agents DAG system",
            "execution": "Background Controller",
            "context_management": "Context Engineering"
        },
        "usage_example": """
        # Old way (workflow):
        # workflow = IntelligentPlaceholderWorkflow()
        # result = await workflow.execute(template, context)
        
        # New way (DAG agents):
        service = IntelligentPlaceholderService()
        result = await service.analyze_template_for_sql_generation(
            template_content, template_id, user_id
        )
        """
    }