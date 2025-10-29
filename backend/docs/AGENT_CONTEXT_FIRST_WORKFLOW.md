# 🎯 Agent 上下文优先工作流实现报告

## 📋 概述

本文档记录了Agent系统从"工具优先"到"上下文优先"的工作流优化过程，确保Agent在执行SQL生成任务时，优先分析系统注入的Schema上下文，然后再使用工具进行深入探索。

---

## 🎯 目标

**用户需求：**
> "我们加载了上下文，能不能第一次循环的时候让agent需要参考上下文来分析，然后使用工具进一步分析，在生成sql，和校验"

**翻译：**
- 第一步：Agent分析系统预加载的Schema上下文
- 第二步：使用工具进行进一步探索（如需要）
- 第三步：生成SQL查询
- 第四步：验证SQL正确性

---

## 🔍 背景问题分析

### 问题1: 工具注册但从不调用

**症状：**
```
📦 [ToolRegistry] 共创建 13 个工具
❌ 未使用任何工具
📊 质量评分: 0.52 (F级)
💡 建议: 未使用任何工具，建议使用 Schema 和 SQL 工具提高准确性
```

**根本原因：**
`ContainerLLMAdapter` 缺少 `supports_tools` 属性覆盖：
```python
# ❌ 原始代码（继承BaseLLM默认）
@property
def supports_tools(self) -> bool:
    return False  # BaseLLM默认值
```

**影响链：**
1. `supports_tools = False`
2. → Loom AgentExecutor 调用 `generate()` 而非 `generate_with_tools()`
3. → 工具调用指令未注入到prompt
4. → LLM不知道应该返回 `{"action": "tool_call"}` 格式
5. → Agent认为任务完成，TT循环仅1次迭代
6. → 工具从未被调用

**修复：**
```python
# ✅ 修复后的代码
@property
def supports_tools(self) -> bool:
    """🔥 关键修复：标记此LLM支持工具调用

    这会让Loom的AgentExecutor调用generate_with_tools()而不是generate()
    从而注入工具调用指令，使LLM能够正确调用工具
    """
    return True
```

**文件位置：** `backend/app/services/infrastructure/agents/llm_adapter.py:74-80`

---

### 问题2: 缺乏明确的执行工作流

即使工具可以被调用，Agent也没有明确的指导：
- 何时应该先分析上下文
- 何时应该调用工具
- 如何设计完整的SQL生成流程

**结果：**
- Agent行为不可预测
- 可能跳过上下文分析直接生成SQL
- 可能过度使用工具

---

## ✅ 解决方案：上下文优先工作流

### 1. 增强基础系统Prompt

**文件：** `backend/app/services/infrastructure/agents/prompts/system.py:77-126`

**添加内容：**

```markdown
### 1. 上下文优先原则（🔥 最重要！）

**在调用任何工具之前，必须先仔细分析系统已经注入的上下文信息！**

系统会自动为你注入以下上下文：
- **Schema Context**: 数据库表结构、字段信息、关系等
- **Task Context**: 任务相关的业务信息和约束
- **Template Context**: 模板和格式要求

**工作流程：**
1. 📖 **第一步：阅读和理解上下文** - 仔细分析已有信息
2. 🤔 **第二步：识别信息缺口** - 判断是否需要更多信息
3. 🔧 **第三步：使用工具补充** - 仅在必要时调用工具
4. ✅ **第四步：执行任务** - 基于完整信息完成任务

**示例（推荐）：**
```
思考：系统上下文显示有return_requests表，包含以下字段：
- id (主键)
- customer_id (外键)
- request_date (时间戳)
- status (状态)

但我需要了解status字段的可能值，使用data_sampler获取样本数据...
```

**❌ 错误做法：**
```
思考：需要查询退货申请数量，立即生成SQL...
（错误：没有先分析上下文中已有的Schema信息）
```
```

**关键点：**
- 将"上下文优先"提升为最重要的工作原则
- 提供具体的4步工作流程
- 给出正确和错误的示例对比

---

### 2. 详细的SQL生成阶段6步工作流

**文件：** `backend/app/services/infrastructure/agents/prompts/system.py:203-326`

**添加内容：**

```markdown
## SQL 生成阶段指导

**🔥 重要：必须按以下顺序执行，不要跳过任何步骤！**

### 第一步：分析已加载的Schema上下文（必须！）

在开始任何操作之前，**仔细分析系统已经为你注入的Schema上下文信息**：
- 查看上下文中包含哪些表（tables）
- 理解每个表的字段（columns）、数据类型（data_type）
- 识别主键（primary_key）和外键（foreign_key）关系
- 理解字段的业务含义和约束（nullable, default_value）

**不要立即生成SQL！先确保你完全理解了数据结构。**

### 第二步：使用工具进一步探索（如需要）

如果上下文信息不够详细，或你需要更多信息，使用以下工具：
- `schema_retrieval`: 获取特定表的详细结构信息
- `schema_cache`: 查询缓存的Schema信息
- `data_sampler`: 获取数据样本，了解实际数据内容

**示例工具调用：**
```json
{
  "reasoning": "上下文显示有return_requests表，但我需要了解其详细字段信息",
  "action": "tool_call",
  "tool_calls": [
    {
      "name": "schema_retrieval",
      "arguments": {
        "table_names": ["return_requests"],
        "include_sample_data": true
      }
    }
  ]
}
```

### 第三步：设计查询逻辑

基于完整的Schema信息，设计SQL查询：
- 确定需要哪些表
- 选择正确的字段
- 设计JOIN条件（如果多表）
- 确定WHERE过滤条件
- 设计聚合和分组逻辑（如需要）

**在脑海中模拟查询执行，确保逻辑正确。**

### 第四步：生成SQL查询

使用 `sql_generator` 工具生成SQL，或直接编写。

### 第五步：验证SQL正确性

生成SQL后，**必须使用工具验证**：
- `sql_validator`: 检查语法正确性
- `sql_column_checker`: 验证字段是否存在、类型是否匹配

### 第六步：返回最终SQL

验证通过后，返回最终结果。

**✅ 正确示例（推荐）：**
1. 分析上下文 → 2. 使用schema工具 → 3. 生成SQL → 4. 验证SQL → 5. 返回结果

**❌ 错误示例（不要这样做）：**
```json
{
  "action": "finish",
  "content": {
    "sql_query": "SELECT COUNT(*) FROM some_table"
  }
}
```
这是错误的，因为：
1. 没有先分析Schema上下文
2. 没有使用工具探索数据结构
3. 没有验证SQL的正确性
4. 可能使用了不存在的表或字段
```

**关键点：**
- 明确的6步顺序，禁止跳过
- 每一步都有详细的指导和示例
- 强调"不要立即生成SQL"
- 提供正确和错误的完整示例对比

---

## 📊 预期效果

### 修复前 vs 修复后

| 指标 | 修复前 | 修复后（预期） |
|------|--------|----------------|
| **工具调用** | 0 次 | ≥3 次 (schema + sql + validate) |
| **TT迭代次数** | 1 次 | 3-8 次 |
| **质量评分** | 0.52 (F级) | ≥0.7 (C级或更高) |
| **上下文利用** | 未使用 | 优先分析 |
| **SQL准确性** | 低 | 高 |
| **执行流程** | 混乱 | 清晰的6步流程 |

### 日志输出示例（预期）

```
🎯 [SQL生成阶段] 开始执行（TT递归模式）
📖 [Agent] 第一步：分析Schema上下文
   - 发现 return_requests 表
   - 字段: id, customer_id, request_date, status, ...
   - 主键: id
🔧 [Agent] 第二步：使用工具探索
   - 调用 schema_retrieval 获取详细信息
   - 调用 data_sampler 了解 status 字段的值
🤔 [Agent] 第三步：设计查询逻辑
   - 需要统计总数 → 使用 COUNT(*)
   - 单表查询 → 不需要 JOIN
✍️ [Agent] 第四步：生成SQL
   - SQL: SELECT COUNT(*) AS total_requests FROM return_requests
🔍 [Agent] 第五步：验证SQL
   - 调用 sql_validator: ✅ 语法正确
   - 调用 sql_column_checker: ✅ 表和字段存在
✅ [Agent] 第六步：返回最终结果
📊 [质量评分] 总体评分: 0.85 (B级)
   - SQL语法: 1.0
   - 语义正确性: 0.9
   - 工具使用: 0.8
   - 上下文利用: 0.9
```

---

## 🧪 测试验证计划

### 1. 功能测试

**测试脚本：** 创建 `scripts/test_context_first_workflow.py`

**测试用例：**
```python
async def test_context_first_workflow():
    """测试上下文优先工作流"""

    # 创建Runtime
    runtime = build_stage_aware_runtime(
        container=container,
        config=config
    )

    # 执行SQL生成任务
    request = AgentRequest(
        placeholder="统计退货申请的总数",
        data_source_id=1,
        user_id="test_user",
        stage=ExecutionStage.SQL_GENERATION
    )

    # 收集执行事件
    events = []
    async for event in runtime.execute_with_stage(request, ExecutionStage.SQL_GENERATION):
        events.append(event)
        print_event_summary(event)

    # 验证
    assert_tool_calls_made(events, expected_tools=['schema_retrieval', 'sql_validator'])
    assert_quality_score_improved(events, min_score=0.7)
    assert_iterations_count(events, min_iterations=3)
```

**验证点：**
1. ✅ `supports_tools=True` 生效，调用 `generate_with_tools()`
2. ✅ 工具调用指令被注入到prompt
3. ✅ Agent返回 `{"action": "tool_call"}` 格式
4. ✅ Schema工具被调用（schema_retrieval, schema_cache）
5. ✅ SQL验证工具被调用（sql_validator, sql_column_checker）
6. ✅ TT递归执行多次迭代（≥3次）
7. ✅ 质量评分提升到 ≥0.7
8. ✅ Agent遵循6步工作流程

---

### 2. 日志监控

**关键日志标记：**
```
✅ 正向信号:
- "📖 [Agent] 第一步：分析Schema上下文"
- "🔧 [Agent] 调用工具: schema_retrieval"
- "🔧 [Agent] 调用工具: sql_validator"
- "📊 [质量评分] 总体评分: 0.8+"
- "🔄 [TT递归] 第 N 次迭代 (N ≥ 3)"

❌ 负向信号:
- "未使用任何工具"
- "质量评分: 0.5-"
- "TT递归仅 1 次迭代"
- "Agent结果为 None"
```

---

## 📁 修改文件清单

### 1. 核心修复

| 文件 | 修改内容 | 行号 |
|------|----------|------|
| `llm_adapter.py` | 添加 `supports_tools=True` 属性 | 74-80 |
| `prompts/system.py` | 添加"上下文优先原则"到基础prompt | 77-126 |
| `prompts/system.py` | 增强SQL生成阶段6步工作流 | 203-326 |

### 2. 相关文件（之前修复）

| 文件 | 修改内容 |
|------|----------|
| `runtime.py` | 添加 `_create_tools_from_config()` 工具自动注册 |
| `runtime.py` | 在 `execute_with_tt()` 中设置 `_CURRENT_USER_ID` |
| `types.py` | 修改 `TaskComplexity` 为 float 枚举 |

---

## 🎓 关键经验总结

### 1. LLM适配器必须正确标记能力

**问题：**
- Loom框架通过 `supports_tools` 属性判断LLM是否支持工具调用
- 如果返回 `False`，框架不会注入工具调用指令

**教训：**
- 实现自定义LLM适配器时，必须正确覆盖所有能力标记属性
- 不能依赖基类的默认值

### 2. 系统Prompt是行为的契约

**问题：**
- Agent的行为完全由系统prompt定义
- 模糊的指令导致不可预测的行为

**教训：**
- 使用明确的步骤顺序（第一步、第二步...）
- 提供具体的示例和反例
- 强调关键原则（如"不要立即生成SQL"）

### 3. 上下文注入需要显式利用

**问题：**
- 系统通过ContextRetriever注入了Schema上下文
- 但Agent没有被明确告知"必须先读取上下文"

**教训：**
- 上下文注入 ≠ 上下文利用
- 需要在prompt中显式指导Agent使用上下文

### 4. 工具注册 ≠ 工具使用

**问题：**
- 工具成功注册到Agent
- 但Agent从未调用它们

**教训：**
- 确保框架支持工具调用（`supports_tools=True`）
- 确保prompt中有工具调用指令
- 确保LLM理解工具调用协议

---

## 🚀 下一步

### 立即行动

1. **运行测试**
   ```bash
   cd backend
   python scripts/test_context_first_workflow.py
   ```

2. **监控日志**
   - 查看是否出现 "📖 第一步：分析Schema上下文"
   - 查看工具调用次数
   - 查看质量评分变化

3. **验证效果**
   - 对比修复前后的质量评分
   - 检查SQL生成的准确性
   - 确认Agent遵循6步流程

### 后续优化

1. **上下文注入优化**
   - 优化ContextRetriever的注入格式
   - 确保关键信息突出显示

2. **工具调用监控**
   - 添加工具调用统计
   - 分析工具使用模式

3. **质量评分细化**
   - 添加"上下文利用率"维度
   - 添加"工作流遵守度"维度

---

## 📚 相关文档

- [BUG_FIX_TOOL_REGISTRATION.md](./BUG_FIX_TOOL_REGISTRATION.md) - 工具注册机制修复
- [AGENT_ARCHITECTURE_REFACTORING_COMPLETE.md](./AGENT_ARCHITECTURE_REFACTORING_COMPLETE.md) - Agent架构重构
- [THREE_STAGE_AGENT_ARCHITECTURE.md](./THREE_STAGE_AGENT_ARCHITECTURE.md) - 三阶段Agent架构

---

**修复完成日期:** 2025-01-28
**修复人:** AI Assistant
**验证状态:** ⏳ 待测试

**关键成就:**
- ✅ 修复 `supports_tools` 属性，使工具调用生效
- ✅ 建立"上下文优先"工作原则
- ✅ 设计详细的6步SQL生成工作流
- ✅ 提供清晰的正确/错误示例

**预期提升:**
- 质量评分从 0.52 → ≥0.7 (提升 35%+)
- 工具调用从 0 次 → ≥3 次
- TT迭代从 1 次 → 3-8 次
- SQL准确性显著提升
