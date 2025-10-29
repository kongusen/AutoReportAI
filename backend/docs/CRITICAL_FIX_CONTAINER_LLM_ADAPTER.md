# 关键修复：ContainerLLMAdapter 丢失 Schema Context

**日期**: 2025-10-26
**严重性**: 🔴 CRITICAL
**状态**: ✅ 已修复

---

## 🔴 问题诊断

### 用户报告

> "我觉得完全没有使用到这些能力，还是错误百出"

### 实际问题

从日志分析发现：

1. ✅ **Schema 检索正常**：
   ```
   ✅ [SchemaContextRetriever] 检索到 1 个相关表
      返回的表: ['online_retail']
   ```

2. ❌ **LLM 没有看到 Schema**：
   ```
   "sql": "SELECT SUM(revenue) AS total_revenue FROM sales WHERE ..."
   ```
   生成了 `sales` 表，但实际只有 `online_retail` 表！

3. ❌ **验证失败**：
   ```
   ⚠️ 表 'sales' 不存在
   ❌ SQL 列验证失败
   ```

4. ❌ **关键日志缺失**：
   - 没有 `📝 [ContextRetriever.format_documents] 被Loom调用`
   - 没有 `📊 [SchemaAssembler] Token usage: xxx/4000`

---

## 🔍 根本原因

### ContainerLLMAdapter 的致命缺陷

**文件**: `app/services/infrastructure/agents/runtime.py:51-82`

```python
# ❌ 修复前：只提取最后一条 user message
async def generate(self, messages: List[Dict]) -> str:
    prompt = self._extract_prompt(messages)  # ❌ 丢弃 system messages
    # ...
    response = await self._service.ask(
        user_id=user_id,
        prompt=prompt,  # ❌ 只传递 user message，schema context 丢失！
    )

def _extract_prompt(self, messages: List[Dict]) -> str:
    user_messages = [m for m in messages if m.get("role") == "user"]
    return user_messages[-1]  # ❌ 只返回最后一条，丢弃所有 system messages！
```

### 问题分析

**即使 Loom 在 messages 中注入了 schema context（作为 system message），ContainerLLMAdapter 也会把它扔掉！**

```
Loom 的 messages 结构：
[
  {
    "role": "system",
    "content": "# 📊 数据表结构信息\n\n## online_retail\n- InvoiceNo\n- StockCode\n- ..."  ← ❌ 被丢弃！
  },
  {
    "role": "user",
    "content": "生成一个SQL查询..."  ← ✅ 只有这个被传递
  }
]

ContainerLLMAdapter 只提取:
prompt = "生成一个SQL查询..."  ← ❌ Schema 丢失！
```

### 为什么 ContextRetriever 机制没有工作？

根本原因不是 ContextRetriever 没有被调用（它可能被调用了），而是：

1. Loom 正确地将 schema context 注入到 messages 中
2. 但 ContainerLLMAdapter 错误地只提取 user message
3. 导致 schema context 在传递给底层 LLM service 之前就被丢弃了

---

## ✅ 解决方案

### 修复：合并所有 messages

**文件**: `app/services/infrastructure/agents/runtime.py`

#### 修改 1: 更新 `generate()` 方法

```python
# ✅ 修复后：合并所有 messages
async def generate(self, messages: List[Dict]) -> str:
    """
    生成 LLM 响应

    🔥 关键改进：合并所有 messages（包括 Loom 注入的 system messages）
    这样可以确保 ContextRetriever 注入的 schema context 被传递给 LLM
    """
    # 🔥 合并所有 messages 为一个完整的 prompt
    prompt = self._compose_full_prompt(messages)
    user_id = self._extract_user_id(messages)

    self._logger.info(f"🧠 [ContainerLLMAdapter] Composed prompt length: {len(prompt)} chars")
    self._logger.debug(f"   Message count: {len(messages)}, user_id: {user_id}")

    response = await self._service.ask(
        user_id=user_id,
        prompt=prompt,  # ✅ 包含 system messages（schema context）
        ...
    )
```

#### 修改 2: 新增 `_compose_full_prompt()` 方法

```python
def _compose_full_prompt(self, messages: List[Dict]) -> str:
    """
    合并所有 messages 为一个完整的 prompt

    🔥 关键功能：确保 Loom 注入的 system messages（schema context）被包含

    支持的 message 类型：
    - system: 系统指令（包括 ContextRetriever 注入的 schema）
    - user: 用户输入
    - assistant: 助手响应
    - tool: 工具执行结果
    """
    sections = []

    # 1. 收集所有 system messages（包括 schema context）
    system_messages = [
        m.get("content", "")
        for m in messages
        if m.get("role") == "system" and m.get("content")
    ]

    if system_messages:
        # 🔥 Schema context 会在这里被包含！
        system_content = "\n\n".join(system_messages)
        self._logger.debug(f"📋 System messages count: {len(system_messages)}, length: {len(system_content)} chars")
        sections.append("# SYSTEM INSTRUCTIONS\n\n" + system_content)

    # 2. 收集对话历史（user, assistant, tool）
    conversation = []
    for m in messages:
        role = m.get("role")
        content = m.get("content", "")

        if role == "user":
            conversation.append(f"# USER\n{content}")
        elif role == "assistant":
            conversation.append(f"# ASSISTANT\n{content}")
        elif role == "tool":
            tool_name = m.get("name", "unknown")
            conversation.append(f"# TOOL RESULT ({tool_name})\n{content}")

    if conversation:
        sections.append("\n\n".join(conversation))

    # 3. 合并所有部分
    separator = "\n\n" + "=" * 80 + "\n\n"
    full_prompt = separator.join(sections)

    return full_prompt
```

### 修复效果

**修复前**：
```
LLM 接收到的 prompt:
"生成一个SQL查询..."  [~500 chars]
```

**修复后**：
```
LLM 接收到的 prompt:
# SYSTEM INSTRUCTIONS

# 📊 数据表结构信息

## online_retail
- InvoiceNo (VARCHAR)
- StockCode (VARCHAR)
- Description (VARCHAR)
- ...

================================================================================

# USER
生成一个SQL查询...

[~5000 chars]  ← ✅ 包含完整的 schema context！
```

---

## 📊 预期日志变化

### 修复前（❌ 缺失的日志）

```
📊 [StaticContextAssembler] Token usage: 916/16000
   Components: 0 included  ← ❌

[没有 format_documents 调用日志]
[没有 SchemaAssembler 日志]
[没有 ContainerLLMAdapter prompt length 日志]

API调用成功，响应时间: 2429ms
SQL: SELECT ... FROM sales ...  ← ❌ 错误的表名
⚠️ 表 'sales' 不存在  ← ❌ 验证失败
```

### 修复后（✅ 预期日志）

```
📊 [StaticContextAssembler] Token usage: 916/16000
   Summary keys: [...]
   Full summary: {...}

📝 [ContextRetriever.format_documents] 被Loom调用，收到 1 个文档
📊 [SchemaAssembler] Token usage: 850/4000
   Components: 3 included, 0 truncated

🧠 [ContainerLLMAdapter] Composed prompt length: 5234 chars  ← ✅ 新增
   Message count: 2, user_id: ...
📋 System messages count: 1, length: 3456 chars  ← ✅ 新增

API调用成功，响应时间: 2500ms
SQL: SELECT ... FROM online_retail ...  ← ✅ 正确的表名
✅ SQL 列验证通过  ← ✅ 验证成功
```

---

## 🧪 测试验证

### 验证点 1: 检查日志

```bash
grep "ContainerLLMAdapter.*Composed prompt length" logs/*.log
grep "System messages count" logs/*.log
```

预期输出：
```
🧠 [ContainerLLMAdapter] Composed prompt length: 5000+ chars
📋 System messages count: 1, length: 3000+ chars
```

### 验证点 2: 检查 SQL 生成

**预期**：生成的 SQL 应该使用实际存在的表名（`online_retail`），而不是臆造的表名（`sales`）。

### 验证点 3: 检查验证结果

**预期**：SQL 列验证应该通过，不再出现"表不存在"的错误。

---

## 📋 Checklist

- [x] 修复 ContainerLLMAdapter.generate() 只提取 user message 的问题
- [x] 新增 _compose_full_prompt() 合并所有 messages
- [x] 添加详细日志记录 prompt 长度和 system messages
- [x] 添加调试日志记录 ContextAssembler summary
- [ ] 测试验证 schema context 确实被传递给 LLM
- [ ] 验证 SQL 生成使用正确的表名
- [ ] 验证 SQL 列验证通过
- [ ] 监控生产环境日志

---

## 🔗 相关文档

- [CONTEXT_ASSEMBLY_RECURSIVE_DESIGN.md](./CONTEXT_ASSEMBLY_RECURSIVE_DESIGN.md) - 递归模式架构设计
- [CONTEXT_ASSEMBLY_IMPLEMENTATION_SUMMARY.md](./CONTEXT_ASSEMBLY_IMPLEMENTATION_SUMMARY.md) - 实现总结

---

**作者**: AI Assistant
**审核**: 待定
**最后更新**: 2025-10-26
