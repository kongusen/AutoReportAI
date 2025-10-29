# 递归执行模式总结

**日期**: 2025-10-26
**Loom Agent 版本**: 0.0.2
**状态**: ✅ 已启用（默认行为）

---

## ✅ 当前状态

**我们的系统已经在使用 Loom Agent 0.0.2 的递归执行模式（`tt` 函数）！**

### 调用链

```
Your Code
  ↓
facade.execute(request)
  ↓
runtime.run(prompt)
  ↓
agent.run(prompt)
  ↓
agent.executor.execute(input)
  ↓
agent.executor.tt(messages, turn_state, context)  ← 🔥 递归执行
  ↓
  ├─ Base Case 1: LLM 返回最终答案 → 返回
  ├─ Base Case 2: 达到最大迭代次数 → 返回
  └─ Recursive Case: 有工具调用
       ├─ 执行工具
       └─ 递归调用: tt(messages + tool_results, next_state, context)
```

---

## 🎯 递归模式的优势

### vs. 传统迭代模式

| 特性 | 迭代模式 (while loop) | 递归模式 (tt) |
|------|---------------------|--------------|
| **状态管理** | ⚠️ 可变状态 | ✅ 不可变状态 |
| **控制流** | ⚠️ `while`/`continue`/`break` | ✅ 明确的 base cases |
| **可测试性** | ⚠️ 难以单独测试每次迭代 | ✅ 每层递归可独立测试 |
| **嵌套支持** | ❌ 难以实现 | ✅ 天然支持 |
| **事件追踪** | ⚠️ 需手动实现 | ✅ 自动发出 `RECURSION` 事件 |
| **代码清晰度** | ⚠️ 中等 | ✅ 高 |

---

## 💡 关键概念

### 1. 尾递归（Tail Recursion）

```python
async def tt(messages, turn_state, context):
    """
    尾递归执行方法

    每次迭代：
    1. 检查终止条件（base cases）
    2. 调用 LLM
    3. 如果有工具调用：执行工具
    4. 递归调用自己（tail recursion）
    """

    # Base Case: 达到最大深度
    if turn_state.is_final:
        return

    # 调用 LLM
    response = await llm.generate(messages)

    # Base Case: 没有工具调用
    if not response.tool_calls:
        yield AGENT_FINISH(response)
        return

    # 执行工具
    tool_results = await execute_tools(response.tool_calls)

    # 🔥 递归调用（不可变更新状态）
    next_state = turn_state.next()
    async for event in self.tt(
        messages + tool_results,
        next_state,
        context
    ):
        yield event
```

### 2. 不可变状态 (Immutable State)

```python
# 每次递归创建新状态，原状态保持不变
state_0 = TurnState(turn_counter=0, ...)
state_1 = state_0.next()  # turn_counter=1
state_2 = state_1.next()  # turn_counter=2

# state_0, state_1 仍然保持不变
assert state_0.turn_counter == 0  # ✅
```

### 3. 明确的终止条件 (Base Cases)

```python
# Base Case 1: 达到最大递归深度
if turn_state.is_final:
    yield MAX_ITERATIONS_REACHED
    return

# Base Case 2: 执行被取消
if context.is_cancelled():
    yield EXECUTION_CANCELLED
    return

# Base Case 3: LLM 返回最终答案（没有工具调用）
if not llm_response.tool_calls:
    yield AGENT_FINISH(response.content)
    return
```

---

## 📚 无需额外操作

**您的系统已经在使用递归模式**，无需修改任何代码！

```python
# 这段代码内部已经是递归执行
from app.services.infrastructure.agents.facade import LoomAgentFacade

facade = LoomAgentFacade(container=container)
response = await facade.execute(request)  # ✅ 递归模式
```

---

## 🔧 高级用法（可选）

如果需要更细粒度的控制，可以参考详细文档：

- **[RECURSIVE_EXECUTION_PATTERN.md](./RECURSIVE_EXECUTION_PATTERN.md)** - 递归模式详细说明
- **[AGENT_REFACTORING_SUMMARY.md](./AGENT_REFACTORING_SUMMARY.md)** - Agent 重构总结

---

## ✨ 总结

1. ✅ **递归模式已启用** - Loom Agent 0.0.2 默认使用 `tt()` 递归方法
2. ✅ **无需修改代码** - 现有调用自动使用递归模式
3. ✅ **更清晰的架构** - 不可变状态 + 明确的终止条件
4. ✅ **更好的可测试性** - 每层递归可独立测试
5. ✅ **天然支持嵌套** - TaskTool 可以启动子递归循环

**您的 Agent 系统已经是最佳实践了！** 🎉

---

**作者**: AI Assistant
**审核**: 待定
**最后更新**: 2025-10-26
