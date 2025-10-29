# 递归模式下的动态 Context 组装架构

**日期**: 2025-10-26
**版本**: 1.0
**状态**: 设计中

---

## 🎯 核心问题

基于 Loom Agent 的**递归执行模式**（`tt()` 方法），我们需要重新思考：

1. **Context 如何在递归过程中动态传入？**
2. **Prompt 如何支持动态更新？**
3. **如何充分利用 ContextAssembler 的动态组装能力？**

---

## 🔄 递归执行流程回顾

```python
# 递归执行的核心逻辑
async def tt(messages, turn_state, context):
    """尾递归执行方法"""

    # Base Case 1: 达到最大深度
    if turn_state.is_final:
        return

    # 🔥 关键点：每次递归前调用 LLM
    # ContextRetriever 会在这里被触发！
    response = await llm.generate(messages)

    # Base Case 2: 没有工具调用
    if not response.tool_calls:
        yield AGENT_FINISH(response)
        return

    # 执行工具
    tool_results = await execute_tools(response.tool_calls)

    # 🔥 递归调用（messages 不断累积）
    next_messages = messages + [response] + tool_results
    next_state = turn_state.next()

    async for event in self.tt(next_messages, next_state, context):
        yield event
```

**关键特性**：
1. ✅ **Messages 累积**：每次递归都会累积之前的 LLM 响应和工具结果
2. ✅ **多次 LLM 调用**：每次递归都会调用一次 LLM
3. ✅ **ContextRetriever 多次触发**：如果配置了 ContextRetriever，每次 LLM 调用前都会检索 context

---

## ❌ 当前方案的问题

### 问题 1: ContextAssembler 只用了一次

```python
# Facade.execute()
async def execute(self, request):
    # ❌ 只在初始阶段组装一次 context
    prompt = await self._assemble_context(request)

    # Schema context 也在这里检索并添加
    # 但后续递归调用时，无法根据新的 messages 动态调整

    return await self._runtime.run(prompt)
```

**局限性**：
- Schema context 只在初始阶段检索一次
- 无法根据工具执行结果动态调整 schema
- 浪费了 ContextAssembler 的动态能力

### 问题 2: 递归过程中的 Context 是静态的

```
初始调用: prompt (静态 context)
  ↓
递归 1: messages + prompt (静态 context)
  ↓
递归 2: messages + response1 + tool_results1 + prompt (静态 context)
  ↓
递归 3: messages + response2 + tool_results2 + prompt (静态 context)
```

**问题**：
- 即使工具执行结果中提到了新的表名，schema context 也不会更新
- 无法实现真正的"动态上下文"

---

## ✅ 新架构设计

### 架构层次

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Facade 层 - 静态 Context 组装                              │
│    - 用户需求、阶段、任务上下文（不变的部分）                   │
│    - 使用 ContextAssembler 组装                               │
├─────────────────────────────────────────────────────────────┤
│ 2. Runtime 层 - 传递 ContextRetriever                        │
│    - 将 context_retriever 传递给 Agent                        │
├─────────────────────────────────────────────────────────────┤
│ 3. Agent Executor 层 - 递归执行                              │
│    - 每次递归调用 tt() 前，触发 ContextRetriever               │
├─────────────────────────────────────────────────────────────┤
│ 4. ContextRetriever 层 - 动态 Schema 检索与组装              │
│    - 根据当前 messages 检索相关 schema                        │
│    - 使用 ContextAssembler 组装 schema 文档                   │
│    - 注入到 system message                                   │
└─────────────────────────────────────────────────────────────┘
```

### 关键改进

#### 改进 1: 分离静态 Context 和动态 Context

**静态 Context（Facade 层，只组装一次）**：
- 用户需求
- 执行阶段
- 任务上下文（task_id, time_window 等）
- 工具列表

**动态 Context（ContextRetriever 层，每次递归都检索）**：
- 数据库 Schema（根据当前 query 检索）
- 工具执行历史（根据累积的 messages）
- 错误修复提示（根据之前的失败）

#### 改进 2: ContextAssembler 在 ContextRetriever 中使用

```python
class SchemaContextRetriever(BaseRetriever):
    """动态 Schema 检索器"""

    async def retrieve(self, query: str, **kwargs) -> List[Document]:
        # 1. 检索相关表
        documents = await self._search_schema(query)
        return documents

    def format_documents(self, documents: List[Document]) -> str:
        """
        🔥 在这里使用 ContextAssembler！
        每次递归调用都会触发这个方法
        """
        from loom.core.context_assembly import ContextAssembler, ComponentPriority

        # 设置 schema token 预算（避免超出 LLM 限制）
        assembler = ContextAssembler(max_tokens=4000)

        # 1. 高优先级：约束说明
        assembler.add_component(
            name="constraints",
            content=self._build_constraint_text(),
            priority=ComponentPriority.CRITICAL,
        )

        # 2. 中优先级：Schema 文档（按相关性排序）
        for i, doc in enumerate(documents):
            assembler.add_component(
                name=f"schema_{doc.metadata['table_name']}",
                content=doc.content,
                priority=ComponentPriority.HIGH if i < 3 else ComponentPriority.MEDIUM,
            )

        # 3. 组装并返回
        return assembler.assemble()
```

#### 改进 3: Loom 的自动注入机制

```python
# AgentExecutor 内部（每次递归调用 LLM 前）
async def _prepare_messages(self, messages):
    """准备发送给 LLM 的 messages"""

    if self.context_retriever:
        # 🔥 根据当前 messages 检索 context
        last_user_message = self._get_last_user_message(messages)
        documents = await self.context_retriever.retrieve_for_query(last_user_message)

        # 🔥 格式化（会调用 ContextAssembler）
        context_text = self.context_retriever.format_documents(documents)

        # 🔥 注入到 system message
        if self.context_retriever.inject_as == "system":
            messages = self._inject_system_message(messages, context_text)
        else:
            messages = self._inject_user_prefix(messages, context_text)

    return messages
```

---

## 🔧 实现方案

### 步骤 1: 增强 ContextRetriever 的 format_documents

**修改文件**: `app/services/infrastructure/agents/context_retriever.py`

```python
class ContextRetriever(BaseRetriever):
    """包装 SchemaContextRetriever，支持 Loom 注入"""

    def __init__(
        self,
        retriever: BaseRetriever,
        top_k: int = 5,
        max_schema_tokens: int = 4000,  # 🆕 Schema token 预算
        inject_as: str = "system",
    ):
        self.retriever = retriever
        self.top_k = top_k
        self.max_schema_tokens = max_schema_tokens
        self.inject_as = inject_as

    def format_documents(self, documents: List[Document]) -> str:
        """
        使用 ContextAssembler 组装 schema 文档

        这个方法会在**每次递归调用 LLM 前**被触发！
        """
        from loom.core.context_assembly import ContextAssembler, ComponentPriority

        assembler = ContextAssembler(max_tokens=self.max_schema_tokens)

        # 1. CRITICAL: 约束说明
        assembler.add_component(
            name="schema_constraints",
            content=self._build_constraints(),
            priority=ComponentPriority.CRITICAL,
        )

        # 2. HIGH/MEDIUM: Schema 文档（按相关性）
        for i, doc in enumerate(documents):
            priority = ComponentPriority.HIGH if i < 3 else ComponentPriority.MEDIUM
            assembler.add_component(
                name=f"schema_{doc.metadata.get('table_name', i)}",
                content=doc.content,
                priority=priority,
            )

        # 3. 组装
        result = assembler.assemble()

        # 记录 token 使用情况
        summary = assembler.get_summary()
        logger.info(f"📊 [SchemaAssembler] {summary}")

        return result

    def _build_constraints(self) -> str:
        """构建约束说明"""
        return """
# 📊 数据库Schema信息

⚠️⚠️⚠️ **关键约束** ⚠️⚠️⚠️

你**必须且只能**使用以下列出的表和列。
**禁止臆造任何不存在的表名或列名！**

## 可用的数据表
"""
```

### 步骤 2: 简化 Facade 层为静态 Context 组装

**修改文件**: `app/services/infrastructure/agents/facade.py`

```python
async def _assemble_context(self, request: AgentRequest) -> str:
    """
    组装**静态上下文**

    动态部分（Schema）由 ContextRetriever 在每次递归时注入
    """
    from loom.core.context_assembly import ContextAssembler, ComponentPriority

    assembler = ContextAssembler(max_tokens=self._max_context_tokens)

    # 1. CRITICAL: 用户需求
    assembler.add_component(
        name="user_prompt",
        content=f"### 用户需求\n{request.prompt}",
        priority=ComponentPriority.CRITICAL,
    )

    # 2. CRITICAL: 执行阶段
    assembler.add_component(
        name="stage_info",
        content=f"### 执行阶段\n{request.stage}\n### 工作模式\n{request.mode}",
        priority=ComponentPriority.CRITICAL,
    )

    # 3. MEDIUM: 任务上下文
    if request.context:
        context_json = json.dumps(request.context, ensure_ascii=False, indent=2)
        assembler.add_component(
            name="task_context",
            content=f"### 任务上下文\n{context_json}",
            priority=ComponentPriority.MEDIUM,
        )

    # ⚠️ 不再在这里检索 Schema！
    # Schema 由 ContextRetriever 在每次 LLM 调用前动态注入

    return assembler.assemble()
```

### 步骤 3: 确保 ContextRetriever 正确传递

**修改文件**: `app/services/infrastructure/agents/runtime.py`

```python
def _create_agent(
    *,
    llm_cfg: LLMRuntimeConfig,
    runtime_cfg: RuntimeOptions,
    tools: Sequence[BaseTool],
    llm: Optional[BaseLLM],
    context_retriever: Optional[Any] = None,
) -> Agent:
    """创建 Agent，传递 ContextRetriever"""

    agent_kwargs = {
        "tools": list(tools),
        "max_iterations": runtime_cfg.max_iterations,
        "llm": llm or _build_llm(llm_cfg),
    }

    # 🔥 传递 context_retriever（Loom 会自动在每次 LLM 调用前触发）
    if context_retriever is not None:
        agent_kwargs["context_retriever"] = context_retriever
        logger.info("✅ ContextRetriever 已注入 Agent（每次递归都会触发）")

    return build_agent(**agent_kwargs)
```

---

## 📊 执行流程对比

### ❌ 旧方案（静态 Context）

```
Facade.execute()
  ├─ _assemble_context()
  │   ├─ 组装用户需求
  │   ├─ 组装阶段信息
  │   └─ 🔴 检索并组装 Schema（只一次）
  │
  └─ Runtime.run(static_prompt)
       └─ Agent.run(static_prompt)
            └─ tt(messages=[user: static_prompt], turn=0)
                 ├─ LLM.generate(messages)  [Schema: 表A, 表B]
                 ├─ Tool: list_tables() → [表C]
                 └─ tt(messages + tool_result, turn=1)
                      ├─ LLM.generate(messages)  [Schema: 仍然是表A, 表B ❌]
                      └─ ...
```

### ✅ 新方案（动态 Context）

```
Facade.execute()
  ├─ _assemble_context()
  │   ├─ 组装用户需求
  │   ├─ 组装阶段信息
  │   └─ 组装任务上下文
  │   └─ ✅ 不检索 Schema（交给 ContextRetriever）
  │
  └─ Runtime.run(static_prompt)
       └─ Agent.run(static_prompt)
            └─ tt(messages=[user: static_prompt], turn=0)
                 ├─ ContextRetriever.retrieve("需求X")  [检索]
                 ├─ ContextAssembler.assemble([表A, 表B])  [组装]
                 ├─ LLM.generate(messages + schema_context)  [Schema: 表A, 表B]
                 ├─ Tool: list_tables() → [表C]
                 └─ tt(messages + tool_result, turn=1)
                      ├─ ContextRetriever.retrieve("表C 的列")  [✅ 重新检索]
                      ├─ ContextAssembler.assemble([表C])  [✅ 重新组装]
                      ├─ LLM.generate(messages + new_schema_context)  [Schema: 表C ✅]
                      └─ ...
```

---

## 🎯 关键优势

| 特性 | 旧方案 | 新方案 |
|------|--------|--------|
| **Schema 检索** | 一次（初始） | 每次递归 |
| **ContextAssembler 使用** | 一次 | 每次递归 + 初始 |
| **动态性** | ❌ 静态 | ✅ 动态 |
| **Token 管理** | 粗粒度 | 细粒度（每次递归） |
| **适应性** | ❌ 无法根据工具结果调整 | ✅ 根据工具结果动态调整 |

---

## 📋 实现 Checklist

- [ ] 增强 `ContextRetriever.format_documents()` 使用 ContextAssembler
- [ ] 简化 `Facade._assemble_context()` 只组装静态部分
- [ ] 确保 `context_retriever` 正确传递给 Agent
- [ ] 测试递归过程中的动态 schema 检索
- [ ] 监控 token 使用情况
- [ ] 创建测试用例

---

## 📚 参考文档

- [PRODUCTION_GUIDE.md](./PRODUCTION_GUIDE.md) - ContextAssembler 使用指南
- [RECURSIVE_EXECUTION_PATTERN.md](./RECURSIVE_EXECUTION_PATTERN.md) - 递归执行模式详解
- [CONTEXT_ENGINEERING_ARCHITECTURE.md](./CONTEXT_ENGINEERING_ARCHITECTURE.md) - 上下文工程架构

---

**作者**: AI Assistant
**审核**: 待定
**最后更新**: 2025-10-26
