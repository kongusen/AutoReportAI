"""
Agent Context Helpers

为各个API端点提供合适的Agent上下文数据构建辅助函数
基于AgentContextBuilder设计，提供语义化的上下文数据
"""

from typing import Dict, Any, List, Optional
from app.services.infrastructure.agents.context.context_builder import (
    AgentContextBuilder, TaskInfo, PlaceholderInfo, TemplateInfo, 
    DatabaseSchemaInfo, ContextType, PlaceholderType
)
from app.services.infrastructure.agents.core.message_types import MessagePriority


def create_template_analysis_context(
    template_id: str,
    template_name: str,
    template_content: str,
    template_type: str = "report",
    data_source_info: Dict[str, Any] = None,
    optimization_level: str = "standard"
) -> Dict[str, Any]:
    """
    创建模板分析的Agent上下文
    
    Args:
        template_id: 模板ID
        template_name: 模板名称
        template_content: 模板内容
        template_type: 模板类型
        data_source_info: 数据源信息
        optimization_level: 优化级别
    
    Returns:
        Dict: Agent上下文数据
    """
    builder = AgentContextBuilder()
    
    # 创建任务信息
    task_info = TaskInfo(
        task_id=f"template_analysis_{template_id}",
        task_name=f"分析模板占位符 - {template_name}",
        task_type="template_analysis",
        description=f"分析模板 {template_name} 的占位符，识别数据字段映射关系",
        priority=MessagePriority.HIGH,
        requirements=[
            "识别模板中的占位符",
            "分析占位符的数据类型和约束",
            "推断数据字段映射关系",
            "生成SQL查询建议"
        ],
        expected_outputs=[
            "占位符清单",
            "数据字段映射",
            "SQL查询建议",
            "优化建议"
        ]
    )
    
    # 创建模板信息
    templates = [TemplateInfo(
        template_id=template_id,
        name=template_name,
        template_type=template_type,
        content=template_content,
        variables=[],  # 将由解析器填充
        metadata={
            "optimization_level": optimization_level,
            "source": "template_api"
        }
    )]
    
    # 创建数据库架构信息（如果有数据源信息）
    database_schemas = []
    if data_source_info:
        schema = DatabaseSchemaInfo(
            table_name=data_source_info.get("default_table", "main_table"),
            metadata={
                "data_source_name": data_source_info.get("name"),
                "data_source_type": data_source_info.get("type"),
                "connection_info": data_source_info.get("connection_info", {})
            }
        )
        database_schemas.append(schema)
    
    # 构建上下文
    context = builder.build_context(
        task_info=task_info,
        templates=templates,
        database_schemas=database_schemas,
        context_type=ContextType.TEMPLATE_PROCESSING
    )
    
    return context.to_dict()


def create_report_generation_context(
    report_type: str,
    data_source_info: Dict[str, Any],
    user_requirements: Dict[str, Any],
    template_info: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    创建报告生成的Agent上下文
    
    Args:
        report_type: 报告类型
        data_source_info: 数据源信息
        user_requirements: 用户需求
        template_info: 模板信息
    
    Returns:
        Dict: Agent上下文数据
    """
    builder = AgentContextBuilder()
    
    # 创建任务信息
    task_info = TaskInfo(
        task_id=f"report_generation_{report_type}",
        task_name=f"生成{report_type}报告",
        task_type="report_generation",
        description=f"基于数据源生成{report_type}类型的智能报告",
        priority=MessagePriority.HIGH,
        requirements=[
            "分析数据源结构",
            "理解用户需求",
            "生成数据查询",
            "创建报告内容",
            "优化报告格式"
        ],
        expected_outputs=[
            "数据分析结果",
            "报告内容",
            "图表配置",
            "格式化输出"
        ]
    )
    
    # 创建占位符信息（基于用户需求）
    placeholders = []
    if user_requirements.get("metrics"):
        for metric in user_requirements["metrics"]:
            placeholder = PlaceholderInfo(
                name=f"metric_{metric}",
                type=PlaceholderType.METRIC_NAME,
                value=metric,
                description=f"业务指标: {metric}"
            )
            placeholders.append(placeholder)
    
    if user_requirements.get("time_range"):
        time_range = user_requirements["time_range"]
        placeholder = PlaceholderInfo(
            name="time_range",
            type=PlaceholderType.DATE_RANGE,
            value=time_range,
            description="时间范围过滤条件"
        )
        placeholders.append(placeholder)
    
    # 创建模板信息（如果提供了模板）
    templates = []
    if template_info:
        template = TemplateInfo(
            template_id=template_info.get("id", "default"),
            name=template_info.get("name", "默认报告模板"),
            template_type="report",
            content=template_info.get("content", ""),
            metadata=template_info.get("metadata", {})
        )
        templates.append(template)
    
    # 创建数据库架构信息
    database_schemas = []
    if data_source_info.get("schema"):
        schema_info = data_source_info["schema"]
        schema = DatabaseSchemaInfo(
            table_name=schema_info.get("table_name", "main_table"),
            columns=schema_info.get("columns", []),
            relationships=schema_info.get("relationships", []),
            metadata={
                "data_source_name": data_source_info.get("name"),
                "data_source_type": data_source_info.get("type")
            }
        )
        database_schemas.append(schema)
    
    # 构建上下文
    context = builder.build_context(
        task_info=task_info,
        placeholders=placeholders,
        templates=templates,
        database_schemas=database_schemas,
        context_type=ContextType.REPORT_GENERATION
    )
    
    return context.to_dict()


def create_sql_generation_context(
    query_description: str,
    table_schemas: List[Dict[str, Any]],
    query_parameters: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    创建SQL生成的Agent上下文
    
    Args:
        query_description: 查询描述
        table_schemas: 表结构信息
        query_parameters: 查询参数
    
    Returns:
        Dict: Agent上下文数据
    """
    builder = AgentContextBuilder()
    
    # 创建任务信息
    task_info = TaskInfo(
        task_id=f"sql_generation",
        task_name="生成SQL查询",
        task_type="sql_generation",
        description=query_description,
        priority=MessagePriority.NORMAL,
        requirements=[
            "理解查询需求",
            "分析表结构关系",
            "生成优化的SQL查询",
            "验证SQL语法"
        ],
        expected_outputs=[
            "SQL查询语句",
            "执行计划",
            "性能优化建议"
        ]
    )
    
    # 创建占位符信息（基于查询参数）
    placeholders = []
    if query_parameters:
        for param_name, param_value in query_parameters.items():
            # 推断占位符类型
            placeholder_type = PlaceholderType.TEMPLATE_VARIABLE
            if "table" in param_name.lower():
                placeholder_type = PlaceholderType.TABLE_NAME
            elif "column" in param_name.lower():
                placeholder_type = PlaceholderType.COLUMN_NAME
            elif "filter" in param_name.lower():
                placeholder_type = PlaceholderType.FILTER_CONDITION
            elif "date" in param_name.lower() or "time" in param_name.lower():
                placeholder_type = PlaceholderType.DATE_RANGE
            
            placeholder = PlaceholderInfo(
                name=param_name,
                type=placeholder_type,
                value=param_value,
                description=f"查询参数: {param_name}"
            )
            placeholders.append(placeholder)
    
    # 创建数据库架构信息
    database_schemas = []
    for schema_dict in table_schemas:
        schema = DatabaseSchemaInfo(
            table_name=schema_dict.get("table_name", ""),
            columns=schema_dict.get("columns", []),
            relationships=schema_dict.get("relationships", []),
            indexes=schema_dict.get("indexes", []),
            constraints=schema_dict.get("constraints", []),
            statistics=schema_dict.get("statistics", {}),
            sample_data=schema_dict.get("sample_data", [])
        )
        database_schemas.append(schema)
    
    # 构建上下文
    context = builder.build_context(
        task_info=task_info,
        placeholders=placeholders,
        database_schemas=database_schemas,
        context_type=ContextType.SQL_GENERATION
    )
    
    return context.to_dict()


def create_data_analysis_context(
    analysis_type: str,
    data_info: Dict[str, Any],
    analysis_parameters: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    创建数据分析的Agent上下文
    
    Args:
        analysis_type: 分析类型
        data_info: 数据信息
        analysis_parameters: 分析参数
    
    Returns:
        Dict: Agent上下文数据
    """
    builder = AgentContextBuilder()
    
    # 创建任务信息
    task_info = TaskInfo(
        task_id=f"data_analysis_{analysis_type}",
        task_name=f"数据分析 - {analysis_type}",
        task_type="data_analysis",
        description=f"执行{analysis_type}类型的数据分析",
        priority=MessagePriority.NORMAL,
        requirements=[
            "加载和预处理数据",
            "执行统计分析",
            "识别数据模式和趋势",
            "生成分析报告"
        ],
        expected_outputs=[
            "统计摘要",
            "数据质量报告",
            "分析结果",
            "可视化建议"
        ]
    )
    
    # 创建占位符信息（基于分析参数）
    placeholders = []
    if analysis_parameters:
        for param_name, param_value in analysis_parameters.items():
            placeholder = PlaceholderInfo(
                name=param_name,
                type=PlaceholderType.TEMPLATE_VARIABLE,
                value=param_value,
                description=f"分析参数: {param_name}"
            )
            placeholders.append(placeholder)
    
    # 创建数据库架构信息
    database_schemas = []
    if data_info.get("schema"):
        schema = DatabaseSchemaInfo(
            table_name=data_info["schema"].get("table_name", "analysis_data"),
            columns=data_info["schema"].get("columns", []),
            statistics=data_info.get("statistics", {}),
            sample_data=data_info.get("sample_data", []),
            metadata={
                "data_source": data_info.get("source", "unknown"),
                "analysis_type": analysis_type
            }
        )
        database_schemas.append(schema)
    
    # 构建上下文
    context = builder.build_context(
        task_info=task_info,
        placeholders=placeholders,
        database_schemas=database_schemas,
        context_type=ContextType.DATA_ANALYSIS
    )
    
    return context.to_dict()


def create_task_execution_context(
    task_name: str,
    task_description: str,
    task_data: Dict[str, Any],
    execution_options: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    创建任务执行的Agent上下文
    
    Args:
        task_name: 任务名称
        task_description: 任务描述
        task_data: 任务数据
        execution_options: 执行选项
    
    Returns:
        Dict: Agent上下文数据
    """
    builder = AgentContextBuilder()
    
    # 创建任务信息
    task_info = TaskInfo(
        task_id=f"task_execution_{task_name}",
        task_name=task_name,
        task_type="task_execution",
        description=task_description,
        priority=MessagePriority.NORMAL,
        requirements=[
            "解析任务数据",
            "执行任务逻辑",
            "处理执行结果",
            "返回任务输出"
        ],
        expected_outputs=[
            "任务执行结果",
            "执行状态",
            "错误信息（如有）"
        ],
        metadata=execution_options or {}
    )
    
    # 创建占位符信息（基于任务数据）
    placeholders = []
    for key, value in task_data.items():
        placeholder = PlaceholderInfo(
            name=key,
            type=PlaceholderType.TEMPLATE_VARIABLE,
            value=value,
            description=f"任务数据: {key}"
        )
        placeholders.append(placeholder)
    
    # 推断上下文类型
    context_type = ContextType.DATA_ANALYSIS  # 默认
    if "sql" in task_name.lower() or "query" in task_name.lower():
        context_type = ContextType.SQL_GENERATION
    elif "report" in task_name.lower():
        context_type = ContextType.REPORT_GENERATION
    elif "template" in task_name.lower():
        context_type = ContextType.TEMPLATE_PROCESSING
    
    # 构建上下文
    context = builder.build_context(
        task_info=task_info,
        placeholders=placeholders,
        context_type=context_type
    )
    
    return context.to_dict()