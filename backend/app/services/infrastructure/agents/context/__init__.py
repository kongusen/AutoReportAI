"""
Agent 上下文系统
===============

智能代理上下文构建和管理系统，包括：
- 上下文构建器
- 占位符解析
- 模板处理
- 数据库架构集成
- 使用示例和演示
"""

from .context_builder import (
    AgentContextBuilder,
    ContextType,
    PlaceholderType,
    PlaceholderInfo,
    DatabaseSchemaInfo,
    TemplateInfo,
    TaskInfo,
    AgentContext,
    create_simple_context
)

from .context_examples import ContextExamples

# 便捷函数
def create_context_for_task(
    task_name: str,
    task_description: str,
    context_type: ContextType = None,
    **kwargs
) -> AgentContext:
    """
    为任务创建上下文的便捷函数
    
    Args:
        task_name: 任务名称
        task_description: 任务描述
        context_type: 上下文类型（自动推断如果为None）
        **kwargs: 其他上下文参数
    
    Returns:
        AgentContext: 构建好的上下文
    """
    return create_simple_context(
        task_name=task_name,
        task_description=task_description,
        placeholders_dict=kwargs.get('placeholders', {}),
        table_schemas=kwargs.get('table_schemas', []),
        context_type=context_type
    )

def create_data_analysis_context(
    task_name: str,
    data_source: str,
    metrics: list = None,
    time_range: dict = None
) -> AgentContext:
    """创建数据分析专用上下文"""
    
    placeholders = {
        'data_source': data_source
    }
    
    if metrics:
        placeholders['metrics'] = metrics
    if time_range:
        placeholders['time_range'] = time_range
    
    return create_simple_context(
        task_name=task_name,
        task_description=f"分析数据源 {data_source}",
        placeholders_dict=placeholders,
        context_type=ContextType.DATA_ANALYSIS
    )

def create_sql_generation_context(
    task_name: str,
    table_names: list,
    columns: list = None,
    conditions: dict = None
) -> AgentContext:
    """创建SQL生成专用上下文"""
    
    placeholders = {
        'table_names': table_names
    }
    
    if columns:
        placeholders['columns'] = columns
    if conditions:
        placeholders['conditions'] = conditions
    
    return create_simple_context(
        task_name=task_name,
        task_description=f"为表 {', '.join(table_names)} 生成SQL查询",
        placeholders_dict=placeholders,
        context_type=ContextType.SQL_GENERATION
    )

def create_report_generation_context(
    task_name: str,
    data_sources: list,
    report_type: str = "analytical",
    include_charts: bool = True
) -> AgentContext:
    """创建报告生成专用上下文"""
    
    placeholders = {
        'data_sources': data_sources,
        'report_type': report_type,
        'include_charts': include_charts
    }
    
    return create_simple_context(
        task_name=task_name,
        task_description=f"生成 {report_type} 类型报告",
        placeholders_dict=placeholders,
        context_type=ContextType.REPORT_GENERATION
    )

def create_business_intelligence_context(
    task_name: str,
    kpi_metrics: list,
    time_dimension: dict = None,
    dashboard_type: str = "executive"
) -> AgentContext:
    """创建商业智能专用上下文"""
    
    placeholders = {
        'kpi_metrics': kpi_metrics,
        'dashboard_type': dashboard_type
    }
    
    if time_dimension:
        placeholders['time_dimension'] = time_dimension
    
    return create_simple_context(
        task_name=task_name,
        task_description=f"创建 {dashboard_type} 类型BI仪表板",
        placeholders_dict=placeholders,
        context_type=ContextType.BUSINESS_INTELLIGENCE
    )

# 全局上下文构建器实例
_global_context_builder = None

def get_context_builder() -> AgentContextBuilder:
    """获取全局上下文构建器实例"""
    global _global_context_builder
    if _global_context_builder is None:
        _global_context_builder = AgentContextBuilder()
    return _global_context_builder

def get_context_examples() -> ContextExamples:
    """获取上下文示例实例"""
    return ContextExamples()

__all__ = [
    # 核心类
    "AgentContextBuilder",
    "ContextType",
    "PlaceholderType",
    "PlaceholderInfo",
    "DatabaseSchemaInfo",
    "TemplateInfo",
    "TaskInfo",
    "AgentContext",
    
    # 示例系统
    "ContextExamples",
    
    # 便捷函数
    "create_simple_context",
    "create_context_for_task",
    "create_data_analysis_context",
    "create_sql_generation_context",
    "create_report_generation_context",
    "create_business_intelligence_context",
    
    # 全局实例
    "get_context_builder",
    "get_context_examples"
]