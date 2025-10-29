# TT 递归上下文管理优化完成报告

## 优化概述

基于 loom-agent 的 TT（Tree Traversal）递归上下文管理机制，我们成功实现了完整的上下文管理能力，包括深度感知、优先级调整、共享上下文和跨阶段链路管理。

## 核心优化内容

### 1. **TT 递归上下文富集** (`tt_recursion.py`)

**功能**：
- 为每个阶段调用提供初始 turn_counter 和优先级提示
- 支持任务类型和复杂度感知的上下文构建
- 与调用方上下文进行智能合并

**实现**：
```python
def _build_enriched_context(base: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """构建带有 TT 提示的上下文"""
    tt_hints = {
        "tt": {
            "turn_counter": 1,  # 初始调用视为第 1 轮
            "priority_hints": {
                "base_instructions": "CRITICAL",
                "tool_definitions": "HIGH",
                "examples": "MEDIUM",
            },
            "task_type": stage,
            "complexity": complexity,
        }
    }
    return {**tt_hints, **base}
```

### 2. **深度感知的递归消息管理** (`runtime.py`)

**核心特性**：
- **深度递归检测**：当 turn_counter > 3 时自动调整策略
- **智能上下文截断**：根据深度和优先级动态调整历史消息数量
- **任务类型感知**：针对 SQL/图表/文档生成提供不同的指导策略
- **上下文大小监控**：实时监控 Token 使用量并发出警告

**实现亮点**：
```python
# 深度递归检测和上下文调整
deep_recursion_threshold = 3
is_deep_recursion = current_turn > deep_recursion_threshold

if is_deep_recursion:
    # 深度递归时，优先保留核心指令，减少示例和历史消息
    priority_hints = {
        "base_instructions": "CRITICAL",
        "tool_definitions": "HIGH", 
        "examples": "LOW",  # 降低示例优先级
        "history": "LOW"   # 降低历史消息优先级
    }

# 根据优先级和深度调整历史消息数量
if is_deep_recursion:
    max_history = 3  # 深度递归时只保留最近3条
elif priority_hints.get("history") == "HIGH":
    max_history = 15  # 高优先级时保留更多历史
else:
    max_history = 10  # 默认保留10条
```

### 3. **跨阶段链路 Turn Counter 管理** (`stage_aware_adapter.py`)

**功能**：
- 每个阶段调用自动递增 turn_counter
- 维护共享上下文，跨阶段传递信息
- 提供调试和监控能力

**实现**：
```python
class StageAwareAgentAdapter:
    def __init__(self):
        # TT 递归上下文管理
        self._turn_counter: int = 0
        self._shared_context: Dict[str, Any] = {}

    def _increment_turn_counter(self) -> int:
        """递增 turn_counter 并返回新值"""
        self._turn_counter += 1
        logger.info(f"🔄 [StageAwareAdapter] Turn counter 递增到: {self._turn_counter}")
        return self._turn_counter

    def _update_shared_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """更新共享上下文，合并新的上下文信息"""
        self._shared_context.update(context)
        
        enriched_context = {
            **self._shared_context,
            "tt": {
                "turn_counter": self._turn_counter,
                "shared_context": self._shared_context,
                "adapter_instance": id(self),  # 用于调试
            }
        }
        return enriched_context
```

### 4. **智能指导消息生成**

**任务类型感知**：
- **SQL 生成阶段**：关注表结构信息和查询执行
- **图表生成阶段**：关注查询数据和可视化需求
- **文档生成阶段**：关注内容优化和数据分析

**深度感知**：
- **正常递归**：提供详细的指导信息
- **深度递归**：提供简洁的指导，避免上下文膨胀

## 技术架构改进

### 1. **多层次上下文管理**

```
应用层调用
    ↓
TT 上下文富集 (tt_recursion.py)
    ↓
StageAwareAgentAdapter (turn_counter 管理)
    ↓
ContextAwareAgentExecutor (深度感知处理)
    ↓
TT 递归执行引擎 (loom-agent)
```

### 2. **上下文优先级体系**

```
CRITICAL (100): base_instructions
HIGH (90): tool_definitions, schema_info
MEDIUM (70): examples, analysis_guidelines
LOW (50): history_messages, detailed_examples
OPTIONAL (30): debug_info, verbose_logs
```

### 3. **深度递归优化策略**

- **Turn 1-3**：正常模式，保留完整上下文
- **Turn 4+**：深度模式，优先保留核心指令
- **动态调整**：根据任务类型和复杂度调整策略

## 性能优化成果

### 1. **上下文大小控制**
- 深度递归时历史消息从 10 条减少到 3 条
- 智能截断避免上下文膨胀
- Token 使用量监控和警告

### 2. **递归效率提升**
- 深度感知的指导消息生成
- 任务类型特定的优化策略
- 共享上下文减少重复计算

### 3. **调试和监控能力**
- 详细的 turn_counter 日志
- 上下文大小实时监控
- 适配器实例 ID 追踪

## 使用示例

### 跨阶段链路调用
```python
# 创建适配器实例
adapter = StageAwareAgentAdapter(container=container)

# 第一阶段：SQL 生成 (Turn 1)
sql_result = await adapter.generate_sql(
    placeholder="查询用户数据",
    data_source_id=1,
    user_id=user_id,
    context={"analysis_type": "user_behavior"}
)

# 第二阶段：图表生成 (Turn 2)
chart_result = await adapter.generate_chart(
    chart_placeholder="用户行为分析图",
    etl_data=sql_result["data"],
    user_id=user_id,
    task_context={"sql_result": sql_result}
)

# 第三阶段：文档生成 (Turn 3)
doc_result = await adapter.generate_document(
    paragraph_context="根据用户行为数据",
    placeholder_data={"chart_data": chart_result},
    user_id=user_id,
    task_context={"previous_results": [sql_result, chart_result]}
)
```

### 深度递归处理
```python
# 当 turn_counter > 3 时，系统自动：
# 1. 减少历史消息数量 (10 → 3)
# 2. 降低示例优先级 (MEDIUM → LOW)
# 3. 简化指导消息
# 4. 优先保留核心指令和工具定义
```

## 监控和日志

### 1. **Turn Counter 追踪**
```
🔄 [StageAwareAdapter] Turn counter 递增到: 1
🔄 [StageAwareAdapter] Turn counter 递增到: 2
🔄 [StageAwareAdapter] Turn counter 递增到: 3
```

### 2. **上下文大小监控**
```
✅ [ContextAwareExecutor] 递归消息准备完成
   总消息数: 8
   总字符数: 2048
   估算Token数: 512
   深度递归模式: 否
```

### 3. **深度递归检测**
```
🔍 [ContextAwareExecutor] 检测到深度递归（第4轮），调整上下文策略
⚠️ [ContextAwareExecutor] 上下文可能过大（8500 tokens），建议优化
```

## 总结

通过这次优化，我们成功实现了：

1. **✅ 完整的 TT 递归上下文管理**：支持深度感知和优先级调整
2. **✅ 跨阶段链路管理**：turn_counter 自动递增和共享上下文维护
3. **✅ 智能上下文优化**：根据深度和任务类型动态调整策略
4. **✅ 性能监控能力**：实时监控上下文大小和递归效率
5. **✅ 调试和追踪**：详细的日志记录和实例追踪

现在整个系统具备了完善的 TT 递归上下文管理能力，能够智能地处理复杂的多阶段任务，同时保持高效的性能和良好的可维护性！
