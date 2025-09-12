"""
Agent 上下文构建器
==================

基于占位符任务构建智能化的 Agent 上下文输入系统。
支持数据占位符、模板信息、任务信息和数据库表结构信息的自动集成。
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field, asdict
from enum import Enum

from ..core.message_types import AgentMessage, MessageType, create_task_request, MessagePriority


class ContextType(Enum):
    """上下文类型枚举"""
    DATA_ANALYSIS = "data_analysis"
    REPORT_GENERATION = "report_generation" 
    SQL_GENERATION = "sql_generation"
    BUSINESS_INTELLIGENCE = "business_intelligence"
    DATA_EXTRACTION = "data_extraction"
    TEMPLATE_PROCESSING = "template_processing"
    TEMPLATE_FILLING = "template_filling"  # 新增：模板填充


class PlaceholderType(Enum):
    """占位符类型枚举"""
    TABLE_NAME = "table_name"
    COLUMN_NAME = "column_name"
    FILTER_CONDITION = "filter_condition"
    DATE_RANGE = "date_range"
    METRIC_NAME = "metric_name"
    AGGREGATION_FUNCTION = "aggregation_function"
    TEMPLATE_VARIABLE = "template_variable"
    REPORT_SECTION = "report_section"
    CHART_TYPE = "chart_type"
    # 新增模板填充相关类型
    FILL_MODE = "fill_mode"
    TEMPLATE_TYPE = "template_type"


@dataclass
class PlaceholderInfo:
    """占位符信息数据类"""
    name: str
    type: PlaceholderType
    value: Any = None
    description: str = ""
    required: bool = True
    default_value: Any = None
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DatabaseSchemaInfo:
    """数据库表结构信息"""
    table_name: str
    columns: List[Dict[str, Any]] = field(default_factory=list)  # [{name, type, nullable, primary_key, etc}]
    relationships: List[Dict[str, Any]] = field(default_factory=list)  # [{type, target_table, columns}]
    indexes: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)  # {row_count, avg_row_length, etc}
    sample_data: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TemplateInfo:
    """模板信息数据类"""
    template_id: str
    name: str
    template_type: str  # "report", "email", "dashboard", "sql_query"
    content: str
    variables: List[str] = field(default_factory=list)  # 模板中的变量占位符
    sections: List[str] = field(default_factory=list)  # 模板章节
    format_options: Dict[str, Any] = field(default_factory=dict)
    validation_schema: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskInfo:
    """任务信息数据类"""
    task_id: str
    task_name: str
    task_type: str
    description: str
    priority: MessagePriority = MessagePriority.NORMAL
    requirements: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    expected_outputs: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: Optional[int] = None  # 秒
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentContext:
    """Agent 执行上下文数据类"""
    context_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    context_type: ContextType = ContextType.DATA_ANALYSIS
    task_info: TaskInfo = None
    placeholders: List[PlaceholderInfo] = field(default_factory=list)
    templates: List[TemplateInfo] = field(default_factory=list)
    database_schemas: List[DatabaseSchemaInfo] = field(default_factory=list)
    
    # 解析和映射的数据
    resolved_placeholders: Dict[str, Any] = field(default_factory=dict)
    processed_templates: Dict[str, str] = field(default_factory=dict)
    query_context: Dict[str, Any] = field(default_factory=dict)
    
    # 执行配置
    execution_options: Dict[str, Any] = field(default_factory=dict)
    tool_preferences: Dict[str, Any] = field(default_factory=dict)
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)

    def to_agent_message_payload(self) -> Dict[str, Any]:
        """转换为 AgentMessage 载荷格式"""
        return {
            "context_id": self.context_id,
            "context_type": self.context_type.value,
            "task": asdict(self.task_info) if self.task_info else None,
            "placeholders": [asdict(p) for p in self.placeholders],
            "templates": [asdict(t) for t in self.templates],
            "database_schemas": [asdict(db) for db in self.database_schemas],
            "resolved_data": {
                "placeholders": self.resolved_placeholders,
                "templates": self.processed_templates,
                "query_context": self.query_context
            },
            "execution_options": self.execution_options,
            "tool_preferences": self.tool_preferences,
            "metadata": self.metadata
        }


class AgentContextBuilder:
    """
    智能 Agent 上下文构建器
    
    根据占位符任务、模板信息、数据库结构等构建完整的 Agent 执行上下文
    """
    
    def __init__(self):
        self.placeholder_resolvers = {
            PlaceholderType.TABLE_NAME: self._resolve_table_placeholder,
            PlaceholderType.COLUMN_NAME: self._resolve_column_placeholder,
            PlaceholderType.FILTER_CONDITION: self._resolve_filter_placeholder,
            PlaceholderType.DATE_RANGE: self._resolve_date_range_placeholder,
            PlaceholderType.METRIC_NAME: self._resolve_metric_placeholder,
            PlaceholderType.AGGREGATION_FUNCTION: self._resolve_aggregation_placeholder,
            PlaceholderType.TEMPLATE_VARIABLE: self._resolve_template_variable,
        }
        
        self.template_processors = {
            "report": self._process_report_template,
            "sql_query": self._process_sql_template,
            "email": self._process_email_template,
            "dashboard": self._process_dashboard_template,
        }
    
    def build_context(
        self,
        task_info: TaskInfo,
        placeholders: List[PlaceholderInfo] = None,
        templates: List[TemplateInfo] = None,
        database_schemas: List[DatabaseSchemaInfo] = None,
        context_type: ContextType = None
    ) -> AgentContext:
        """
        构建完整的 Agent 上下文
        
        Args:
            task_info: 任务信息
            placeholders: 占位符列表
            templates: 模板信息列表
            database_schemas: 数据库表结构列表
            context_type: 上下文类型（自动推断如果为None）
        
        Returns:
            AgentContext: 完整的 Agent 执行上下文
        """
        
        # 自动推断上下文类型
        if context_type is None:
            context_type = self._infer_context_type(task_info, placeholders, templates)
        
        # 创建基础上下文
        context = AgentContext(
            context_type=context_type,
            task_info=task_info,
            placeholders=placeholders or [],
            templates=templates or [],
            database_schemas=database_schemas or []
        )
        
        # 解析占位符
        context.resolved_placeholders = self._resolve_all_placeholders(
            context.placeholders, context.database_schemas
        )
        
        # 处理模板
        context.processed_templates = self._process_all_templates(
            context.templates, context.resolved_placeholders
        )
        
        # 构建查询上下文
        context.query_context = self._build_query_context(context)
        
        # 配置执行选项
        context.execution_options = self._configure_execution_options(context)
        
        # 配置工具偏好
        context.tool_preferences = self._configure_tool_preferences(context)
        
        return context
    
    def create_agent_message(
        self, 
        context: AgentContext,
        target_agent: str,
        from_agent: str = "context_builder"
    ) -> AgentMessage:
        """
        根据上下文创建 AgentMessage
        
        Args:
            context: Agent 上下文
            target_agent: 目标 Agent ID
            from_agent: 发送方 Agent ID
        
        Returns:
            AgentMessage: 准备好的 Agent 消息
        """
        return create_task_request(
            from_agent=from_agent,
            to_agent=target_agent,
            task_data=context.to_agent_message_payload(),
            priority=context.task_info.priority if context.task_info else MessagePriority.NORMAL
        )
    
    def _infer_context_type(
        self, 
        task_info: TaskInfo,
        placeholders: List[PlaceholderInfo] = None,
        templates: List[TemplateInfo] = None
    ) -> ContextType:
        """根据任务信息推断上下文类型"""
        
        task_type = task_info.task_type.lower() if task_info else ""
        task_desc = (task_info.description or "").lower() if task_info else ""
        
        # 基于任务类型推断模板填充
        if "template" in task_type and "fill" in task_type:
            return ContextType.TEMPLATE_FILLING
        elif "placeholder" in task_type and "fill" in task_type:
            return ContextType.TEMPLATE_FILLING
        
        # 基于任务描述推断模板填充
        template_fill_keywords = [
            "填充模板", "fill template", "template filling", 
            "占位符填充", "placeholder filling", "补充模板",
            "模板数据填充", "template data fill"
        ]
        if any(keyword in task_desc for keyword in template_fill_keywords):
            return ContextType.TEMPLATE_FILLING
        
        # 基于占位符推断模板填充
        if placeholders:
            placeholder_types = {p.type for p in placeholders}
            # 检查是否包含模板填充相关的占位符类型
            template_fill_types = {PlaceholderType.FILL_MODE, PlaceholderType.TEMPLATE_TYPE}
            if template_fill_types.intersection(placeholder_types):
                return ContextType.TEMPLATE_FILLING
            
            # 检查其他类型
            if PlaceholderType.TABLE_NAME in placeholder_types:
                return ContextType.SQL_GENERATION
            elif PlaceholderType.CHART_TYPE in placeholder_types:
                return ContextType.REPORT_GENERATION
        
        # 基于模板推断
        if templates:
            for template in templates:
                # 如果模板包含需要填充的内容，优先选择模板填充
                if any(pattern in template.content for pattern in ['{', '{{', '<', '[', '%', '${']):  
                    return ContextType.TEMPLATE_FILLING
                elif template.template_type == "report":
                    return ContextType.REPORT_GENERATION
                elif template.template_type == "sql_query":
                    return ContextType.SQL_GENERATION
        
        # 基于任务类型推断
        if "sql" in task_type or "query" in task_type:
            return ContextType.SQL_GENERATION
        elif "report" in task_type or "dashboard" in task_type:
            return ContextType.REPORT_GENERATION
        elif "analysis" in task_type or "analytics" in task_type:
            return ContextType.DATA_ANALYSIS
        elif "business" in task_type or "intelligence" in task_type:
            return ContextType.BUSINESS_INTELLIGENCE
        
        # 基于任务描述推断
        if "generate sql" in task_desc or "create query" in task_desc:
            return ContextType.SQL_GENERATION
        elif "create report" in task_desc or "generate report" in task_desc:
            return ContextType.REPORT_GENERATION
        elif "analyze data" in task_desc or "data analysis" in task_desc:
            return ContextType.DATA_ANALYSIS
        
        # 默认返回数据分析
        return ContextType.DATA_ANALYSIS
    
    def _resolve_all_placeholders(
        self, 
        placeholders: List[PlaceholderInfo],
        database_schemas: List[DatabaseSchemaInfo]
    ) -> Dict[str, Any]:
        """解析所有占位符"""
        resolved = {}
        
        for placeholder in placeholders:
            if placeholder.type in self.placeholder_resolvers:
                resolver = self.placeholder_resolvers[placeholder.type]
                try:
                    resolved[placeholder.name] = resolver(placeholder, database_schemas)
                except Exception as e:
                    # 使用默认值或留空
                    resolved[placeholder.name] = placeholder.default_value
                    print(f"Warning: Failed to resolve placeholder {placeholder.name}: {e}")
            else:
                # 直接使用值或默认值
                resolved[placeholder.name] = placeholder.value or placeholder.default_value
        
        return resolved
    
    def _resolve_table_placeholder(
        self, 
        placeholder: PlaceholderInfo, 
        database_schemas: List[DatabaseSchemaInfo]
    ) -> str:
        """解析表名占位符"""
        if placeholder.value:
            return placeholder.value
        
        # 从数据库架构中查找匹配的表
        if database_schemas:
            # 简单匹配逻辑 - 在实际应用中可以更复杂
            for schema in database_schemas:
                if placeholder.name.lower() in schema.table_name.lower():
                    return schema.table_name
            
            # 返回第一个表作为默认值
            return database_schemas[0].table_name
        
        return placeholder.default_value or "table_name"
    
    def _resolve_column_placeholder(
        self, 
        placeholder: PlaceholderInfo, 
        database_schemas: List[DatabaseSchemaInfo]
    ) -> str:
        """解析列名占位符"""
        if placeholder.value:
            return placeholder.value
        
        # 从数据库架构中查找匹配的列
        for schema in database_schemas:
            for column in schema.columns:
                if placeholder.name.lower() in column.get('name', '').lower():
                    return column['name']
        
        return placeholder.default_value or "column_name"
    
    def _resolve_filter_placeholder(
        self, 
        placeholder: PlaceholderInfo, 
        database_schemas: List[DatabaseSchemaInfo]
    ) -> str:
        """解析过滤条件占位符"""
        if placeholder.value:
            return placeholder.value
        
        # 构建基本的 WHERE 子句
        return placeholder.default_value or "1=1"
    
    def _resolve_date_range_placeholder(
        self, 
        placeholder: PlaceholderInfo, 
        database_schemas: List[DatabaseSchemaInfo]
    ) -> Dict[str, str]:
        """解析日期范围占位符"""
        if placeholder.value:
            return placeholder.value
        
        # 默认日期范围
        return placeholder.default_value or {
            "start_date": "2024-01-01",
            "end_date": "2024-12-31"
        }
    
    def _resolve_metric_placeholder(
        self, 
        placeholder: PlaceholderInfo, 
        database_schemas: List[DatabaseSchemaInfo]
    ) -> str:
        """解析指标占位符"""
        if placeholder.value:
            return placeholder.value
        
        # 从数据库架构中查找数值列作为指标
        for schema in database_schemas:
            for column in schema.columns:
                column_type = column.get('type', '').lower()
                if any(t in column_type for t in ['int', 'float', 'decimal', 'numeric']):
                    return column['name']
        
        return placeholder.default_value or "metric_value"
    
    def _resolve_aggregation_placeholder(
        self, 
        placeholder: PlaceholderInfo, 
        database_schemas: List[DatabaseSchemaInfo]
    ) -> str:
        """解析聚合函数占位符"""
        if placeholder.value:
            return placeholder.value
        
        return placeholder.default_value or "SUM"
    
    def _resolve_template_variable(
        self, 
        placeholder: PlaceholderInfo, 
        database_schemas: List[DatabaseSchemaInfo]
    ) -> str:
        """解析模板变量占位符"""
        if placeholder.value:
            return placeholder.value
        
        return placeholder.default_value or ""
    
    def _process_all_templates(
        self, 
        templates: List[TemplateInfo],
        resolved_placeholders: Dict[str, Any]
    ) -> Dict[str, str]:
        """处理所有模板"""
        processed = {}
        
        for template in templates:
            if template.template_type in self.template_processors:
                processor = self.template_processors[template.template_type]
                try:
                    processed[template.template_id] = processor(template, resolved_placeholders)
                except Exception as e:
                    print(f"Warning: Failed to process template {template.template_id}: {e}")
                    processed[template.template_id] = template.content
            else:
                # 基本模板变量替换
                processed[template.template_id] = self._basic_template_processing(
                    template, resolved_placeholders
                )
        
        return processed
    
    def _process_report_template(
        self, 
        template: TemplateInfo, 
        resolved_placeholders: Dict[str, Any]
    ) -> str:
        """处理报告模板"""
        content = template.content
        
        # 替换占位符变量
        for var_name, var_value in resolved_placeholders.items():
            placeholder = f"{{{var_name}}}"
            content = content.replace(placeholder, str(var_value))
        
        return content
    
    def _process_sql_template(
        self, 
        template: TemplateInfo, 
        resolved_placeholders: Dict[str, Any]
    ) -> str:
        """处理SQL查询模板"""
        content = template.content
        
        # 替换SQL占位符
        for var_name, var_value in resolved_placeholders.items():
            placeholder = f"{{{var_name}}}"
            if isinstance(var_value, dict) and "start_date" in var_value:
                # 日期范围处理
                date_condition = f"date_column BETWEEN '{var_value['start_date']}' AND '{var_value['end_date']}'"
                content = content.replace(placeholder, date_condition)
            else:
                content = content.replace(placeholder, str(var_value))
        
        return content
    
    def _process_email_template(
        self, 
        template: TemplateInfo, 
        resolved_placeholders: Dict[str, Any]
    ) -> str:
        """处理邮件模板"""
        return self._basic_template_processing(template, resolved_placeholders)
    
    def _process_dashboard_template(
        self, 
        template: TemplateInfo, 
        resolved_placeholders: Dict[str, Any]
    ) -> str:
        """处理仪表板模板"""
        return self._basic_template_processing(template, resolved_placeholders)
    
    def _basic_template_processing(
        self, 
        template: TemplateInfo, 
        resolved_placeholders: Dict[str, Any]
    ) -> str:
        """基本模板处理（变量替换）"""
        content = template.content
        
        for var_name, var_value in resolved_placeholders.items():
            placeholder = f"{{{var_name}}}"
            content = content.replace(placeholder, str(var_value))
        
        return content
    
    def _build_query_context(self, context: AgentContext) -> Dict[str, Any]:
        """构建查询上下文"""
        query_context = {
            "available_tables": [],
            "available_columns": {},
            "relationships": [],
            "suggested_joins": [],
            "performance_hints": []
        }
        
        # 从数据库架构中提取查询上下文
        for schema in context.database_schemas:
            query_context["available_tables"].append(schema.table_name)
            # 处理不同类型的列数据格式
            if schema.columns and isinstance(schema.columns[0], dict):
                # 字典格式的列信息
                query_context["available_columns"][schema.table_name] = [
                    col.get("name", f"column_{i}") for i, col in enumerate(schema.columns)
                ]
            elif schema.columns and isinstance(schema.columns[0], str):
                # 字符串格式的列名
                query_context["available_columns"][schema.table_name] = schema.columns
            else:
                # 其他格式或空列
                query_context["available_columns"][schema.table_name] = []
            query_context["relationships"].extend(schema.relationships)
        
        # 根据占位符添加查询提示
        for placeholder in context.placeholders:
            if placeholder.type == PlaceholderType.TABLE_NAME:
                table_name = context.resolved_placeholders.get(placeholder.name)
                if table_name:
                    query_context["performance_hints"].append(
                        f"Consider adding indexes on frequently queried columns in {table_name}"
                    )
        
        return query_context
    
    def _configure_execution_options(self, context: AgentContext) -> Dict[str, Any]:
        """配置执行选项"""
        options = {
            "timeout_seconds": 300,
            "max_retries": 3,
            "enable_streaming": True,
            "enable_caching": True,
            "enable_performance_monitoring": True
        }
        
        # 根据上下文类型调整选项
        if context.context_type == ContextType.SQL_GENERATION:
            options.update({
                "sql_optimization_level": "standard",
                "include_execution_plan": True,
                "validate_syntax": True
            })
        elif context.context_type == ContextType.REPORT_GENERATION:
            options.update({
                "include_visualizations": True,
                "output_format": "html",
                "enable_interactive_charts": True
            })
        elif context.context_type == ContextType.DATA_ANALYSIS:
            options.update({
                "statistical_confidence": 0.95,
                "include_correlation_analysis": True,
                "detect_outliers": True
            })
        
        return options
    
    def _configure_tool_preferences(self, context: AgentContext) -> Dict[str, Any]:
        """配置工具偏好"""
        preferences = {
            "preferred_tools": [],
            "tool_parameters": {},
            "execution_order": []
        }
        
        # 根据上下文类型配置工具偏好
        if context.context_type == ContextType.TEMPLATE_FILLING:
            preferences["preferred_tools"] = ["template_fill_tool"]
            preferences["execution_order"] = ["template_fill_tool"]
            preferences["tool_parameters"] = {
                "template_fill_tool": {
                    "fill_mode": "smart",
                    "add_descriptions": True,
                    "preserve_formatting": True,
                    "template_type": "word"
                }
            }
        elif context.context_type == ContextType.SQL_GENERATION:
            preferences["preferred_tools"] = ["sql_generator", "sql_executor"]
            preferences["execution_order"] = ["sql_generator", "sql_executor"]
            preferences["tool_parameters"] = {
                "sql_generator": {
                    "optimization_level": "standard",
                    "include_performance_hints": True
                },
                "sql_executor": {
                    "execute_mode": "read_only",
                    "limit_rows": 1000
                }
            }
        elif context.context_type == ContextType.DATA_ANALYSIS:
            preferences["preferred_tools"] = ["data_analyzer", "reasoning_tool"]
            preferences["execution_order"] = ["data_analyzer", "reasoning_tool"]
        elif context.context_type == ContextType.REPORT_GENERATION:
            preferences["preferred_tools"] = ["data_analyzer", "report_generator"]
            preferences["execution_order"] = ["data_analyzer", "report_generator"]
        
        return preferences


# 便利函数
def create_simple_context(
    task_name: str,
    task_description: str,
    placeholders_dict: Dict[str, Any] = None,
    table_schemas: List[Dict[str, Any]] = None,
    context_type: ContextType = None
) -> AgentContext:
    """
    快速创建简单的 Agent 上下文
    
    Args:
        task_name: 任务名称
        task_description: 任务描述
        placeholders_dict: 占位符字典 {name: value}
        table_schemas: 表结构列表
        context_type: 上下文类型
    
    Returns:
        AgentContext: 构建好的上下文
    """
    builder = AgentContextBuilder()
    
    # 创建任务信息
    task_info = TaskInfo(
        task_id=str(uuid.uuid4()),
        task_name=task_name,
        task_type="general",
        description=task_description
    )
    
    # 创建占位符信息
    placeholders = []
    if placeholders_dict:
        for name, value in placeholders_dict.items():
            placeholder = PlaceholderInfo(
                name=name,
                type=PlaceholderType.TEMPLATE_VARIABLE,
                value=value
            )
            placeholders.append(placeholder)
    
    # 创建数据库架构信息
    database_schemas = []
    if table_schemas:
        for schema_dict in table_schemas:
            schema = DatabaseSchemaInfo(
                table_name=schema_dict.get("table_name", ""),
                columns=schema_dict.get("columns", []),
                relationships=schema_dict.get("relationships", [])
            )
            database_schemas.append(schema)
    
    return builder.build_context(
        task_info=task_info,
        placeholders=placeholders,
        database_schemas=database_schemas,
        context_type=context_type
    )


__all__ = [
    "ContextType", "PlaceholderType", "PlaceholderInfo", "DatabaseSchemaInfo",
    "TemplateInfo", "TaskInfo", "AgentContext", "AgentContextBuilder",
    "create_simple_context"
]