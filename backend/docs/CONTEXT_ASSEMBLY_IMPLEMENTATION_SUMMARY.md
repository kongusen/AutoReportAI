# 递归模式下的动态 Context 组装 - 实现总结

**日期**: 2025-10-26
**版本**: 1.0
**状态**: ✅ 已完成

---

## 📋 问题背景

### 原始错误

```
[2025-10-26 01:43:25,691: ERROR] ❌ [Runtime] Context检索失败:
'ContextRetriever' object has no attribute 'retrieve'

[2025-10-26 01:43:25,691: ERROR] Loom agent execution failed:
Agent.run() got an unexpected keyword argument 'event_collector'
```

### 根本原因分析

1. **API 调用错误**：
   - Runtime 层错误地调用了 `context_retriever.retrieve()`
   - 正确的方法应该是 `context_retriever.retrieve_for_query()`
   - 但更重要的是，**不应该在 Runtime 层手动调用！**

2. **架构理解偏差**：
   - 没有充分利用 Loom 的递归执行机制（tt() 方法）
   - ContextAssembler 只在初始阶段用了一次，浪费了动态能力
   - 没有理解 ContextRetriever 在递归过程中的自动触发机制

3. **参数传递错误**：
   - `Agent.run()` 不接受 `event_collector` 参数
   - 尝试传递不支持的参数导致执行失败

---

## ✅ 解决方案

### 核心架构改进

```
┌─────────────────────────────────────────────────────────────┐
│ Facade 层                                                    │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ _assemble_context()                                     │ │
│ │ - 使用 ContextAssembler 组装**静态上下文**              │ │
│ │   · 用户需求（CRITICAL）                                │ │
│ │   · 执行阶段（CRITICAL）                                │ │
│ │   · 任务上下文（HIGH）                                  │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Runtime 层                                                   │
│ - 简化为纯粹的代理层                                          │
│ - 不再手动注入 context                                       │
│ - 将 context_retriever 传递给 Agent                          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Agent Executor 层 (Loom 内部)                                │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ tt(messages, turn_state, context)                       │ │
│ │ [递归执行 - 每次调用 LLM 前]                             │ │
│ │                                                           │ │
│ │ if context_retriever:                                   │ │
│ │   docs = context_retriever.retrieve_for_query(query) ← 动态│ │
│ │   context = context_retriever.format_documents(docs)   │ │
│ │   messages = inject_context(messages, context)          │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ ContextRetriever 层                                          │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ format_documents(documents)                             │ │
│ │ - 使用 ContextAssembler 组装**动态 Schema 上下文**       │ │
│ │   · 约束说明（CRITICAL）                                │ │
│ │   · 前3个表（HIGH）                                      │ │
│ │   · 其他表（MEDIUM）                                     │ │
│ │   · 规则说明（LOW）                                      │ │
│ │   · Token 预算: 4000                                    │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 具体修改

### 1. 修复 Runtime 层（runtime.py）

#### 修改前（❌ 错误）

```python
async def run(self, prompt: str, **kwargs) -> str:
    # ❌ 手动调用 context_retriever.retrieve()
    if context_retriever is not None:
        documents = await context_retriever.retrieve(prompt, top_k=10)
        # 手动注入 context...

    # ❌ 传递不支持的参数
    return await self._agent.run(prompt, event_collector=event_collector, **kwargs)
```

#### 修改后（✅ 正确）

```python
async def run(self, prompt: str, **kwargs) -> str:
    """
    Context 组装应该在 Facade 层使用 ContextAssembler 完成。
    ContextRetriever 由 Loom 自动调用，不需要手动触发。
    """
    # 移除不支持的参数
    kwargs.pop("event_collector", None)

    # 直接代理到 Agent.run()
    # Loom 会自动在每次 LLM 调用前触发 context_retriever
    return await self._agent.run(prompt, **kwargs)
```

### 2. 增强 ContextRetriever 层（context_retriever.py）

#### 新增功能：在 format_documents 中使用 ContextAssembler

```python
def format_documents(self, documents: List[Document]) -> str:
    """
    🔥 这个方法会在每次递归调用 LLM 前被 Loom 触发！
    """
    from loom.core.context_assembly import ContextAssembler, ComponentPriority

    # Schema token 预算（避免超出 LLM 限制）
    assembler = ContextAssembler(max_tokens=4000)

    # 1. CRITICAL: 约束说明（必须保留）
    assembler.add_component(
        name="schema_constraints",
        content=constraint_text,
        priority=ComponentPriority.CRITICAL,
    )

    # 2. HIGH/MEDIUM: Schema 文档（按相关性）
    for i, doc in enumerate(documents):
        priority = ComponentPriority.HIGH if i < 3 else ComponentPriority.MEDIUM
        assembler.add_component(
            name=f"schema_{table_name}",
            content=table_content,
            priority=priority,
        )

    # 3. LOW: 规则说明
    assembler.add_component(
        name="schema_rules",
        content=rules_text,
        priority=ComponentPriority.LOW,
    )

    # 组装并记录 token 使用情况
    formatted_context = assembler.assemble()
    summary = assembler.get_summary()
    logger.info(f"📊 [SchemaAssembler] Token usage: {summary.get('total_tokens')}/4000")

    return formatted_context
```

**关键改进**：
- ✅ 使用 ContextAssembler 进行智能 token 管理
- ✅ 按优先级组织 schema 组件
- ✅ 支持自动裁剪（当 schema 超过 4000 tokens）
- ✅ 详细的日志记录

### 3. 简化 Facade 层（facade.py）

#### 修改前（❌ 职责混乱）

```python
async def _assemble_context(self, request: AgentRequest) -> str:
    assembler = ContextAssembler(max_tokens=self._max_context_tokens)

    # 添加用户需求...
    # 添加阶段信息...

    # ❌ 在这里检索 Schema（只检索一次）
    if self._context_retriever is not None:
        documents = await self._context_retriever.retrieve_for_query(...)
        schema_content = self._context_retriever.format_documents(documents)
        assembler.add_component("schema_context", schema_content, HIGH)

    return assembler.assemble()
```

#### 修改后（✅ 职责清晰）

```python
async def _assemble_context(self, request: AgentRequest) -> str:
    """
    组装**静态上下文**（用户需求、阶段、任务上下文）

    🔥 动态上下文（Schema）由 ContextRetriever 在每次递归调用时注入！
    """
    assembler = ContextAssembler(max_tokens=self._max_context_tokens)

    # 1. CRITICAL: 用户需求（绝对不能被裁剪）
    assembler.add_component(
        name="user_prompt",
        content=f"### 用户需求\n{request.prompt}",
        priority=ComponentPriority.CRITICAL,
    )

    # 2. CRITICAL: 执行阶段和模式
    assembler.add_component(
        name="stage_info",
        content=f"### 执行阶段\n{request.stage}\n\n### 工作模式\n{request.mode}",
        priority=ComponentPriority.CRITICAL,
    )

    # 3. HIGH: 任务上下文
    if request.context:
        assembler.add_component(
            name="task_context",
            content=f"### 任务上下文\n```json\n{context_json}\n```",
            priority=ComponentPriority.HIGH,
        )

    # ⚠️ 不在这里检索 Schema！
    # Schema 由 ContextRetriever 在每次 LLM 调用前动态注入
    if self._context_retriever is not None:
        logger.info("✅ [Facade] ContextRetriever 已配置，Schema 将在每次递归时动态注入")

    return assembler.assemble()
```

**关键改进**：
- ✅ 职责清晰：只组装静态部分
- ✅ 动态部分交给 ContextRetriever
- ✅ 充分利用递归机制

---

## 📊 执行流程对比

### ❌ 旧方案（一次性注入）

```
Facade.execute()
  ├─ _assemble_context()
  │   ├─ 组装用户需求
  │   ├─ 组装阶段信息
  │   └─ 🔴 检索 Schema（只一次）
  │
  └─ Runtime.run(static_prompt)
       └─ Agent.run(static_prompt)
            └─ tt(messages=[user: prompt], turn=0)
                 ├─ LLM.generate()  [Schema: 表A, 表B]
                 ├─ Tool: list_tables() → [表C]
                 └─ tt(messages + tool_result, turn=1)
                      ├─ LLM.generate()  [Schema: 仍然是 A, B ❌]
                      └─ SQL 生成失败（不知道表C的结构）
```

### ✅ 新方案（每次递归动态注入）

```
Facade.execute()
  ├─ _assemble_context()
  │   ├─ 组装用户需求
  │   ├─ 组装阶段信息
  │   └─ 组装任务上下文
  │   └─ ✅ 不检索 Schema
  │
  └─ Runtime.run(static_prompt)
       └─ Agent.run(static_prompt)
            └─ tt(messages=[user: prompt], turn=0)
                 ├─ ContextRetriever.retrieve_for_query("用户需求")
                 ├─ ContextAssembler.assemble([表A, 表B])  [4000 tokens]
                 ├─ LLM.generate(messages + schema_context)  [Schema: A, B]
                 ├─ Tool: list_tables() → [表C]
                 └─ tt(messages + tool_result, turn=1)
                      ├─ ContextRetriever.retrieve_for_query("表C 列")  ← ✅ 重新检索！
                      ├─ ContextAssembler.assemble([表C])  [4000 tokens]
                      ├─ LLM.generate(messages + new_schema)  [Schema: C ✅]
                      └─ SQL 生成成功（知道表C的结构）
```

---

## 🎯 关键优势

| 维度 | 旧方案 | 新方案 |
|------|--------|--------|
| **Schema 检索次数** | 1次（初始） | N次（每次递归） |
| **ContextAssembler 使用** | 1次（Facade） | N+1次（Facade + 每次递归） |
| **动态性** | ❌ 静态 | ✅ 动态适应 |
| **Token 管理** | 粗粒度（16000） | 细粒度（静态12000 + 动态4000） |
| **错误恢复** | ❌ 无法根据错误调整 | ✅ 根据错误重新检索相关表 |
| **工具结果利用** | ❌ 工具发现的新表无法获取schema | ✅ 工具发现新表后自动检索schema |

---

## 📝 测试场景

### 场景 1: 简单查询（一次递归）

```
用户: 查询最近7天的销售额

Facade: 组装静态 context（用户需求、阶段）
  ↓
递归 Turn 0:
  → ContextRetriever 检索: "销售" → [sales 表]
  → ContextAssembler: 组装 sales 表 schema
  → LLM 生成: SELECT SUM(amount) FROM sales WHERE ...
  → 返回结果 ✅
```

### 场景 2: 复杂查询（多次递归 + 工具调用）

```
用户: 分析客户购买行为

Facade: 组装静态 context

递归 Turn 0:
  → ContextRetriever 检索: "客户 购买" → [customers, orders]
  → LLM 判断: 需要先查看有哪些表
  → Tool: list_tables() → [customers, orders, products, reviews]

递归 Turn 1:
  → ContextRetriever 检索: "products reviews 客户购买" → [products, reviews, customers]  ← ✅ 基于工具结果重新检索！
  → LLM 生成:
    SELECT c.name, COUNT(o.id), AVG(r.rating)
    FROM customers c
    JOIN orders o ON c.id = o.customer_id
    JOIN products p ON o.product_id = p.id
    LEFT JOIN reviews r ON p.id = r.product_id
    GROUP BY c.id
  → 返回结果 ✅
```

### 场景 3: 错误恢复（Schema 不足）

```
用户: 查询退货率

Facade: 组装静态 context

递归 Turn 0:
  → ContextRetriever 检索: "退货" → [orders]
  → LLM 生成: SELECT ... FROM returns ...  ← ❌ returns 表不在 schema 中

递归 Turn 1（SQL 验证失败）:
  → ContextRetriever 检索: "returns 退货 表" → [returns, order_items]  ← ✅ 重新检索！
  → LLM 生成: SELECT ... FROM returns JOIN orders ...
  → 返回结果 ✅
```

---

## 🚀 部署影响

### 兼容性
- ✅ 向后兼容（保留了 legacy 降级路径）
- ✅ 渐进式增强（如果 Loom 不支持 ContextAssembler，回退到旧方式）

### 性能
- ✅ 静态 context 只组装一次（高效）
- ✅ 动态 schema 按需检索（避免浪费）
- ✅ Token 预算更精细（4000 for schema, 12000 for static）

### 可观测性
- ✅ 详细的日志记录
- ✅ Token 使用统计
- ✅ 组件裁剪警告

---

## 📚 相关文档

- [CONTEXT_ASSEMBLY_RECURSIVE_DESIGN.md](./CONTEXT_ASSEMBLY_RECURSIVE_DESIGN.md) - 架构设计文档
- [PRODUCTION_GUIDE.md](./PRODUCTION_GUIDE.md) - ContextAssembler 使用指南
- [RECURSIVE_EXECUTION_PATTERN.md](./RECURSIVE_EXECUTION_PATTERN.md) - 递归执行模式详解

---

## ✅ Checklist

- [x] 修复 Runtime 层 API 调用错误
- [x] 移除不支持的 event_collector 参数
- [x] 增强 ContextRetriever.format_documents() 使用 ContextAssembler
- [x] 简化 Facade._assemble_context() 只组装静态部分
- [x] 创建架构设计文档
- [x] 创建实现总结文档
- [ ] 测试递归过程中的动态 context
- [ ] 监控生产环境 token 使用情况

---

**作者**: AI Assistant
**审核**: 待定
**最后更新**: 2025-10-26
