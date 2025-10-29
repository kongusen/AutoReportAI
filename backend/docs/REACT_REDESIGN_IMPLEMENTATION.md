# ReAct 架构改造实施总结

**日期**: 2025-10-26
**版本**: 1.0
**状态**: ✅ 已完成

---

## 🎯 改造目标

将流程化的伪 ReAct 改造为真正的 ReAct 模式：
- ❌ **Before**: 给 Agent 明确的步骤（1→2→3），自动注入 schema
- ✅ **After**: 只给 Agent 目标，让 Agent 自主探索和推理

---

## 🔧 实施内容

### 1. 简化 Prompt 为目标导向

**文件**: `app/services/application/placeholder/placeholder_service.py:140-166`

#### Before（❌ 流程化）

```python
task_prompt = f"""
生成SQL: {request.business_command}

## 流程
1. 探索schema
2. 生成SQL (占位符不加引号)
3. 验证 → 失败则refine

## 工具
- schema.list_tables: 列表
- schema.list_columns: 列详情
- sql.validate: 验证
"""
```

**问题**：
- 明确告诉 Agent 要做什么步骤
- 工具列表手动维护（会与实际注册的工具不一致）

#### After（✅ 目标导向）

```python
task_prompt = f"""
🎯 目标：{request.business_command}
{time_window_desc}

📋 要求：
1. 使用 Apache Doris 语法（CASE WHEN，不支持 FILTER）
2. 必须包含时间过滤：WHERE col BETWEEN {{{{start_date}}}} AND {{{{end_date}}}}
3. ⚠️ 关键：占位符周围不加引号！
   - ✅ 正确：WHERE dt BETWEEN {{{{start_date}}}} AND {{{{end_date}}}}
   - ❌ 错误：WHERE dt BETWEEN '{{{{start_date}}}}'
4. 确保 SQL 正确性

💡 重要提示：
- 你当前不知道数据库有哪些表和列
- 使用工具探索数据库结构、验证 SQL
- 自己决定何时完成任务
- 可以多次尝试和优化

📊 最终返回 JSON 格式：
{{
  "sql": "你生成的 SQL 查询",
  "reasoning": "你的推理过程（为什么选择这些表/列/计算方式）",
  "tables_used": ["使用的表列表"],
  "has_time_filter": true
}}
"""
```

**改进**：
- ✅ 只给目标和要求，不给步骤
- ✅ 强调"你不知道数据库结构"
- ✅ 强调"自己决定"
- ✅ 移除了工具列表（由 system 自动注入）

---

### 2. 禁用自动 Schema 注入

**文件**: `app/services/application/placeholder/placeholder_service.py:198-210`

#### Before（❌ 自动注入）

```python
# 使用全局的 self.agent_service（带 ContextRetriever）
result = await self.agent_service.execute(agent_input)
```

**问题**：
- ContextRetriever 会在每次递归时自动注入 schema
- Agent 被动接受信息，不需要主动探索
- 工具调用（schema.list_tables, list_columns）变得没有意义

#### After（✅ Agent 主动探索）

```python
# 🔥 ReAct 模式：创建不带 ContextRetriever 的 Agent
# 这样 Agent 必须通过工具主动探索 schema，而不是被动接受
logger.info("🔥 创建真正的 ReAct Agent（无自动 schema 注入）...")
from app.services.infrastructure.agents import AgentService

react_agent = AgentService(
    container=self.container,
    context_retriever=None  # 🔥 禁用自动注入！
)

# 调用Agent执行ReAct
logger.info("📞 调用Agent执行ReAct模式...")
result = await react_agent.execute(agent_input)
```

**改进**：
- ✅ 专门为 ReAct 模式创建不带 ContextRetriever 的 Agent
- ✅ Agent 必须通过工具探索（schema.list_tables, list_columns）
- ✅ 真正的"思考-行动-观察"循环

---

### 3. 添加配置标志

**文件**: `app/services/application/placeholder/placeholder_service.py:187-194`

```python
task_driven_context={
    "mode": "react",
    "business_command": request.business_command,
    "requirements": request.requirements,
    "target_objective": request.target_objective,
    "enable_tools": True,  # 明确启用工具使用
    "disable_auto_schema": True  # 🔥 禁用自动 schema 注入，让 Agent 主动探索
},
```

**作用**：
- 文档化配置意图
- 为未来可能的运行时检查提供标志

---

## 🎯 预期的 Agent 行为

### Before（流程化）

```
Turn 0:
  System: [自动注入的 online_retail 表结构]
  User: 生成SQL，按照步骤1->2->3执行

Agent:
  哦，schema 已经给我了，我直接生成SQL吧

  → 生成 SQL: SELECT SUM(...) FROM online_retail ...
  → 返回结果 ✅

Tool calls: 0 次
Turns: 1 次
```

### After（真正的 ReAct）

```
Turn 0:
  System: 你有这些工具：schema.list_tables, schema.list_columns, sql.validate, ...
  User: 🎯 目标：统计该产品总收入
        💡 你当前不知道数据库有哪些表和列

Agent (Thought):
  我需要先了解数据库中有哪些表

Agent (Action):
  {
    "action": "tool_call",
    "reasoning": "需要先查看数据库中有哪些表",
    "tool_calls": [{"name": "schema.list_tables", "arguments": {}}]
  }

═══════════════════════════════════════

Turn 1:
  Tool Result: ["online_retail", "customers", "products"]

Agent (Thought):
  online_retail 表看起来最相关（包含销售数据）
  我需要查看这个表的列结构

Agent (Action):
  {
    "action": "tool_call",
    "reasoning": "需要查看 online_retail 表的列结构",
    "tool_calls": [{"name": "schema.list_columns", "arguments": {"table_name": "online_retail"}}]
  }

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
  - 产品收入 = Quantity * UnitPrice
  - InvoiceDate: 用于时间过滤

Agent (Action):
  生成候选 SQL 并验证

═══════════════════════════════════════

Turn 3:
Agent (Thought):
  让我验证列名是否正确

Agent (Action):
  {
    "action": "tool_call",
    "reasoning": "验证SQL中的列名",
    "tool_calls": [{"name": "sql.validate_columns", "arguments": {...}}]
  }

═══════════════════════════════════════

Turn 4:
  Tool Result: {"valid": true}

Agent (Action):
  {
    "action": "finish",
    "content": {
      "sql": "SELECT SUM(Quantity * UnitPrice) AS total_revenue FROM online_retail WHERE InvoiceDate BETWEEN {{start_date}} AND {{end_date}}",
      "reasoning": "使用 online_retail 表，通过 Quantity * UnitPrice 计算总收入",
      "tables_used": ["online_retail"],
      "has_time_filter": true
    }
  }

Tool calls: 3-5 次
Turns: 4-6 次
```

---

## 📊 关键对比

| 维度 | Before（流程化） | After（ReAct） |
|------|----------------|--------------|
| **Prompt** | 明确步骤1→2→3 | 只给目标 |
| **Schema** | 自动注入 | Agent 主动探索 |
| **工具调用** | 可选（有 schema 不需要调用） | 必须（否则不知道表结构） |
| **推理过程** | 线性执行 | 递归思考 |
| **灵活性** | 低（固定流程） | 高（自适应） |
| **可观察性** | 低（看不到思考） | 高（每步都有 reasoning） |
| **Token 使用** | 高（预先注入全部 schema） | 可能更低（只检索需要的表） |
| **LLM 调用次数** | 1-2 次 | 3-6 次 |

---

## 🎯 关键优势

### 1. 真正的自主推理

**Before**：
```python
Agent: 看到 schema 了，按步骤生成 SQL
```

**After**：
```python
Agent:
  - (Thought) 我不知道有哪些表，需要探索
  - (Action) 调用 list_tables
  - (Observation) 看到 online_retail 表
  - (Thought) 我需要知道列结构
  - (Action) 调用 list_columns
  - (Observation) 看到 Quantity, UnitPrice 列
  - (Thought) 可以计算收入了
  - (Action) 生成 SQL
```

### 2. 更好的可观察性

每次工具调用都有明确的 reasoning：
- "需要先查看数据库中有哪些表"
- "online_retail 表看起来最相关，需要查看列结构"
- "验证SQL中的列名是否正确"

### 3. 充分利用 LLM 能力

- LLM 自己决定探索策略
- LLM 自己决定验证策略
- LLM 根据任务复杂度调整工具调用

### 4. 更灵活的适应性

**简单任务**（查询所有记录）：
- 可能只调用 1-2 个工具
- 快速完成

**复杂任务**（多表联合、复杂计算）：
- 可能调用 5-6 个工具
- 多次验证和优化

---

## 🧪 验证方案

### 测试 1: Agent 主动探索

```bash
# 输入
business_command: "统计该产品总收入"

# 期望的工具调用序列
1. schema.list_tables
2. schema.list_columns(table="online_retail")
3. sql.validate_columns(...)
4. (finish)

# 验证点
- ✅ Agent 是否主动调用 list_tables？
- ✅ Agent 是否基于 list_tables 结果选择表？
- ✅ Agent 是否调用 list_columns 获取列信息？
- ✅ Agent 是否验证生成的 SQL？
```

### 测试 2: 复杂查询的多次迭代

```bash
# 输入
business_command: "统计每个国家每月的平均客单价，并计算同比增长率"

# 期望的工具调用序列
1. schema.list_tables
2. schema.list_columns(table="online_retail")
3. (生成初步SQL)
4. sql.validate_columns(...)
5. sql.validate(...)
6. sql.refine(...)  # 优化复杂计算
7. sql.validate(...)  # 再次验证
8. (finish)

# 验证点
- ✅ Agent 是否处理复杂的聚合计算？
- ✅ Agent 是否多次验证和优化？
- ✅ Agent 是否正确处理时间维度？
```

---

## ⚠️ 潜在挑战

### 1. 更多的 LLM 调用次数

**Before**: 1-2 次 LLM 调用
**After**: 3-6 次 LLM 调用

**影响**：
- 更长的响应时间（每次调用 ~1-3秒）
- 更高的 API 成本

**缓解方案**：
- 使用更快的 LLM（如 GPT-4o-mini）
- 添加工具结果缓存
- 并行调用部分工具

### 2. Agent 可能的探索失败

**风险**：
- Agent 可能选择错误的表
- Agent 可能遗漏重要的列
- Agent 可能过早结束探索

**缓解方案**：
- 在 system prompt 中添加更多指导
- 提供错误恢复机制（sql.refine）
- 添加验证工具（sql.validate_columns）

### 3. Token 累积问题

**风险**：
- 多次递归会累积大量 messages
- 可能超出 LLM 上下文限制

**已有解决方案**：
- ✅ 滑动窗口机制（ContainerLLMAdapter）
- ✅ Token 预算管理（max_tokens=12000）

---

## ✅ 总结

### 完成的改造

1. ✅ **Prompt 简化**：移除流程指导，只给目标
2. ✅ **禁用自动注入**：创建不带 ContextRetriever 的 Agent
3. ✅ **配置标志**：添加 disable_auto_schema 标记

### 关键差异

**Before（伪 ReAct）**：
```
User: 生成SQL
System: [自动注入 schema] + 请按步骤 1→2→3 执行
Agent: 好的，我按步骤执行（1次调用完成）
```

**After（真正的 ReAct）**：
```
User: 目标是生成SQL，你自己决定怎么做
Agent:
  - (思考) 我需要先了解数据库结构
  - (行动) 调用 schema.list_tables
  - (观察) 看到了表列表
  - (思考) 我需要查看列结构
  - (行动) 调用 schema.list_columns
  - (观察) 看到了列信息
  - (思考) 我可以生成SQL了
  - (行动) 生成并验证SQL
  - (完成) 返回结果

（3-6次调用，充分推理）
```

这才是 ReAct 的精髓：**Reasoning (推理) + Acting (行动) = ReAct** 🎉

---

**作者**: AI Assistant
**审核**: 待定
**最后更新**: 2025-10-26
