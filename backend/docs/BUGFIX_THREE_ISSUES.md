# 🐛 三个关键问题修复

## 📋 问题总结

### 问题1：LLM 模型选择冲突 ❌
- 自主选择了 `gpt-4`
- 但实际使用了 `gpt-3.5-turbo`
- **原因**：多个模型选择逻辑冲突

### 问题2：Schema Context Retriever 返回0个表 ❌  
- 能发现19个表和294个列
- 但检索时返回0个表
- **原因**：阶段感知缓存了空结果

### 问题3：工具结果未传递到下一轮 ❌
- LLM 重复调用相同工具
- 没有基于工具结果前进
- **原因**：没有配置 Memory

---

## 🔧 修复方案

### ✅ 修复1：添加 Memory 支持

**问题根因**：
Loom 的 TT 递归需要 memory 来保存对话历史，否则：
- 工具结果无法在下一轮传递
- LLM 看不到之前的消息
- 递归无法正常工作

**修复代码** (`runtime.py:732-754`)：
```python
from loom.memory import InMemoryMessageMemory

agent_kwargs = {
    "llm": llm,
    "tools": tools,
    "memory": InMemoryMessageMemory(),  # 🔥 关键！
    "max_iterations": config.max_iterations,
    "max_context_tokens": config.max_context_tokens,
}
```

**预期效果**：
- ✅ Loom 自动保存每轮对话
- ✅ 工具结果被包含在下一轮 LLM 调用中
- ✅ 递归正常工作

---

### ✅ 修复2：修复阶段感知缓存Bug

**问题根因**：
1. 阶段感知缓存会缓存空结果
2. 当查询文本无法匹配表时（如Loom的递归指导消息），返回空列表
3. 这个空列表被缓存
4. 后续查询直接返回缓存的空列表

**修复代码** (`context_retriever.py:382-405`)：
```python
# 检查阶段感知缓存
if self.enable_stage_aware:
    cache_key = f"{query[:100]}_{top_k}"
    if cache_key in self.stage_context_cache:
        cached_docs = self.stage_context_cache[cache_key]
        # 🔥 不要返回空缓存
        if len(cached_docs) > 0:
            return cached_docs
        else:
            # 清除空缓存，重新检索
            del self.stage_context_cache[cache_key]
    
    # 🔥 仅当结果非空时才缓存
    if len(documents) > 0:
        self.stage_context_cache[cache_key] = documents
```

**预期效果**：
- ✅ 空结果不会被缓存
- ✅ 即使第一次检索失败，后续仍会重试
- ✅ 提高检索成功率

---

### ✅ 修复3：改进降级策略

**问题根因**：
当查询文本（如"工具调用已完成。请基于返回的结果完成任务"）无法匹配任何表时，应该使用降级策略返回一些表，而不是返回空列表。

**修复代码** (`context_retriever.py:498-508`)：
```python
if not top_tables:
    # 改进降级策略
    logger.warning(f"⚠️ 没有表匹配查询关键词")
    if self.schema_cache:
        fallback_count = min(top_k, len(self.schema_cache))
        logger.info(f"   使用降级策略：返回前 {fallback_count} 个表")
        top_tables = [(name, info, 0.5) for name, info in list(self.schema_cache.items())[:fallback_count]]
    else:
        logger.error(f"   ❌ Schema缓存为空，无法提供降级策略")
        return []
```

**预期效果**：
- ✅ 即使无法匹配，也会返回前几个表
- ✅ LLM 至少能看到一些 schema 信息
- ✅ 提高Agent完成任务的成功率

---

### ⏳ 问题1待修复：LLM 模型选择

这个问题需要检查模型选择服务的实现，暂时保留，不影响核心功能。

---

## 📊 预期效果

修复后的执行流程：

```
1️⃣ 第一轮：
   🧠 LLM 生成: {"action": "tool_call", "tool_calls": ["schema_discovery"]}
   🔧 执行 schema_discovery
   ✅ 发现 19 个表
   💾 Memory 保存: [user message, assistant tool_call, tool result]

2️⃣ 递归（基于工具结果）：
   🔄 Loom 递归调用
   📝 查询: "工具调用已完成。请基于返回的结果完成任务"
   🔍 ContextRetriever 检索:
      - 无法匹配 -> 使用降级策略
      - 返回前5个表 ✅
   🧠 LLM 看到:
      - 工具结果（19个表）✅
      - Schema上下文（前5个表的详细信息）✅
   🧠 LLM 生成: {"action": "finish", "content": "SELECT ..."}

3️⃣ 完成：
   ✅ 返回 SQL
   📊 质量评分: 0.75+ (预计)
```

---

## 🎯 关键改进点

| 方面 | 修复前 | 修复后 |
|------|--------|--------|
| **Memory** | ❌ 未配置 | ✅ InMemoryMessageMemory |
| **工具结果传递** | ❌ 丢失 | ✅ 自动包含在下一轮 |
| **空缓存** | ❌ 被缓存并重复返回 | ✅ 不缓存，重新检索 |
| **降级策略** | ⚠️ 简单返回空 | ✅ 返回前N个表 |
| **递归** | ❌ 停滞 | ✅ 正常工作 |
| **质量评分** | 0.40 (F) | 0.75+ (预计C+/B) |

---

## 📝 测试建议

1. **验证递归**：
   - 检查日志中是否有多次 LLM_START 事件
   - 检查是否有 RECURSION 事件
   - 确认工具调用次数 > 1

2. **验证 Schema 检索**：
   - 检查递归时返回的表数量 > 0
   - 确认降级策略被触发时有日志

3. **验证质量评分**：
   - 质量评分应该提升到 0.7+
   - 工具使用评分不再为0

---

## 📅 修复记录

- **日期**: 2025-10-28
- **修复文件**:
  - `app/services/infrastructure/agents/runtime.py`
  - `app/services/infrastructure/agents/context_retriever.py`
- **影响范围**: Agent 递归执行、Schema 检索、质量评分
- **测试状态**: 待测试

