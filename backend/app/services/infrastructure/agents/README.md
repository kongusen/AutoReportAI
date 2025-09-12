# 新一代智能 Agents 系统

## 📁 整理后的目录结构

```
agents/
├── README.md                    # 本文档
├── __init__.py                  # 主入口，导出所有核心组件和便捷函数
├── run_example.py               # 完整系统运行示例
│
├── core/                        # 🔧 核心Agent框架
│   ├── __init__.py              # 核心组件导出
│   ├── main.py                  # AgentCoordinator - 主协调器
│   ├── message_types.py         # 消息类型和消息处理
│   ├── message_bus.py           # 消息总线和路由
│   ├── memory_manager.py        # 内存管理和缓存
│   ├── progress_aggregator.py   # 进度聚合和ANR检测
│   ├── streaming_parser.py      # 流式消息解析
│   └── error_formatter.py       # 错误格式化和处理
│
├── context/                     # 🎯 上下文构建系统
│   ├── __init__.py              # 上下文系统导出和便捷函数
│   ├── context_builder.py       # 核心上下文构建器
│   └── context_examples.py      # 详细使用示例和演示
│
├── tools/                       # 🛠️ 工具系统
│   ├── __init__.py              # 工具系统导出
│   ├── core/                    # 工具核心框架
│   │   ├── base.py              # 基础工具类和接口
│   │   ├── executor.py          # 工具执行器
│   │   ├── permissions.py       # 权限管理
│   │   └── registry.py          # 工具注册表
│   ├── data/                    # 数据处理工具
│   │   ├── sql_tool.py          # SQL生成和执行
│   │   ├── analysis_tool.py     # 数据分析工具
│   │   └── report_tool.py       # 报告生成工具
│   ├── ai/                      # AI推理工具
│   │   └── reasoning_tool.py    # 逻辑推理工具
│   └── system/                  # 系统操作工具
│       ├── bash_tool.py         # 命令执行工具
│       ├── file_tool.py         # 文件操作工具
│       └── search_tool.py       # 搜索工具
│
└── prompts/                     # 📝 专业化指令系统
    ├── __init__.py              # 指令系统导出
    ├── core_instructions.py     # 核心Agent指令
    ├── specialized_instructions.py  # 专业化Agent指令
    ├── tool_specific_prompts.py     # 工具特定指令
    └── error_recovery_prompts.py    # 错误恢复指令
```

## 🏗️ 模块化架构设计

### 1. 核心层 (core/)
提供Agent系统的基础框架：

```python
from agents.core import (
    AgentCoordinator,          # 主协调器
    MessageBus,               # 消息总线
    MemoryManager,            # 内存管理
    ProgressAggregator,       # 进度聚合
    StreamingMessageParser,   # 流式解析
    ErrorFormatter            # 错误处理
)
```

### 2. 上下文层 (context/)
智能上下文构建和管理：

```python
from agents.context import (
    AgentContextBuilder,      # 核心构建器
    ContextType,             # 上下文类型枚举
    PlaceholderInfo,         # 占位符信息
    DatabaseSchemaInfo,      # 数据库架构
    create_simple_context,   # 便捷函数
    ContextExamples          # 使用示例
)

# 专业化上下文创建函数
from agents.context import (
    create_data_analysis_context,
    create_sql_generation_context,
    create_report_generation_context,
    create_business_intelligence_context
)
```

### 3. 工具层 (tools/)
丰富的工具生态系统：

```python
from agents.tools import (
    AgentTool,               # 基础工具类
    StreamingAgentTool,      # 流式工具类
    SQLGeneratorTool,        # SQL生成工具
    DataAnalysisTool,        # 数据分析工具
    ReportGeneratorTool,     # 报告生成工具
    ReasoningTool           # AI推理工具
)
```

### 4. 指令层 (prompts/)
专业化指令和提示词系统：

```python
from agents.prompts import (
    get_specialized_instructions,
    PromptManager,
    DataAnalysisAgentInstructions,
    BusinessIntelligenceAgentInstructions
)
```

## 🚀 快速开始

### 简单使用
```python
from app.services.infrastructure.agents import execute_agent_task

# 执行数据分析任务
result = await execute_agent_task(
    task_name="销售数据分析",
    task_description="分析过去30天的销售趋势和模式",
    context_data={
        "placeholders": {
            "data_source": "sales_orders",
            "time_range": "last_30_days",
            "metrics": ["revenue", "order_count", "avg_order_value"]
        }
    }
)

print(f"分析结果: {result['success']}")
print(f"使用的Agent: {result['target_agent']}")
```

### 专业化上下文使用
```python
from agents.context import (
    create_data_analysis_context,
    create_sql_generation_context,
    create_report_generation_context
)

# 数据分析上下文
analysis_context = create_data_analysis_context(
    task_name="客户行为分析",
    data_source="customer_events",
    metrics=["conversion_rate", "retention_rate", "lifetime_value"],
    time_range={"start": "2024-01-01", "end": "2024-03-31"}
)

# SQL生成上下文  
sql_context = create_sql_generation_context(
    task_name="销售汇总查询",
    table_names=["sales", "products", "customers"],
    columns=["product_name", "total_sales", "customer_count"],
    conditions={"date": ">=2024-01-01", "status": "completed"}
)

# 报告生成上下文
report_context = create_report_generation_context(
    task_name="月度业务报告",
    data_sources=["sales_summary", "customer_metrics"],
    report_type="executive",
    include_charts=True
)
```

### 完整系统集成
```python
from agents import (
    get_agent_coordinator,
    get_context_builder
)

async def main():
    # 获取系统组件
    coordinator = await get_agent_coordinator()
    builder = get_context_builder()
    
    # 创建自定义上下文
    context = builder.build_context(
        task_info=task_info,
        placeholders=placeholders,
        templates=templates,
        database_schemas=schemas
    )
    
    # 创建消息并执行
    message = builder.create_agent_message(context, "target_agent")
    result = await coordinator.execute_task(...)
    
    return result
```

## 💡 系统特性

### 🎯 智能上下文构建
- **占位符解析**: 自动解析表名、列名、日期范围等
- **模板处理**: 支持报告、SQL、邮件模板自动变量替换
- **类型推断**: 根据任务特征自动选择最佳Agent
- **架构集成**: 利用数据库表结构进行智能匹配

### 🔄 六阶段编排模式
1. **验证阶段**: 并行验证权限和数据源
2. **只读并行**: 并行执行数据发现和分析
3. **写入顺序**: 顺序执行数据修改操作
4. **压缩阶段**: 数据压缩和优化
5. **推理阶段**: AI推理和洞察生成  
6. **合成阶段**: 结果合成和报告生成

### 🛠️ 丰富工具生态
- **数据工具**: SQL生成/执行、统计分析、数据可视化
- **AI工具**: 逻辑推理、模式识别、内容生成
- **系统工具**: 文件操作、命令执行、搜索功能

### 📝 专业化指令系统
- **角色特化**: 数据分析师、系统管理员、BI专家等
- **上下文感知**: 根据用户角色和任务自动调整指令
- **工具集成**: 与具体工具的使用指南深度集成

## 🎨 使用场景

### 场景1: 自动化数据分析
```python
# 客户流失分析
context = create_data_analysis_context(
    task_name="客户流失预警分析",
    data_source="customer_activities", 
    metrics=["last_activity_date", "purchase_frequency", "engagement_score"],
    time_range={"months_back": 6}
)

result = await execute_agent_task(
    task_name="客户流失分析",
    task_description="识别高风险流失客户并生成预警报告",
    context_data=context.to_dict()
)
```

### 场景2: 智能报告生成
```python
# 月度业务报告
context = create_report_generation_context(
    task_name="Q1业务总结报告",
    data_sources=["sales_summary", "marketing_metrics", "customer_feedback"],
    report_type="executive",
    include_charts=True
)

# 自动选择最佳模板和可视化方案
result = await execute_agent_task(
    task_name="Q1业务报告生成",
    task_description="生成包含关键指标、趋势分析和业务建议的高管报告",
    context_data=context.to_dict()
)
```

### 场景3: 动态SQL生成
```python
# 复杂业务查询
context = create_sql_generation_context(
    task_name="多维度销售分析查询",
    table_names=["orders", "products", "customers", "regions"],
    columns=["region_name", "product_category", "total_revenue", "order_count"],
    conditions={
        "date_range": "2024-Q1",
        "status": "completed", 
        "min_order_value": 100
    }
)

result = await execute_agent_task(
    task_name="生成销售分析SQL",
    task_description="生成多表关联的销售数据分析查询，包含地区和产品维度",
    context_data=context.to_dict()
)
```

## 🔧 扩展和定制

### 添加新的上下文类型
```python
# 1. 扩展ContextType枚举
class ContextType(Enum):
    DATA_ANALYSIS = "data_analysis"
    REPORT_GENERATION = "report_generation"
    # 新增类型
    PREDICTIVE_ANALYTICS = "predictive_analytics"
    
# 2. 创建专用便捷函数
def create_predictive_analytics_context(
    task_name: str,
    historical_data: str,
    prediction_target: str,
    model_type: str = "regression"
) -> AgentContext:
    placeholders = {
        'historical_data': historical_data,
        'prediction_target': prediction_target, 
        'model_type': model_type
    }
    
    return create_simple_context(
        task_name=task_name,
        task_description=f"预测分析: {prediction_target}",
        placeholders_dict=placeholders,
        context_type=ContextType.PREDICTIVE_ANALYTICS
    )
```

### 添加新的工具
```python
# 1. 继承基础工具类
class PredictionTool(StreamingAgentTool):
    def __init__(self):
        definition = create_tool_definition(
            name="prediction_tool",
            description="机器学习预测工具",
            category=ToolCategory.ANALYSIS,
            priority=ToolPriority.HIGH
        )
        super().__init__(definition)
    
    async def execute(self, input_data, context):
        # 实现预测逻辑
        pass

# 2. 注册到工具系统
register_tool(PredictionTool())
```

## 📊 性能监控

### 系统健康检查
```python
# 获取详细系统状态
coordinator = await get_agent_coordinator()
status = await coordinator.get_system_status()

print(f"注册Agent数: {status['registered_agents']}")
print(f"消息处理成功率: {status['message_bus']['success_rate']:.2%}")
print(f"内存使用率: {status['memory_manager']['memory_percent']:.1f}%")
print(f"平均任务执行时间: {status['avg_execution_time_ms']:.1f}ms")
```

### 上下文构建统计
```python
builder = get_context_builder()

# 获取构建统计
stats = builder.get_statistics()
print(f"已构建上下文数: {stats['total_contexts_built']}")
print(f"最常用上下文类型: {stats['most_common_context_type']}")
print(f"平均占位符数量: {stats['avg_placeholders_per_context']:.1f}")
```

## 🧪 测试和调试

### 运行示例和测试
```bash
# 运行完整系统演示
python agents/run_example.py

# 运行上下文构建示例  
python agents/context/context_examples.py

# 运行简化演示
python simple_context_demo.py
```

### 单元测试
```python
# 测试上下文构建
from agents.context import AgentContextBuilder, ContextType

def test_context_builder():
    builder = AgentContextBuilder()
    
    context = builder.build_context(
        task_info=task_info,
        context_type=ContextType.DATA_ANALYSIS
    )
    
    assert context.context_type == ContextType.DATA_ANALYSIS
    assert len(context.execution_options) > 0
    assert 'data_analyzer' in context.tool_preferences['preferred_tools']
```

## 📈 版本历史和路线图

### 当前版本: 1.0.0
- ✅ 核心Agent协调器
- ✅ 智能上下文构建系统  
- ✅ 丰富的工具生态系统
- ✅ 专业化指令系统
- ✅ 六阶段编排模式

### 未来规划: 1.1.0
- 🔄 动态Agent注册和发现
- 🔄 分布式Agent协调
- 🔄 高级缓存和持久化
- 🔄 可视化监控界面
- 🔄 更多专业化工具

## 📚 相关文档

- [详细API文档](docs/API_REFERENCE.md)
- [工具开发指南](tools/TOOL_DEVELOPMENT.md) 
- [上下文系统详解](context/CONTEXT_SYSTEM_GUIDE.md)
- [性能优化指南](docs/PERFORMANCE_GUIDE.md)
- [部署和运维指南](docs/DEPLOYMENT_GUIDE.md)

---

这个整理后的Agents系统为你提供了模块化、可扩展的AI代理基础设施。通过清晰的目录结构和丰富的便捷函数，你可以轻松构建复杂的智能任务处理流程！