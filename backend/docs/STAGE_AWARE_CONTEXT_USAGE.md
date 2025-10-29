# 阶段感知的智能上下文管理系统使用指南

## 概述

新的智能上下文管理系统能够根据Agent执行阶段动态提供最相关的上下文信息，避免上下文过载，提升Agent的决策质量。

## 核心组件

### 1. ExecutionStateManager（执行状态管理器）

**职责**：
- 跟踪Agent当前执行阶段
- 管理执行过程中产生的各种信息
- 维护工具调用历史

**使用方法**：

```python
from app.services.infrastructure.agents.context_manager import (
    ExecutionStateManager,
    ExecutionStage,
    ContextType,
    ContextItem
)

# 创建状态管理器
state_manager = ExecutionStateManager()

# 设置执行阶段
state_manager.set_stage(ExecutionStage.PLANNING)

# 添加上下文信息
state_manager.add_context(
    key="schema_cache",
    item=ContextItem(
        type=ContextType.SCHEMA,
        content="表结构信息...",
        metadata={"table": "orders"},
        relevance_score=1.0
    )
)

# 记录工具调用结果
state_manager.add_tool_result(
    tool_name="sql.validate",
    result={"valid": True, "errors": []},
    metadata={"sql_length": 100}
)
```

### 2. StageAwareContextRetriever（阶段感知上下文检索器）

**职责**：
- 根据当前执行阶段选择最相关的上下文类型
- 智能排序和聚焦上下文信息
- 格式化上下文以适应不同阶段

**执行阶段与上下文类型映射**：

| 阶段 | 主要上下文类型 | 说明 |
|------|---------------|------|
| PLANNING | Schema | 表结构信息，用于SQL规划 |
| VALIDATION | Validation Result, Schema | 验证结果和表结构 |
| EXECUTION | Execution Result, Validation Result | 执行结果和之前的验证 |
| OPTIMIZATION | Performance Metrics, Execution Result | 性能指标和执行结果 |
| CHART_GENERATION | Data Preview, Execution Result | 数据预览和执行结果 |
| ERROR_RECOVERY | Error Info, Validation Result, Schema | 错误信息和相关上下文 |

### 3. ToolResultRecorder（工具结果记录器）

**职责**：
- 自动记录工具调用结果
- 智能分类和格式化结果
- 计算相关性分数

**使用方法**：

```python
from app.services.infrastructure.agents.tool_wrapper import ToolResultRecorder

# 创建记录器
recorder = ToolResultRecorder(state_manager)

# 记录SQL验证结果
recorder.record_sql_validation(
    tool_name="sql.validate",
    result={
        "valid": False,
        "errors": ["Unknown column 'foo'"]
    }
)

# 记录SQL执行结果
recorder.record_sql_execution(
    tool_name="sql.execute",
    result={
        "success": True,
        "row_count": 100,
        "rows": [...]
    }
)
```

## 集成到现有系统

### 在PlaceholderService中使用

```python
class PlaceholderApplicationService:
    def __init__(self, user_id: str, context_retriever=None):
        self.user_id = user_id
        self.context_retriever = context_retriever

        # 获取state_manager（如果启用了阶段感知）
        self.state_manager = getattr(context_retriever, 'state_manager', None)

        # 创建工具结果记录器
        if self.state_manager:
            from app.services.infrastructure.agents.tool_wrapper import ToolResultRecorder
            self.tool_recorder = ToolResultRecorder(self.state_manager)
        else:
            self.tool_recorder = None

    async def analyze_placeholder(self, request):
        # 1. 设置阶段为PLANNING
        if self.state_manager:
            from app.services.infrastructure.agents.context_manager import ExecutionStage
            self.state_manager.set_stage(ExecutionStage.PLANNING)

        # 2. 调用Agent生成SQL
        result = await self.agent_service.execute(agent_input)

        # 3. 如果生成成功，切换到VALIDATION阶段
        if result.success and self.state_manager:
            self.state_manager.set_stage(ExecutionStage.VALIDATION)

            # 验证SQL
            validation_result = await self.validate_sql(result.result)

            # 记录验证结果
            if self.tool_recorder:
                self.tool_recorder.record_sql_validation(
                    tool_name="internal_validator",
                    result=validation_result
                )

            # 如果验证失败，切换到ERROR_RECOVERY阶段
            if not validation_result.get("valid"):
                self.state_manager.set_stage(ExecutionStage.ERROR_RECOVERY)
                # Agent会自动看到错误信息和修复建议
```

### 在任务执行中使用

```python
# 在tasks.py中
from app.services.infrastructure.agents.context_retriever import create_schema_context_retriever

# 创建上下文检索器（启用阶段感知）
schema_context_retriever = create_schema_context_retriever(
    data_source_id=str(task.data_source_id),
    connection_config=connection_config,
    container=container,
    top_k=10,
    inject_as="system",
    enable_stage_aware=True  # 🔥 启用阶段感知
)

# 获取state_manager
state_manager = getattr(schema_context_retriever, 'state_manager', None)

if state_manager:
    # 阶段1: 规划
    state_manager.set_stage(ExecutionStage.PLANNING)
    # ... 执行规划逻辑 ...

    # 阶段2: 验证
    state_manager.set_stage(ExecutionStage.VALIDATION)
    # ... 执行验证逻辑 ...

    # 阶段3: 执行
    state_manager.set_stage(ExecutionStage.EXECUTION)
    # ... 执行SQL ...
```

## 上下文聚焦策略

系统会自动应用以下聚焦策略：

1. **阶段优先级**：优先显示当前阶段最需要的上下文类型
2. **相关性排序**：按relevance_score排序，只返回top_k个
3. **时效性过滤**：自动清理过期的上下文
4. **错误优先**：验证失败或执行失败的结果会获得更高的相关性分数

## 格式化策略

不同阶段使用不同的格式化策略：

### PLANNING阶段
```
## 📊 数据表结构（SQL规划阶段）

以下是你可以使用的数据表和列信息，请仔细阅读并严格使用：

### 表: orders
**列信息**:
- order_id (BIGINT): 订单ID
- customer_id (BIGINT): 客户ID
...

⚠️ **关键约束**：
1. 只能使用上述列出的表和列
2. 表名和列名必须精确匹配
```

### ERROR_RECOVERY阶段
```
## ⚠️ 错误诊断与修复上下文

以下是错误信息和相关上下文，请分析并修复：

### 🚫 错误信息：
SQL验证失败: Unknown column 'foo'

### 📋 相关上下文：
表 orders 的列信息...
```

## 高级用法

### 自定义上下文项

```python
from datetime import datetime, timedelta

# 添加自定义上下文，设置过期时间
state_manager.add_context(
    key="temp_cache",
    item=ContextItem(
        type=ContextType.PERFORMANCE_METRICS,
        content="查询耗时: 1.5秒",
        metadata={"duration_ms": 1500},
        relevance_score=0.7,
        expires_at=datetime.now() + timedelta(minutes=5)  # 5分钟后过期
    )
)
```

### 查询工具调用历史

```python
# 获取最近的SQL验证调用
recent_validations = state_manager.get_recent_tool_calls(
    tool_name="sql.validate",
    limit=3
)

for call in recent_validations:
    print(f"Tool: {call['tool']}")
    print(f"Result: {call['result']}")
    print(f"Stage: {call['stage']}")
```

### 清理过期上下文

```python
# 定期清理过期的上下文
state_manager.clear_expired_context()
```

## 性能优化建议

1. **合理设置top_k**：不要设置过大，5-10个足够
2. **及时清理过期上下文**：在阶段切换时清理
3. **设置相关性分数**：重要的上下文设置更高的分数
4. **使用过期时间**：临时性的上下文设置过期时间

## 调试技巧

启用详细日志：

```python
import logging
logging.getLogger("app.services.infrastructure.agents.context_manager").setLevel(logging.DEBUG)
logging.getLogger("app.services.infrastructure.agents.tool_wrapper").setLevel(logging.DEBUG)
```

日志输出示例：

```
🎯 [ExecutionState] 切换到阶段: planning
📦 [ExecutionState] 添加上下文: schema_orders (类型: schema)
📝 记录SQL验证结果: sql.validate (失败)
🗑️ [ExecutionState] 清理了 2 个过期上下文
```

## 常见问题

### Q: 如何禁用阶段感知功能？

A: 在创建context_retriever时设置 `enable_stage_aware=False`

```python
retriever = create_schema_context_retriever(
    ...,
    enable_stage_aware=False  # 禁用
)
```

### Q: 自定义上下文类型？

A: 扩展ContextType枚举：

```python
class ContextType(str, Enum):
    # ... 现有类型 ...
    CUSTOM_TYPE = "custom_type"  # 添加自定义类型
```

### Q: 如何在Loom外部使用？

A: StateManager是独立的，可以单独使用：

```python
state_manager = ExecutionStateManager()
state_manager.set_stage(ExecutionStage.PLANNING)
# ... 使用state_manager ...
```

## 下一步

- [ ] 扩展更多上下文类型（如用户偏好、历史查询等）
- [ ] 实现基于向量相似度的智能排序
- [ ] 添加上下文压缩（summarization）
- [ ] 支持多轮对话的上下文持久化
