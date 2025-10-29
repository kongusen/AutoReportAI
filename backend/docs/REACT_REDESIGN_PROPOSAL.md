# ReAct 架构重新设计方案

**日期**: 2025-10-26
**版本**: 1.0
**状态**: 🚧 设计中

---

## 🎯 核心问题

当前的 "ReAct 模式" 虽然名为 ReAct，但**本质上是流程化指导**，没有充分利用 ReAct 的自主推理能力。

### 当前的流程（❌ 流程化）

```python
# placeholder_service.py
task_prompt = f"""
生成SQL: {request.business_command}

## 流程
1. 探索schema
2. 生成SQL (占位符不加引号)
3. 验证 → 失败则refine

## 输出JSON
{{"sql": "...", "reasoning": "...", ...}}
"""
```

**问题**：
- ❌ 明确告诉 Agent 要做哪些步骤（1, 2, 3）
- ❌ Schema 是被动注入的（ContextRetriever 自动注入）
- ❌ Agent 没有真正的"思考-行动-观察"循环
- ❌ 流程是线性的，不是递归的

### Agent 的实际行为

```
Turn 0:
  System: [自动注入的 schema context]
  User: 生成SQL，按照步骤1->2->3执行

Agent: 哦，schema 已经给我了，我直接生成SQL吧
  → 生成 SQL
  → 返回结果 ✅
```

**Agent 实际上不需要调用工具**，因为：
1. Schema 已经被注入了
2. 流程已经被规定了

---

## ✅ 真正的 ReAct 流程

### 理想的 Agent 行为

```
Turn 0:
  System: 你是 SQL 生成专家，可以使用这些工具：
    - schema.list_tables: 列出所有表
    - schema.list_columns: 查看表的列
    - sql.validate: 验证SQL
    - sql.execute: 测试SQL
  User: 目标：生成统计该产品总收入的SQL

Agent (Thought):
  我需要先了解数据库中有哪些表才能开始

Agent (Action):
  调用 schema.list_tables

═══════════════════════════════════════

Turn 1:
  Tool Result:
    ["online_retail", "customers", "products"]

Agent (Thought):
  online_retail 表看起来最相关（包含销售数据）
  我需要查看这个表的列结构

Agent (Action):
  调用 schema.list_columns(table="online_retail")

═══════════════════════════════════════

Turn 2:
  Tool Result:
    - InvoiceNo (VARCHAR)
    - Quantity (INT)
    - UnitPrice (DECIMAL)
    - InvoiceDate (DATETIME)
    - ...

Agent (Thought):
  好的，我看到了：
  - Quantity: 数量
  - UnitPrice: 单价
  - 收入 = Quantity * UnitPrice

  我需要生成 SQL 并验证

Agent (Action):
  生成候选 SQL:
  SELECT SUM(Quantity * UnitPrice) AS total_revenue
  FROM online_retail
  WHERE InvoiceDate BETWEEN {{start_date}} AND {{end_date}}

═══════════════════════════════════════

Turn 3:
Agent (Thought):
  让我验证这个 SQL 的列名是否正确

Agent (Action):
  调用 sql.validate_columns(
    sql="SELECT SUM(Quantity * UnitPrice) ...",
    table="online_retail"
  )

═══════════════════════════════════════

Turn 4:
  Tool Result:
    {"valid": true, "all_columns_exist": true}

Agent (Thought):
  列名验证通过，让我再验证SQL语法

Agent (Action):
  调用 sql.validate(sql="...")

═══════════════════════════════════════

Turn 5:
  Tool Result:
    {"valid": true, "message": "SQL语法正确"}

Agent (Thought):
  SQL已经验证通过，可以返回最终结果了

Agent (Action):
  finish

Final Result:
  {
    "sql": "SELECT SUM(Quantity * UnitPrice) AS total_revenue FROM online_retail WHERE InvoiceDate BETWEEN {{start_date}} AND {{end_date}}",
    "reasoning": "使用 online_retail 表，通过 Quantity * UnitPrice 计算总收入",
    "tables_used": ["online_retail"],
    "has_time_filter": true
  }
```

---

## 🔧 需要修改什么

### 1. 禁用自动 Schema 注入

**当前**：ContextRetriever 在每次递归时自动注入 schema

**修改方案 A**（推荐）：完全禁用 ContextRetriever，让 Agent 通过工具探索
```python
# runtime.py
runtime = build_default_runtime(
    container=container,
    context_retriever=None,  # ❌ 禁用自动注入
    ...
)
```

**修改方案 B**：保留 ContextRetriever，但只在 Agent 调用工具后才触发
```python
# context_retriever.py
async def retrieve_for_query(self, query: str, top_k: int = 5) -> List[Document]:
    # 只在查询中包含工具调用时才返回 schema
    if "schema.list" in query or "sql.validate" in query:
        return await self._retrieve_documents(query, top_k)
    return []  # 否则不注入
```

---

### 2. 简化 Prompt 为目标导向

**当前**：
```python
task_prompt = f"""
生成SQL: {request.business_command}

## 流程
1. 探索schema
2. 生成SQL
3. 验证
"""
```

**修改后**：
```python
task_prompt = f"""
目标：{request.business_command}

要求：
- 使用 Apache Doris 语法
- 包含时间过滤（使用 {{{{start_date}}}} 和 {{{{end_date}}}}，不加引号）
- 验证 SQL 正确性

你可以使用工具来探索数据库结构、验证SQL等。
"""
```

**关键区别**：
- ✅ 只给目标，不给步骤
- ✅ Agent 自己决定如何探索
- ✅ Agent 自己决定何时验证
- ✅ Agent 自己决定何时结束

---

### 3. 移除流程式的工具列表

**当前**：
```python
## 工具
- schema.list_tables: 列表
- schema.list_columns: 列详情
- sql.validate: 验证
- sql.refine: 优化

## 流程
1. 探索schema
2. 生成SQL
3. 验证
```

**修改后**：
```python
# 完全不在任务 prompt 中列出工具
# 工具列表由 generate_with_tools() 自动注入
```

工具描述会通过 `_format_tools_description()` 自动格式化并注入到 system message。

---

## 📊 对比：流程化 vs ReAct

| 维度 | 流程化（当前） | 真正的 ReAct（目标） |
|------|--------------|-------------------|
| **Prompt** | 明确步骤：1→2→3 | 只给目标 |
| **Schema** | 自动注入 | Agent 主动探索 |
| **工具使用** | 按流程调用 | Agent 自主决定 |
| **推理过程** | 线性执行 | 递归思考 |
| **灵活性** | 低（固定流程） | 高（自适应） |
| **token 使用** | 高（预先注入全部 schema） | 低（只检索需要的表） |

---

## 🎯 实现步骤

### Phase 1: 禁用自动 Schema 注入

**文件**: `app/services/infrastructure/agents/facade.py`

```python
# 当前
self._runtime = build_default_runtime(
    container=container,
    context_retriever=context_retriever,  # ❌ 自动注入
    ...
)

# 修改后
self._runtime = build_default_runtime(
    container=container,
    context_retriever=None,  # ✅ 禁用自动注入
    ...
)
```

**影响**：
- ✅ Agent 不会再收到自动注入的 schema
- ✅ Agent 必须通过工具探索

---

### Phase 2: 简化任务 Prompt

**文件**: `app/services/application/placeholder/placeholder_service.py`

```python
# 🔥 真正的 ReAct prompt（目标导向）
task_prompt = f"""
目标：{request.business_command}
{time_window_desc}

要求：
1. 使用 Apache Doris 语法（CASE WHEN，不支持 FILTER）
2. 时间过滤必须使用占位符：WHERE col BETWEEN {{{{start_date}}}} AND {{{{end_date}}}}
3. ⚠️ 占位符周围不加引号
4. 验证 SQL 正确性

💡 提示：
- 你不知道数据库有哪些表和列，需要先探索
- 使用工具来获取信息、验证SQL
- 自己决定何时完成任务

最终返回 JSON：
{{
  "sql": "...",
  "reasoning": "...",
  "tables_used": [...],
  "has_time_filter": true
}}
"""
```

**关键改变**：
- ❌ 移除了 "流程 1→2→3"
- ❌ 移除了工具列表（由 system 自动注入）
- ✅ 强调"你不知道数据库结构"
- ✅ 强调"自己决定"

---

### Phase 3: 确保工具正确注册

**文件**: `app/services/infrastructure/agents/tools/__init__.py`

确保所有工具都已注册：

```python
def build_default_tool_factories() -> List[ToolFactory]:
    return [
        # Schema 探索工具
        lambda c: SchemaListTablesTool(c),
        lambda c: SchemaListColumnsTool(c),

        # SQL 验证工具
        lambda c: SQLValidateTool(c),
        lambda c: SQLValidateColumnsTool(c),
        lambda c: SQLAutoFixColumnsTool(c),

        # SQL 执行工具
        lambda c: SQLExecuteTool(c),

        # SQL 优化工具
        lambda c: SQLRefineTool(c),
    ]
```

---

## 🧪 测试方案

### 测试 1: Agent 主动探索

```python
# 输入
request = {
    "business_command": "统计该产品总收入",
    "data_source_id": "...",
}

# 期望行为
Turn 0: Agent 调用 schema.list_tables
Turn 1: Agent 调用 schema.list_columns(table="online_retail")
Turn 2: Agent 生成 SQL
Turn 3: Agent 调用 sql.validate
Turn 4: Agent 返回最终结果

# 验证
assert len(tool_calls) >= 2  # 至少调用了 list_tables + list_columns
assert "schema.list_tables" in tool_names
assert "schema.list_columns" in tool_names
```

---

### 测试 2: Agent 自主决定验证策略

```python
# 输入：简单查询
request = {
    "business_command": "查询所有记录",
}

# 期望：Agent 可能不调用验证工具（因为SQL很简单）

# 输入：复杂查询
request = {
    "business_command": "统计每个国家每月的平均客单价，并计算同比增长率",
}

# 期望：Agent 会多次验证、优化
Turn X: sql.validate
Turn Y: sql.execute (测试)
Turn Z: sql.refine (优化)
```

---

## 🎯 预期效果

### 优势

1. **真正的自主推理**
   - ✅ Agent 自己决定探索策略
   - ✅ Agent 自己决定验证策略
   - ✅ 充分利用 LLM 的推理能力

2. **更高效的 Token 使用**
   - ✅ 只检索需要的表（不是全部注入）
   - ✅ 根据任务复杂度调整工具调用

3. **更好的可观察性**
   - ✅ 可以看到 Agent 的完整推理过程
   - ✅ 每次工具调用都有明确的理由（reasoning）

4. **更灵活的适应性**
   - ✅ 简单任务少调用工具
   - ✅ 复杂任务多调用工具
   - ✅ 遇到错误时自主调整策略

### 潜在挑战

1. **更多的 LLM 调用**
   - ❌ 每次工具调用都需要一次 LLM 调用
   - ✅ 可以通过缓存、批处理优化

2. **可能的探索失败**
   - ❌ Agent 可能选择错误的表
   - ✅ 可以通过验证工具及时发现并修正

3. **Token 累积问题**
   - ❌ 多次递归会累积 token
   - ✅ 已经有滑动窗口机制解决

---

## 📋 实施计划

### Milestone 1: 基础改造（1-2小时）
- [ ] 禁用 ContextRetriever 自动注入
- [ ] 简化 placeholder_service 的 task_prompt
- [ ] 测试 Agent 能否主动调用工具

### Milestone 2: 优化和测试（2-3小时）
- [ ] 创建测试用例验证 ReAct 流程
- [ ] 优化工具描述和参数定义
- [ ] 调整 system prompt 引导 Agent

### Milestone 3: 监控和调优（持续）
- [ ] 添加详细的日志记录 Agent 推理过程
- [ ] 监控工具调用模式
- [ ] 根据实际表现调整 prompt

---

## 🎉 总结

**当前**：流程化的伪 ReAct
```
User: 生成SQL
System: [自动注入 schema] + 请按步骤 1→2→3 执行
Agent: 好的，我按步骤执行
```

**目标**：真正的 ReAct
```
User: 目标是生成SQL，你自己决定怎么做
Agent:
  - (思考) 我需要先了解数据库结构
  - (行动) 调用 schema.list_tables
  - (观察) 看到了 online_retail 表
  - (思考) 我需要查看这个表的列
  - (行动) 调用 schema.list_columns
  - (观察) 看到了 Quantity、UnitPrice
  - (思考) 我可以生成SQL了
  - (行动) 生成SQL并验证
  - (完成) 返回结果
```

这才是 ReAct 的精髓：**Reasoning (推理) + Acting (行动) = ReAct**

---

**作者**: AI Assistant
**审核**: 待定
**最后更新**: 2025-10-26
