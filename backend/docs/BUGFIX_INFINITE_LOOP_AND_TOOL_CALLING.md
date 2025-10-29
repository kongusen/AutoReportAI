# 🐛 Bug 修复：无限循环和工具调用问题

## 📋 问题描述

### 观察到的现象
1. Agent 执行进入无限循环
2. 日志显示"继续处理任务：继续处理任务：..." 重复出现
3. 降级策略被错误触发："⚠️ LLM 没有调用任何工具"
4. 但实际上 LLM 正确调用了工具（schema_discovery）

### 日志分析
```
✅ LLM 返回: {"action": "tool_call", "tool_calls": [...]}
✅ 工具成功执行: 发现 19 个表和 294 个列
❌ 但日志显示: 解析后的 action: N/A
❌ 错误触发降级策略
❌ 进入无限循环
```

---

## 🔍 根本原因

### 问题1：使用了错误的 Loom API
**错误代码**：
```python
result = await self._agent.run(initial_prompt)  # ❌ 只返回字符串结果
```

**问题**：
- `agent.run()` 只返回最终的文本结果
- 无法获取中间的工具调用事件
- 导致 `tool_call_history` 始终为空

**正确做法**：
```python
async for event in self._agent.execute(initial_prompt):  # ✅ 返回事件流
    # 处理工具调用事件、LLM 输出等
```

### 问题2：调试日志位置错误
**错误代码**：
```python
result = self._parse_tool_response(response)
self._logger.info(f"解析后的 action: {result.get('action', 'N/A')}")  # ❌
```

**问题**：
- `action` 字段在解析过程的 `parsed` 变量中
- 最终的 `result` 只包含 `{content, tool_calls}`
- 所以 `result.get('action')` 始终返回 None

### 问题3：错误的降级策略检查
**错误代码**：
```python
if len(self._current_state.tool_call_history) == 0:
    logger.warning("⚠️ LLM 没有调用任何工具，尝试降级策略")
```

**问题**：
- 这个检查在使用 `agent.run()` 时总是为真
- 因为工具调用事件没有被捕获和记录

---

## 🔧 修复方案

### 修复1：使用 Loom 的事件流 API

**位置**：`app/services/infrastructure/agents/runtime.py:287-324`

**修改**：
```python
# ❌ 旧代码
result = await self._agent.run(initial_prompt)

# ✅ 新代码
from loom.core.events import AgentEventType

result = ""
tool_call_count = 0

async for event in self._agent.execute(initial_prompt):
    if event.type == AgentEventType.LLM_TOOL_CALLS:
        tool_count = event.metadata.get("tool_count", 0)
        tool_call_count += tool_count
        logger.info(f"🔧 LLM 调用了 {tool_count} 个工具")
    
    elif event.type == AgentEventType.LLM_DELTA:
        if event.content:
            result += event.content
    
    elif event.type == AgentEventType.AGENT_FINISH:
        result = event.content or result
        break
    
    elif event.type == AgentEventType.ERROR:
        raise event.error
```

### 修复2：更正调试日志

**位置**：`app/services/infrastructure/agents/llm_adapter.py:382`

**修改**：
```python
# ❌ 旧位置（在 _parse_tool_response 外部）
result = self._parse_tool_response(response)
self._logger.info(f"解析后的 action: {result.get('action', 'N/A')}")

# ✅ 新位置（在 _parse_tool_response 内部）
def _parse_tool_response(self, response: Any) -> Dict:
    ...
    action = parsed.get("action", "finish")
    self._logger.info(f"📝 [DEBUG] 解析后的 action: {action}")  # ← 正确位置
    ...
```

### 修复3：删除错误的降级策略

**位置**：`app/services/infrastructure/agents/runtime.py:333-335`

**修改**：
```python
# ❌ 删除这段代码
if len(self._current_state.tool_call_history) == 0:
    logger.warning("⚠️ LLM 没有调用任何工具，尝试降级策略")
```

**原因**：
- 现在我们通过事件流正确跟踪工具调用
- `tool_call_count` 变量包含准确的统计信息

### 修复4：改进日志输出

**位置**：`app/services/infrastructure/agents/llm_adapter.py:276-285`

**修改**：
```python
# 🔧 改进的日志输出
if isinstance(result, dict):
    tool_calls = result.get('tool_calls', [])
    
    if tool_calls:
        self._logger.info(f"✅ [ContainerLLMAdapter] 成功解析 {len(tool_calls)} 个工具调用")
        for i, tc in enumerate(tool_calls):
            self._logger.info(f"   工具 {i+1}: {tc.get('name')} (id: {tc.get('id')})")
    else:
        self._logger.info(f"✅ [ContainerLLMAdapter] LLM 返回最终答案（无工具调用）")
```

---

## ✅ 修复效果

### 预期改进
1. **无限循环解决** ✅
   - 正确处理 Loom 的事件流
   - Agent 能够正常完成执行

2. **工具调用统计准确** ✅
   - 通过 `AgentEventType.LLM_TOOL_CALLS` 事件追踪
   - 准确记录工具使用次数

3. **日志输出清晰** ✅
   - `action` 字段正确显示
   - 工具调用详情完整记录

4. **质量评分改善** ✅
   - 工具使用评分不再为 0
   - 整体质量评分应该提高到至少 0.7+

### 预期日志输出
```
✅ [ContainerLLMAdapter] 成功解析 1 个工具调用
   工具 1: schema_discovery (id: xxx)
🔧 [LoomAgentRuntime] LLM 调用了 1 个工具
🔧 [LoomAgentRuntime] 工具 schema_discovery: executing
✅ [LoomAgentRuntime] 工具执行完成
✅ [LoomAgentRuntime] Agent 执行完成
📊 [LoomAgentRuntime] 总工具调用次数: 1
```

---

## 📚 学习要点

### 1. Loom Agent API 的正确使用

**简单场景**：
```python
result = await agent.run(prompt)  # 只需要最终结果
```

**需要监控执行过程**：
```python
async for event in agent.execute(prompt):
    # 处理各种事件类型
    if event.type == AgentEventType.TOOL_RESULT:
        # 获取工具执行结果
    elif event.type == AgentEventType.AGENT_FINISH:
        # 获取最终答案
```

### 2. 事件驱动的执行模型

Loom 使用事件流来报告执行状态：
- `LLM_START` - LLM 开始生成
- `LLM_DELTA` - LLM 输出增量
- `LLM_TOOL_CALLS` - LLM 请求调用工具
- `TOOL_PROGRESS` - 工具执行中
- `TOOL_RESULT` - 工具执行完成
- `AGENT_FINISH` - Agent 完成

### 3. 调试技巧

**添加调试日志时**：
1. 在正确的变量作用域内
2. 记录原始数据和解析后的数据
3. 使用清晰的标识符（如 `[DEBUG]`）

**常见陷阱**：
```python
# ❌ 错误
parsed = json.loads(response)
action = parsed.get("action")
# ... 一些处理 ...
result = {"content": ..., "tool_calls": ...}
print(result.get("action"))  # 这里 action 已经不在 result 中了！

# ✅ 正确
parsed = json.loads(response)
action = parsed.get("action")
print(f"action: {action}")  # 在正确的作用域内记录
```

---

## 🎯 后续优化建议

1. **增强错误处理**
   - 捕获并记录所有 AgentEventType.ERROR 事件
   - 提供更详细的错误上下文

2. **添加 Metrics**
   - 记录工具调用成功率
   - 追踪迭代次数统计
   - 监控执行时间分布

3. **实现工具调用验证**
   - 检查工具调用是否合理
   - 防止重复调用相同工具
   - 提供智能提示

4. **优化 Prompt**
   - 根据实际工具使用情况调整
   - 添加更多示例
   - 简化工具描述

---

## 📅 修复记录

- **日期**: 2025-10-28
- **修复文件**:
  - `app/services/infrastructure/agents/runtime.py`
  - `app/services/infrastructure/agents/llm_adapter.py`
- **影响范围**: Agent 执行流程、工具调用统计、质量评分
- **测试建议**: 运行完整的占位符分析流程，验证无循环且工具正确执行

