# BugFix: ReAct模式下schema=None导致的错误

## 问题描述

在启用ReAct模式后，task队列执行报告生成任务时出现错误：

```
[2025-10-24 10:23:38,598: ERROR/ForkPoolWorker-1] 占位符分析失败: 'NoneType' object has no attribute 'tables'
[2025-10-24 10:23:38,598: ERROR/ForkPoolWorker-1] ❌ SQL结果验证失败: sql_result=None, has_sql_query=False
[2025-10-24 10:23:38,598: ERROR/ForkPoolWorker-1] ❌ 占位符 统计:退货原因为发票/收据不正规的退货单数量占总退货单数量的占比 SQL生成失败: Agent未返回有效的SQL结果
```

## 根本原因

### 1. ReAct模式的设计

在ReAct模式下，我们希望Agent自主使用工具探索schema，因此在 `PlaceholderApplicationService.analyze_placeholder` 中设置：

```python
# backend/app/services/application/placeholder/placeholder_service.py:181
agent_input = AgentInput(
    user_prompt=task_prompt,
    placeholder=PlaceholderSpec(...),
    schema=None,  # ← Agent自己探索schema，不预先提供
    context=TaskContext(...),
    data_source=data_source_config,
    ...
)
```

### 2. 兼容层的Bug

但是在Agent兼容层中，`_build_context_block` 函数没有处理 `schema=None` 的情况：

```python
# backend/app/services/infrastructure/agents/compat.py:66-69 (修复前)
def _build_context_block(agent_input: AgentInput) -> Dict[str, Any]:
    context: Dict[str, Any] = {}

    context["placeholder"] = _serialize(agent_input.placeholder)
    context["schema"] = {
        "tables": list(agent_input.schema.tables),  # ❌ agent_input.schema是None！
        "columns": _serialize(agent_input.schema.columns),
    }
    # ...
```

当 `agent_input.schema` 是 `None` 时，访问 `.tables` 属性会抛出：
```
'NoneType' object has no attribute 'tables'
```

## 修复方案

修改 `_build_context_block` 函数，支持 `schema=None` 的情况：

```python
# backend/app/services/infrastructure/agents/compat.py:62-84 (修复后)
def _build_context_block(agent_input: AgentInput) -> Dict[str, Any]:
    context: Dict[str, Any] = {}

    context["placeholder"] = _serialize(agent_input.placeholder)

    # ReAct模式支持：schema可以为None，Agent将自主使用工具探索schema
    if agent_input.schema is not None:
        context["schema"] = {
            "tables": list(agent_input.schema.tables),
            "columns": _serialize(agent_input.schema.columns),
        }
    else:
        # ReAct模式：schema=None表示Agent将使用schema.list_tables等工具自主探索
        context["schema"] = None

    context["task_context"] = _serialize(agent_input.context)
    context["constraints"] = _serialize(agent_input.constraints)
    if agent_input.data_source:
        context["data_source"] = agent_input.data_source
    if agent_input.task_driven_context:
        context["task_driven_context"] = agent_input.task_driven_context

    return _prune_empty(context)
```

### 注意事项

1. **`_prune_empty` 会过滤 `None` 值**：修复后的代码中 `context["schema"] = None` 会被 `_prune_empty` 函数过滤掉（Line 160: `v not in (None, {}, [], "")`），这是预期行为，因为在ReAct模式下我们不需要预先提供schema。

2. **向后兼容**：对于非ReAct模式（手动编排模式），`agent_input.schema` 仍然会是一个有效的SchemaInfo对象，兼容层会正常序列化它。

## 影响范围

### 修复前

- ❌ ReAct模式下的占位符分析会立即失败
- ❌ Task队列无法生成报告
- ❌ 错误日志：`'NoneType' object has no attribute 'tables'`

### 修复后

- ✅ ReAct模式正常工作，Agent可以自主使用工具探索schema
- ✅ Task队列可以正常执行占位符分析
- ✅ 向后兼容手动编排模式

## 测试建议

### 1. ReAct模式测试

```python
# 测试ReAct模式下的占位符分析
service = PlaceholderApplicationService(user_id="test-user")

request = PlaceholderAnalysisRequest(
    placeholder_id="test-001",
    business_command="统计退货申请数量",
    requirements="查询ods_refund表",
    data_source_info={...}
)

async for event in service.analyze_placeholder(request):
    print(event)
    # 应该成功生成SQL，不会报schema.tables错误
```

### 2. 手动编排模式测试（向后兼容）

```python
# 测试传统模式（schema != None）
agent_input = AgentInput(
    user_prompt="...",
    schema=SchemaInfo(
        tables=["table1", "table2"],
        columns={"table1": ["col1", "col2"]}
    ),
    ...
)

# 应该正常序列化schema
```

## 相关文档

- [ReAct模式SQL生成](./REACT_MODE_SQL_GENERATION.md)
- [多步骤SQL生成改进](./MULTI_STEP_SQL_IMPROVEMENT.md)
- [手动验证删除说明](./MANUAL_VALIDATION_REMOVAL.md)

## 总结

这个bug是ReAct模式改造过程中的一个兼容性问题：
- **根源**：兼容层假设 `agent_input.schema` 总是非空
- **触发**：ReAct模式设置 `schema=None`，让Agent自主探索
- **修复**：添加空值检查，支持ReAct模式的设计理念
- **影响**：修复后ReAct模式可以正常工作，同时保持向后兼容

这个修复是PTAV架构（Plan → Tool → Action → Validate）的关键部分，确保Agent可以自主使用工具，而不依赖预先提供的schema信息。
