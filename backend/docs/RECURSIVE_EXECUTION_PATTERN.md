# Loom Agent 递归执行模式（tt 函数）

**日期**: 2025-10-26
**Loom Agent 版本**: 0.0.2
**状态**: ✅ 已启用（默认行为）

---

## 📋 什么是递归执行模式？

Loom Agent 0.0.2 使用 **`tt()` 函数**（tail-recursive）作为核心执行方法，将传统的 `while` 循环迭代模式改造为**尾递归模式**。

### 传统迭代模式 vs. 递归模式

#### ❌ 传统迭代模式（旧方式）

```python
async def execute(self, prompt: str):
    messages = [{"role": "user", "content": prompt}]
    iterations = 0

    while iterations < MAX_ITERATIONS:
        # 调用 LLM
        response = await llm.generate(messages)

        # 解析工具调用
        if has_tool_calls(response):
            # 执行工具
            tool_results = await execute_tools(response.tool_calls)

            # 添加到消息列表
            messages.append(response)
            messages.extend(tool_results)

            iterations += 1
            continue  # 继续循环
        else:
            # 没有工具调用，返回最终答案
            return response.content

    raise MaxIterationsError()
```

**问题**：
- 状态管理复杂（需要手动维护 `iterations`, `messages` 等）
- 控制流不清晰（`continue`, `break` 混杂）
- 难以测试和调试
- 不易支持嵌套任务

#### ✅ 递归模式（Loom Agent 0.0.2）

```python
async def tt(
    self,
    messages: List[Message],
    turn_state: TurnState,  # 不可变状态
    context: ExecutionContext,  # 共享上下文
) -> AsyncGenerator[AgentEvent, None]:
    """
    Tail-recursive control loop (inspired by Claude Code).

    Recursion Flow:
        tt(messages, state_0, ctx)
          → LLM generates tool calls
          → Execute tools
          → tt(messages + tool_results, state_1, ctx)  # 递归调用
              → LLM generates final answer
              → return (base case)
    """

    # Base Case 1: 达到最大递归深度
    if turn_state.is_final:
        yield AgentEvent(type=AgentEventType.MAX_ITERATIONS_REACHED)
        return

    # Base Case 2: 执行被取消
    if context.is_cancelled():
        yield AgentEvent(type=AgentEventType.EXECUTION_CANCELLED)
        return

    # Phase 1: Context Assembly（上下文组装）
    full_context = await self._assemble_context(messages, turn_state)

    # Phase 2: LLM Call（调用 LLM）
    llm_response = await self._call_llm(full_context)

    # Base Case 3: 没有工具调用（最终答案）
    if not llm_response.tool_calls:
        yield AgentEvent(type=AgentEventType.AGENT_FINISH, content=llm_response.content)
        return

    # Phase 3: Tool Execution（执行工具）
    tool_results = await self._execute_tools(llm_response.tool_calls)

    # Phase 4: Recursive Call（递归调用）
    next_messages = messages + [llm_response] + tool_results
    next_state = turn_state.next()  # 不可变更新

    async for event in self.tt(next_messages, next_state, context):
        yield event  # 递归调用
```

**优势**：
- ✅ **状态不可变**：`TurnState` 是不可变的，每次递归创建新状态
- ✅ **控制流清晰**：明确的 base cases，没有 `continue`/`break`
- ✅ **易于测试**：每次递归调用都可以独立测试
- ✅ **支持嵌套**：子任务可以启动自己的递归循环
- ✅ **更好的事件追踪**：每次递归发出 `RECURSION` 事件

---

## 🔄 递归流程详解

### 完整执行流程

```
用户输入: "查询销售数据并生成图表"
    ↓
[Turn 0] tt(messages=[user_input], state_0, ctx)
    ├─ Phase 0: 递归控制 ✅
    ├─ Phase 1: Context Assembly（组装上下文）
    ├─ Phase 2: LLM Call
    │   └─ LLM 输出: tool_calls=[execute_sql]
    ├─ Phase 3: Tool Execution
    │   └─ execute_sql → result="sales data"
    └─ Phase 4: 递归调用 🔄
        ↓
    [Turn 1] tt(messages=[user_input, tool_call, tool_result], state_1, ctx)
        ├─ Phase 0: 递归控制 ✅
        ├─ Phase 1: Context Assembly
        ├─ Phase 2: LLM Call
        │   └─ LLM 输出: tool_calls=[generate_chart]
        ├─ Phase 3: Tool Execution
        │   └─ generate_chart → result="chart config"
        └─ Phase 4: 递归调用 🔄
            ↓
        [Turn 2] tt(messages=[...], state_2, ctx)
            ├─ Phase 0: 递归控制 ✅
            ├─ Phase 1: Context Assembly
            ├─ Phase 2: LLM Call
            │   └─ LLM 输出: "这是销售图表"（无工具调用）
            └─ Base Case: AGENT_FINISH ✋
                返回最终答案
```

### 关键数据结构

#### 1. `TurnState` - 不可变递归状态

```python
@dataclass(frozen=True)  # 不可变
class TurnState:
    turn_id: str
    turn_counter: int
    max_iterations: int
    parent_turn_id: Optional[str] = None

    @property
    def is_final(self) -> bool:
        """是否达到最大递归深度"""
        return self.turn_counter >= self.max_iterations

    def next(self) -> "TurnState":
        """创建下一个递归状态（不可变更新）"""
        return TurnState(
            turn_id=str(uuid.uuid4()),
            turn_counter=self.turn_counter + 1,
            max_iterations=self.max_iterations,
            parent_turn_id=self.turn_id,
        )

    @classmethod
    def initial(cls, max_iterations: int = 50) -> "TurnState":
        """创建初始状态"""
        return cls(
            turn_id=str(uuid.uuid4()),
            turn_counter=0,
            max_iterations=max_iterations,
        )
```

#### 2. `ExecutionContext` - 共享执行上下文

```python
@dataclass
class ExecutionContext:
    correlation_id: str
    cancel_token: Optional[asyncio.Event] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_cancelled(self) -> bool:
        """检查是否被取消"""
        return self.cancel_token is not None and self.cancel_token.is_set()

    @classmethod
    def create(
        cls,
        correlation_id: Optional[str] = None,
        cancel_token: Optional[asyncio.Event] = None,
    ) -> "ExecutionContext":
        return cls(
            correlation_id=correlation_id or str(uuid.uuid4()),
            cancel_token=cancel_token,
        )
```

---

## 💡 在我们系统中的应用

### 当前状态

**✅ 我们已经在使用递归模式！**

当前的调用链：
```python
# runtime.py
async def run(self, prompt: str, **kwargs) -> str:
    return await self._agent.run(prompt, **kwargs)

# loom.components.agent.Agent
async def run(self, input: str, ...) -> str:
    return await self._executor.execute(input, ...)

# loom.core.agent_executor.AgentExecutor
async def execute(self, user_input: str, ...) -> str:
    # 初始化状态
    turn_state = TurnState.initial(max_iterations=self.max_iterations)
    context = ExecutionContext.create(correlation_id=correlation_id)
    messages = [Message(role="user", content=user_input)]

    # 🔥 使用递归模式
    async for event in self.tt(messages, turn_state, context):
        if event.type == AgentEventType.AGENT_FINISH:
            return event.content
```

### 高级用法：直接使用 `tt()` 方法

如果需要更细粒度的控制，可以直接使用 `tt()` 方法：

```python
from loom.core.agent_executor import AgentExecutor, TurnState, ExecutionContext
from loom.core.events import AgentEvent, AgentEventType

async def advanced_agent_execution(
    executor: AgentExecutor,
    user_input: str,
    max_iterations: int = 10,
):
    """
    直接使用 tt() 递归方法，获得更强的控制能力
    """

    # 1. 初始化递归状态
    turn_state = TurnState.initial(max_iterations=max_iterations)
    context = ExecutionContext.create()
    messages = [Message(role="user", content=user_input)]

    # 2. 执行递归循环并处理事件
    tool_calls_count = 0
    recursion_depth = 0

    async for event in executor.tt(messages, turn_state, context):
        # 追踪递归深度
        if event.type == AgentEventType.RECURSION:
            recursion_depth = event.metadata.get('depth', 0)
            print(f"🔄 递归到第 {recursion_depth} 层")

        # 追踪工具调用
        elif event.type == AgentEventType.TOOL_RESULT:
            tool_calls_count += 1
            print(f"🔧 第 {tool_calls_count} 个工具执行完成")

        # 最终答案
        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"✅ 完成！总共递归 {recursion_depth} 次，调用 {tool_calls_count} 个工具")
            return event.content

        # 达到最大迭代次数
        elif event.type == AgentEventType.MAX_ITERATIONS_REACHED:
            print(f"⚠️ 达到最大递归深度 {max_iterations}")
            return None
```

### 在 Facade 中集成递归监控

```python
# facade.py
async def execute_with_recursion_tracking(self, request: AgentRequest) -> AgentResponse:
    """
    执行 Agent 并追踪递归深度
    """
    from loom.core.agent_executor import TurnState, ExecutionContext
    from loom.core.events import AgentEventType

    prompt = self._assemble_context(request)

    # 获取底层 executor
    executor = self._runtime.agent._executor

    # 初始化递归状态
    turn_state = TurnState.initial(max_iterations=self._config.runtime.max_iterations)
    context = ExecutionContext.create()
    messages = [{"role": "user", "content": prompt}]

    # 执行并追踪递归
    recursion_stats = {
        "max_depth": 0,
        "tool_calls": 0,
        "recursion_events": []
    }

    async for event in executor.tt(messages, turn_state, context):
        # 追踪递归事件
        if event.type == AgentEventType.RECURSION:
            depth = event.metadata.get('depth', 0)
            recursion_stats["max_depth"] = max(recursion_stats["max_depth"], depth)
            recursion_stats["recursion_events"].append({
                "from_turn": event.metadata.get('from_turn'),
                "to_turn": event.metadata.get('to_turn'),
                "depth": depth,
            })

        elif event.type == AgentEventType.TOOL_RESULT:
            recursion_stats["tool_calls"] += 1

        elif event.type == AgentEventType.AGENT_FINISH:
            parsed_output, metadata_updates = self._parse_llm_output(event.content)

            metadata = {
                "prompt": prompt,
                "recursion_stats": recursion_stats,  # 添加递归统计
            }
            metadata.update(request.metadata)
            metadata.update(metadata_updates)

            return AgentResponse(success=True, output=parsed_output, metadata=metadata)

    # 如果没有 AGENT_FINISH 事件（达到最大迭代）
    return AgentResponse(
        success=False,
        output="",
        error="达到最大递归深度",
        metadata={"recursion_stats": recursion_stats}
    )
```

---

## 🎯 递归模式的优势总结

### 1. **状态管理更清晰**
- ✅ 不可变状态（`TurnState.next()` 创建新状态）
- ✅ 避免状态污染
- ✅ 易于回溯和调试

### 2. **控制流更自然**
- ✅ 明确的终止条件（base cases）
- ✅ 没有复杂的 `while`/`continue`/`break`
- ✅ 更接近自然语言描述

### 3. **更好的可测试性**
- ✅ 每次递归调用可以独立测试
- ✅ 可以 mock 特定的递归层级
- ✅ 易于验证终止条件

### 4. **支持嵌套和并行**
- ✅ 子任务可以启动自己的递归循环
- ✅ 不同的递归分支可以并行执行
- ✅ TaskTool 天然支持递归模式

### 5. **更好的可观测性**
- ✅ 每次递归发出 `RECURSION` 事件
- ✅ 可以追踪递归深度和路径
- ✅ 易于实现分布式追踪

---

## 📊 性能对比

### 迭代模式 vs. 递归模式

| 指标 | 迭代模式 | 递归模式 |
|------|---------|----------|
| **代码复杂度** | ⚠️ 高（需手动管理状态） | ✅ 低（不可变状态） |
| **可读性** | ⚠️ 中等 | ✅ 高 |
| **可测试性** | ⚠️ 困难 | ✅ 容易 |
| **内存开销** | ✅ 低 | ✅ 低（尾递归优化） |
| **嵌套支持** | ❌ 困难 | ✅ 天然支持 |
| **事件追踪** | ⚠️ 需手动实现 | ✅ 内置支持 |

**注意**：Python 不支持 TCO（尾调用优化），但 loom-agent 使用 `async for event in self.tt()` 的方式避免了栈溢出问题。

---

## 🔧 最佳实践

### 1. 使用默认的 `agent.run()` 即可

对于大多数场景，直接使用 `agent.run()` 就已经是递归模式了：

```python
# 简单使用（已经是递归）
response = await agent.run("查询销售数据")
```

### 2. 需要细粒度控制时，使用 `tt()` 方法

```python
# 高级使用（直接调用 tt）
executor = agent._executor
turn_state = TurnState.initial(max_iterations=10)
context = ExecutionContext.create()
messages = [Message(role="user", content="查询销售数据")]

async for event in executor.tt(messages, turn_state, context):
    # 处理每个事件
    if event.type == AgentEventType.RECURSION:
        print(f"递归深度: {event.metadata['depth']}")
```

### 3. 监控递归深度

```python
# 添加递归深度监控
MAX_SAFE_DEPTH = 20

async for event in executor.tt(messages, turn_state, context):
    if event.type == AgentEventType.RECURSION:
        depth = event.metadata.get('depth', 0)
        if depth > MAX_SAFE_DEPTH:
            logger.warning(f"递归深度过深: {depth}")
```

### 4. 利用不可变状态

```python
# 不可变状态的好处
state_0 = TurnState.initial(max_iterations=10)
state_1 = state_0.next()
state_2 = state_1.next()

# state_0 仍然保持初始状态，可以用于回溯
assert state_0.turn_counter == 0
assert state_1.turn_counter == 1
assert state_2.turn_counter == 2
```

---

## 📚 相关资源

- [Loom Agent 文档](https://github.com/loom-agent/loom-agent)
- [AGENT_REFACTORING_SUMMARY.md](./AGENT_REFACTORING_SUMMARY.md) - Agent 重构总结
- [PRODUCTION_GUIDE.md](../PRODUCTION_GUIDE.md) - 生产环境指南

---

**总结**：Loom Agent 0.0.2 的递归模式（`tt()` 函数）是对传统迭代模式的重大改进，提供了更清晰的状态管理、更自然的控制流和更好的可测试性。**我们的系统已经在使用递归模式**，无需额外配置。如需更细粒度的控制，可以直接使用 `tt()` 方法。

---

**作者**: AI Assistant
**审核**: 待定
**最后更新**: 2025-10-26
