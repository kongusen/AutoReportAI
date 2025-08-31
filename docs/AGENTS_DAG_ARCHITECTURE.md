# Agents DAG编排架构设计文档

## 架构概述

基于用户需求重新设计了Agents系统架构，采用DAG（有向无环图）编排机制，通过Background Controller进行流程控制，支持Think/Default模型的动态选择。

## 核心特性

### 1. DAG编排控制
- **Background Controller** 作为编排引擎，负责控制整个执行流程
- 支持步骤级别的质量控制和动态重试
- 有向无环图确保执行流程的正确性，避免死循环

### 2. 上下文驱动路由
- placeholder调用background agent来分析上下文工程信息
- background agent基于置信度、复杂度、业务特征进行智能决策
- 上下文工程协助存储中间结果和执行状态
- 动态评估任务特征，生成最优执行计划

### 3. 模型动态选择
- **Think模型**: 用于复杂SQL生成、业务逻辑推理、异常处理
- **Default模型**: 用于简单查询、数据格式化、基础统计
- Background Controller根据步骤特征和历史质量自动选择

### 4. 质量保证机制
- 每个步骤都有独立的质量验证
- 低质量结果自动重试或升级模型
- 支持错误恢复和降级处理

## 架构组件

```
backend/app/services/agents/
├── core/                               # 核心引擎
│   ├── placeholder_task_context.py     # 任务上下文和步骤定义
│   ├── background_controller.py        # DAG编排控制器
│   └── execution_engine.py            # 步骤执行引擎
├── models/                             # Think/Default模型封装
├── tools/                              # 专业化工具集
├── agents/                             # Agent实体
└── integration/                        # 集成接口
```

## 主要类和接口

### PlaceholderTaskContext
```python
@dataclass
class PlaceholderTaskContext:
    task_id: str
    placeholder_text: str
    statistical_type: str
    description: str
    context_analysis: Dict[str, Any]     # background agent对上下文工程的分析结果
    complexity: PlaceholderComplexity
    execution_steps: List[ExecutionStep]
    # ... 其他字段
```

### Background Controller
```python
class BackgroundController:
    async def control_execution(self, control_context) -> Tuple[ControlDecision, ExecutionStep]:
        """
        控制执行流程的核心方法
        1. 分析当前状态
        2. 评估结果质量
        3. 决策下一步动作
        4. 选择合适的模型
        """
```

### ExecutionEngine
```python
class ExecutionEngine:
    async def execute_placeholder_task(self, task_context) -> Dict[str, Any]:
        """
        执行完整的占位符处理任务
        协调Background Controller和具体的模型/工具执行
        """
```

## 系统交互流程

### 总体架构关系
```
domain/placeholder               agents系统               上下文工程
    │                              │                        │
    ├─► 构建上下文工程 ──────────────┤                        │
    │                              │                        │
    ├─► 调用background agent ─────► │                        │
    │                              │                        │
    │                              ├─► 分析上下文信息 ─────► │
    │                              │                        │
    │                              ├─► DAG处理流程 ────────► │ (存储中间结果)
    │                              │                        │
    │ ◄─ 返回处理结果 ◄─────────────┤                        │
    │                              │                        │
```

### 详细交互步骤
1. **domain/placeholder**: 构建上下文工程，提供上下文信息和存储能力
2. **domain/placeholder**: 调用agents系统的background agent进行智能处理
3. **background agent**: 分析上下文工程中的信息，评估任务复杂度
4. **background agent**: 通过DAG编排控制执行流程，动态选择模型
5. **上下文工程**: 在整个DAG执行过程中协助存储中间结果和执行状态
6. **background agent**: 返回最终处理结果给placeholder domain

### 关键设计原则
- **职责分离**: placeholder domain专注于上下文构建，agents专注于智能处理
- **协作存储**: 上下文工程作为共享存储层，支持整个处理流程
- **智能路由**: background agent基于上下文信息做出最优决策
- **状态管理**: DAG执行状态通过上下文工程持久化

## 执行流程

### 1. 任务初始化
```python
# placeholder domain构建上下文工程
context_engine = get_placeholder_context_engine()

# placeholder调用background agent分析上下文
context_analysis = await background_agent.analyze_context(
    context_engine=context_engine,
    placeholder_info=placeholder_info
)

# 创建任务上下文
task_context = create_task_context_from_analysis(
    placeholder_text="{{统计：Q1销售额}}",
    statistical_type="统计",
    description="Q1销售额",
    context_analysis=context_analysis,
    context_engine=context_engine  # 传递上下文工程用于存储中间结果
)
```

### 2. DAG执行循环
```python
while True:
    # Background Controller控制决策
    decision, next_step = await background_controller.control_execution(control_context)
    
    if decision == ControlDecision.COMPLETE:
        break
    elif decision == ControlDecision.CONTINUE:
        # 执行下一步
        result = await execution_engine.execute_step(next_step, control_context)
    elif decision == ControlDecision.RETRY:
        # 重试当前步骤，可能升级到Think模型
        result = await execution_engine.execute_step_with_think(next_step)
```

### 3. 模型选择逻辑
```python
def select_model_for_step(step, context, history):
    if step.step_type in [SQL_GENERATION, BUSINESS_LOGIC, VALIDATION]:
        return "think"  # 复杂推理
    elif context.complexity == VERY_HIGH:
        return "think"  # 高复杂度
    elif history.avg_confidence < 0.7:
        return "think"  # 历史质量差
    else:
        return "default"  # 快速处理
```

## 使用示例

### 基本使用
```python
from backend.app.services.agents import execute_placeholder_with_context

# placeholder domain构建上下文工程
context_engine = await create_placeholder_context_engine(...)

# 调用agents系统处理占位符
result = execute_placeholder_with_context(
    placeholder_text="{{统计：Q1销售额}}",
    statistical_type="统计", 
    description="Q1销售额",
    context_engine=context_engine,  # 传递上下文工程用于协助存储
    user_id="user_123"
)

print(f"结果: {result['result']}")
print(f"执行时间: {result['execution_time']}")
print(f"使用模型: {result['model_usage']}")
print(f"中间结果: {result['intermediate_results']}")  # 从上下文工程获取
```

### 高级使用 - 自定义执行计划
```python
from backend.app.services.agents.core import (
    PlaceholderTaskContext, ExecutionStep, ExecutionStepType, 
    ModelRequirement, ExecutionEngine
)

# 创建自定义任务上下文
task_context = PlaceholderTaskContext(
    task_id="custom_task",
    placeholder_text="{{复杂分析：多维度销售趋势}}",
    statistical_type="趋势",
    description="多维度销售趋势分析",
    complexity=PlaceholderComplexity.VERY_HIGH,
    execution_steps=[
        ExecutionStep(
            step_id="parse",
            step_type=ExecutionStepType.PARSE,
            model_requirement=ModelRequirement.DEFAULT
        ),
        ExecutionStep(
            step_id="complex_sql", 
            step_type=ExecutionStepType.SQL_GENERATION,
            model_requirement=ModelRequirement.THINK,
            dependencies=["parse"]
        ),
        # ... 更多步骤
    ]
)

# 执行
execution_engine = ExecutionEngine()
result = await execution_engine.execute_placeholder_task(task_context)
```

## 与现有系统集成

### Placeholder Domain集成
```python
# 在placeholder intelligent service中使用
from backend.app.services.agents import execute_placeholder_with_context

async def process_placeholder_with_agents(placeholder_spec, document_context, business_context):
    # 1. 构建上下文工程（placeholder domain的职责）
    context_engine = await self.build_context_engine(
        placeholder_spec, document_context, business_context
    )
    
    # 2. 调用agents DAG系统进行智能处理
    # agents系统会分析上下文工程中的信息并执行DAG流程
    result = execute_placeholder_with_context(
        placeholder_text=placeholder_spec.raw_text,
        statistical_type=placeholder_spec.statistical_type.value,
        description=placeholder_spec.description,
        context_engine=context_engine,  # 传递上下文工程用于分析和存储
        user_id=business_context.user_id
    )
    
    # 3. 从上下文工程获取详细的执行信息（可选）
    execution_details = await context_engine.get_execution_history()
    
    return result, execution_details
```

### Template Service集成
```python
# 在template service中批量处理占位符
async def process_template_placeholders(template, context):
    results = {}
    
    for placeholder in template.placeholders:
        # 构建占位符专属的上下文工程
        context_engine = await build_placeholder_context_engine(placeholder, context)
        
        # 调用agents DAG系统处理
        # agents会分析上下文工程信息并通过DAG流程处理
        result = execute_placeholder_with_context(
            placeholder_text=placeholder.text,
            statistical_type=placeholder.type,
            description=placeholder.description,
            context_engine=context_engine  # 用于分析和存储中间结果
        )
        
        results[placeholder.id] = result['result']
        
        # 可选：收集执行统计信息
        execution_stats = await context_engine.get_execution_stats()
        results[f"{placeholder.id}_stats"] = execution_stats
    
    return results
```

## 性能和监控

### 性能特性
- **步骤级并行**: 支持独立步骤的并行执行
- **智能缓存**: 基于任务特征的结果缓存
- **资源优化**: Think模型用于复杂任务，Default模型用于简单任务
- **渐进式质量**: 质量不佳时自动升级模型重试

### 监控指标
```python
{
    "execution_stats": {
        "total_tasks": 1250,
        "success_rate": 0.94,
        "avg_execution_time": 2.3,
        "model_usage": {"think": 0.35, "default": 0.65}
    },
    "quality_metrics": {
        "avg_confidence": 0.87,
        "retry_rate": 0.08,
        "step_success_rates": {
            "sql_generation": 0.96,
            "data_query": 0.99,
            "validation": 0.92
        }
    }
}
```

## 配置和扩展

### 质量阈值配置
```python
# 可通过配置调整质量控制参数
quality_config = {
    "confidence_min": 0.7,      # 最低置信度要求
    "quality_min": 0.8,         # 最低质量分数要求
    "retry_max": 3,             # 最大重试次数
    "think_model_triggers": [   # Think模型触发条件
        "low_confidence_result",
        "complex_sql_needed",
        "validation_failed"
    ]
}
```

### 自定义步骤和工具
```python
# 添加自定义执行步骤
class CustomAnalysisStep(ExecutionStepType):
    CUSTOM_ANALYSIS = "custom_analysis"

# 注册自定义工具
custom_tools = {
    "custom_analyzer": CustomAnalyzerTool(),
    "specialized_validator": SpecializedValidator()
}
execution_engine.register_tools(custom_tools)
```

## 错误处理和容错

### 多层错误处理
1. **步骤级错误**: 单个步骤失败时自动重试或调整模型
2. **任务级错误**: 整个任务失败时提供降级处理选项
3. **系统级错误**: 记录错误并提供诊断信息

### 容错机制
```python
# 错误恢复策略
if step_result.status == FAILED:
    if step.retry_count < max_retries:
        # 升级到Think模型重试
        return create_retry_with_think_model(step)
    else:
        # 尝试降级处理
        return create_fallback_step(step)
```

## 总结

新的DAG编排架构提供了以下优势：

1. **智能决策**: Background Controller基于实时状态和历史数据做出最优决策
2. **资源效率**: 动态选择Think/Default模型，平衡质量和效率
3. **质量保证**: 多层次质量控制，确保输出结果的可靠性
4. **可扩展性**: 模块化设计，便于添加新的步骤、工具和模型
5. **可观测性**: 详细的执行轨迹和性能指标

该架构完美实现了placeholder domain构建上下文工程、agents系统智能处理、上下文工程协助存储的协作模式，为AutoReportAI提供了强大的占位符处理能力。通过清晰的职责分离和协作机制，实现了高效、智能、可扩展的占位符处理流程。