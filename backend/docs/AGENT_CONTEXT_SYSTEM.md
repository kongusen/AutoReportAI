# Agent 上下文构建系统

## 概述

基于你现有的 agents 架构，我设计了一套完整的上下文构建系统，用于根据占位符任务、模板信息、任务信息和数据库表结构信息构建智能化的 Agent 执行上下文。

## 系统架构

```text
├── context_builder.py          # 核心上下文构建器
├── context_examples.py         # 使用示例和演示
├── prompts/                    # Agent 专业化指令
│   ├── specialized_instructions.py
│   └── ...
├── tools/                      # 工具系统
│   ├── data/                   # 数据工具 (SQL, 分析, 报告)
│   ├── ai/                     # AI 工具 (推理)
│   └── system/                 # 系统工具 (文件, 搜索)
└── message_types.py            # 消息传递系统
```

## 核心组件

### 1. 数据类定义

```python
@dataclass
class PlaceholderInfo:
    """占位符信息 - 包含名称、类型、值、验证规则等"""
    name: str
    type: PlaceholderType  # TABLE_NAME, COLUMN_NAME, DATE_RANGE 等
    value: Any
    description: str
    required: bool = True
    default_value: Any = None
    validation_rules: Dict[str, Any] = field(default_factory=dict)

@dataclass  
class DatabaseSchemaInfo:
    """数据库表结构信息 - 包含列、关系、索引、统计信息等"""
    table_name: str
    columns: List[Dict[str, Any]]     # 列定义
    relationships: List[Dict[str, Any]]  # 外键关系
    indexes: List[Dict[str, Any]]     # 索引信息
    statistics: Dict[str, Any]        # 表统计信息
    sample_data: List[Dict[str, Any]] # 样本数据

@dataclass
class TemplateInfo:
    """模板信息 - 报告、SQL、邮件等模板"""
    template_id: str
    name: str
    template_type: str  # "report", "sql_query", "email", "dashboard"
    content: str        # 模板内容
    variables: List[str] # 变量占位符列表
    sections: List[str]  # 模板章节

@dataclass
class TaskInfo:
    """任务信息 - 任务描述、需求、约束等"""
    task_id: str
    task_name: str
    task_type: str
    description: str
    requirements: List[str]      # 任务需求
    constraints: List[str]       # 约束条件
    expected_outputs: List[str]  # 期望输出
    success_criteria: List[str]  # 成功标准
```

### 2. 上下文构建器

```python
class AgentContextBuilder:
    """智能 Agent 上下文构建器"""
    
    def build_context(
        self,
        task_info: TaskInfo,
        placeholders: List[PlaceholderInfo] = None,
        templates: List[TemplateInfo] = None, 
        database_schemas: List[DatabaseSchemaInfo] = None,
        context_type: ContextType = None
    ) -> AgentContext:
        """构建完整的 Agent 上下文"""
        
        # 1. 自动推断上下文类型
        if context_type is None:
            context_type = self._infer_context_type(task_info, placeholders, templates)
        
        # 2. 解析占位符
        resolved_placeholders = self._resolve_all_placeholders(placeholders, database_schemas)
        
        # 3. 处理模板
        processed_templates = self._process_all_templates(templates, resolved_placeholders)
        
        # 4. 构建查询上下文
        query_context = self._build_query_context(...)
        
        # 5. 配置执行选项和工具偏好
        execution_options = self._configure_execution_options(...)
        tool_preferences = self._configure_tool_preferences(...)
        
        return AgentContext(...)
```

### 3. 占位符解析

支持多种占位符类型的智能解析：

- **表名占位符**: 从数据库架构中匹配合适的表
- **列名占位符**: 根据数据类型和语义匹配列
- **日期范围占位符**: 解析时间范围表达式
- **指标占位符**: 识别数值型列作为分析指标
- **聚合函数占位符**: 选择合适的统计函数
- **模板变量占位符**: 处理模板中的变量替换

### 4. 模板处理

支持多种模板类型：

- **报告模板**: HTML/Markdown 格式的报告模板
- **SQL 模板**: 带参数化的 SQL 查询模板
- **邮件模板**: 邮件通知模板
- **仪表板模板**: JSON 格式的仪表板配置

## 使用示例

### 示例 1: 销售报告生成

```python
from context_builder import AgentContextBuilder, ContextType

builder = AgentContextBuilder()

# 1. 定义任务
task_info = TaskInfo(
    task_id="sales_report_001",
    task_name="生成月度销售报告",
    task_type="report_generation",
    description="基于销售数据表生成包含趋势分析和图表的月度销售报告",
    requirements=["包含销售趋势分析", "生成可视化图表", "计算同比增长率"]
)

# 2. 定义占位符
placeholders = [
    PlaceholderInfo(
        name="sales_table",
        type=PlaceholderType.TABLE_NAME,
        value="sales_orders"
    ),
    PlaceholderInfo(
        name="date_range", 
        type=PlaceholderType.DATE_RANGE,
        value={"start_date": "2024-01-01", "end_date": "2024-01-31"}
    ),
    PlaceholderInfo(
        name="primary_metric",
        type=PlaceholderType.METRIC_NAME, 
        value="total_amount"
    )
]

# 3. 定义数据库表结构
database_schemas = [
    DatabaseSchemaInfo(
        table_name="sales_orders",
        columns=[
            {"name": "order_id", "type": "bigint", "primary_key": True},
            {"name": "customer_id", "type": "bigint"},
            {"name": "order_date", "type": "date"},
            {"name": "total_amount", "type": "decimal(10,2)"},
            {"name": "status", "type": "varchar(20)"}
        ],
        relationships=[
            {
                "type": "foreign_key",
                "target_table": "customers", 
                "columns": [{"source": "customer_id", "target": "customer_id"}]
            }
        ]
    )
]

# 4. 定义报告模板
templates = [
    TemplateInfo(
        template_id="sales_report_template",
        name="月度销售报告模板",
        template_type="report", 
        content="""
        <h1>月度销售报告 - {date_range}</h1>
        <h2>关键指标</h2>
        <ul>
            <li>总销售额: {total_revenue}</li>
            <li>订单数量: {total_orders}</li>
        </ul>
        """,
        variables=["date_range", "total_revenue", "total_orders"]
    )
]

# 5. 构建上下文
context = builder.build_context(
    task_info=task_info,
    placeholders=placeholders,
    templates=templates,
    database_schemas=database_schemas,
    context_type=ContextType.REPORT_GENERATION
)

# 6. 创建 Agent 消息
message = builder.create_agent_message(
    context=context,
    target_agent="report_generation_agent"
)
```

### 示例 2: SQL 查询生成

```python
# 使用便利函数快速创建
context = create_simple_context(
    task_name="生成销售汇总查询",
    task_description="生成按产品类别和月份汇总的销售统计查询",
    placeholders_dict={
        "main_table": "sales_fact",
        "date_column": "sale_date", 
        "amount_column": "sale_amount",
        "aggregation_func": "SUM"
    },
    table_schemas=[
        {
            "table_name": "sales_fact",
            "columns": [
                {"name": "sale_id", "type": "bigint", "primary_key": True},
                {"name": "product_id", "type": "bigint"},
                {"name": "sale_date", "type": "date"},
                {"name": "sale_amount", "type": "decimal(12,2)"}
            ]
        }
    ],
    context_type=ContextType.SQL_GENERATION
)
```

## 智能功能

### 1. 自动上下文类型推断

系统会根据以下信息自动推断上下文类型：

- 任务类型和描述
- 占位符类型组合
- 模板类型
- 预期输出类型

```python
def _infer_context_type(self, task_info, placeholders, templates):
    # 基于任务类型推断
    if "sql" in task_type or "query" in task_type:
        return ContextType.SQL_GENERATION
    elif "report" in task_type or "dashboard" in task_type:
        return ContextType.REPORT_GENERATION
    # ... 更多推断逻辑
```

### 2. 智能占位符解析

```python
def _resolve_table_placeholder(self, placeholder, database_schemas):
    # 从数据库架构中查找匹配的表
    for schema in database_schemas:
        if placeholder.name.lower() in schema.table_name.lower():
            return schema.table_name
    return database_schemas[0].table_name  # 默认值
```

### 3. 工具偏好配置

根据上下文类型自动配置最适合的工具：

```python
def _configure_tool_preferences(self, context):
    if context.context_type == ContextType.SQL_GENERATION:
        return {
            "preferred_tools": ["sql_generator", "sql_executor"],
            "execution_order": ["sql_generator", "sql_executor"],
            "tool_parameters": {
                "sql_generator": {"optimization_level": "standard"},
                "sql_executor": {"execute_mode": "read_only"}
            }
        }
    # ... 其他上下文类型的配置
```

## 与现有系统集成

### 1. 消息系统集成

上下文构建器生成的消息与你现有的 `AgentMessage` 系统完全兼容：

```python
# 生成的消息可以直接发送给协调器
coordinator = AgentCoordinator()
await coordinator.start()

message = builder.create_agent_message(context, "target_agent")
await coordinator.message_bus.send_message(message)
```

### 2. 工具系统集成

构建的上下文包含工具偏好和参数，可以直接用于工具调用：

```python
# 上下文中的工具偏好可以指导工具选择
preferred_tools = context.tool_preferences["preferred_tools"]
tool_params = context.tool_preferences["tool_parameters"]
```

### 3. 专业化指令集成

上下文类型可以用来选择合适的专业化指令：

```python
from prompts.specialized_instructions import get_specialized_instructions

instructions = get_specialized_instructions(context.context_type.value)
```

## 扩展性

### 1. 添加新的占位符类型

```python
class PlaceholderType(Enum):
    # 现有类型...
    NEW_PLACEHOLDER_TYPE = "new_type"

# 在构建器中添加解析器
def _resolve_new_placeholder_type(self, placeholder, database_schemas):
    # 自定义解析逻辑
    return resolved_value
```

### 2. 添加新的模板类型

```python
def _process_new_template_type(self, template, resolved_placeholders):
    # 自定义模板处理逻辑  
    return processed_content
```

### 3. 添加新的上下文类型

```python
class ContextType(Enum):
    # 现有类型...
    NEW_CONTEXT_TYPE = "new_context"

# 在构建器中添加配置
def _configure_execution_options(self, context):
    if context.context_type == ContextType.NEW_CONTEXT_TYPE:
        return {...}  # 自定义配置
```

## 最佳实践

### 1. 占位符设计

- 使用描述性名称
- 提供默认值和验证规则
- 明确标识必需和可选占位符

### 2. 模板设计

- 保持模板简洁和可读
- 使用一致的变量命名约定
- 提供模板文档和使用示例

### 3. 数据库架构信息

- 包含完整的列类型信息
- 提供表关系和约束
- 包含统计信息以优化查询

### 4. 任务信息

- 提供清晰的任务描述
- 明确需求和成功标准
- 包含相关约束条件

## 性能考虑

- 上下文构建是轻量级操作，通常在毫秒级完成
- 占位符解析使用缓存机制提高性能
- 模板处理支持增量更新
- 数据库架构信息可以缓存复用

## 总结

这套上下文构建系统为你的 agents 架构提供了：

1. **智能化** - 自动推断上下文类型和工具偏好
2. **灵活性** - 支持多种占位符和模板类型
3. **扩展性** - 易于添加新的类型和处理器
4. **集成性** - 与现有消息和工具系统无缝集成
5. **实用性** - 提供丰富的示例和便利函数

通过这个系统，你可以轻松地为任何占位符任务构建完整的 Agent 执行上下文，让 Agent 能够获得执行任务所需的所有信息和配置。