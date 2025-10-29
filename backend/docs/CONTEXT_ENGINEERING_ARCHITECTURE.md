# Context 工程架构 - 完整分析

## 🎯 核心认知

**Context 是构成 Agent System 的唯一工程**
- 所有给到大模型的提示都基于 Context 实现
- Context 的组织方式直接决定 Agent 的行为质量
- 不存在独立的 "system prompt"，一切都是 Context

---

## 📊 Context 工程的双层架构

你们的系统采用了 **双层 Context 架构**：

### Layer 1: Static Context（静态上下文）

**位置**: `facade.py:157-187` - `_compose_prompt()`

**机制**:
```python
def _compose_prompt(self, request: AgentRequest) -> str:
    # 1. 将 request.context 转为 JSON
    context_json = json.dumps(request.context, ensure_ascii=False, indent=2)

    # 2. 组装到 User Prompt
    sections = [
        "你是AutoReport的智能分析助手...",
        f"### 执行阶段\n{request.stage}",
        f"### 工作模式\n{request.mode}",
        f"### 用户需求\n{request.prompt}",
        f"### 可用工具\n{tool_section}",
        f"### 上下文信息\n{context_json}"  # ← Static Context
    ]
    return "\n\n".join(sections)
```

**内容**:
```json
{
  "placeholder": {...},
  "task_context": {...},
  "constraints": {...},
  "data_source": {...},
  "task_driven_context": {...},
  "available_tools": [...],
  "system_config": {...}
}
```

**特点**:
- ✅ 包含任务级别的配置和参数
- ✅ 结构化信息（JSON 格式）
- ❌ 位置靠后（在 prompt 末尾）
- ❌ 深层嵌套，不够醒目
- ❌ 缺少 Schema 详情（只有 data_source_id）

---

### Layer 2: Dynamic Context（动态上下文）

**位置**: `runtime.py:247-249` + Loom Context Retriever

**机制**:
```python
# 1. Runtime 创建时接收 context_retriever
agent_kwargs["context_retriever"] = context_retriever

# 2. Loom 在每次 LLM 调用前自动执行
documents = await context_retriever.retrieve(query)
formatted_context = context_retriever.format_documents(documents)

# 3. 根据 inject_as 参数注入
if inject_as == "system":
    # 注入到 system message（优先级高）
    system_message += "\n\n" + formatted_context
else:
    # 注入到 user message
    user_message = formatted_context + "\n\n" + user_message
```

**内容**:
```markdown
# 📊 数据表结构信息

⚠️⚠️⚠️ **关键约束** ⚠️⚠️⚠️

你**必须且只能**使用以下列出的表和列...

## 可用的数据表

### 表 1/1: `online_retail`
- InvoiceNo (varchar)
- StockCode (varchar)
- InvoiceDate (datetimev2)
...
```

**特点**:
- ✅ 实时检索，动态注入
- ✅ 内容醒目，强调约束
- ✅ 可注入到 system message（优先级高）
- ✅ 包含完整 Schema 详情
- ⚠️ 需要被正确启用

---

## 🔄 Context 完整流转链路

### 步骤 1: Context 构建（Application Layer）

**位置**: `placeholder_service.py`

```python
# 构建 Static Context
agent_input = AgentInput(
    user_prompt=task_prompt,
    placeholder=PlaceholderSpec(...),
    schema=schema_info,  # ← 这里传了 schema，但...
    context=TaskContext(...),
    data_source=data_source_config,
    task_driven_context={...},
    user_id=self.user_id
)
```

**问题**:
- `schema_info` 只在某些场景传入
- 即使传入，也只是静态的数据结构
- 不包含完整的表列详情

---

### 步骤 2: Context 转换（Facade Layer）

**位置**: `facade.py:189-222`

```python
async def execute(self, request: AgentInput) -> AgentResponse:
    # 1. 转换为 AgentRequest
    request_obj = agent_input_to_request(request)

    # 2. 组装 User Prompt（包含 Static Context）
    prompt = self._compose_prompt(request_obj)

    # 3. 调用 Runtime（Dynamic Context 在这里注入）
    raw_output = await self._runtime.run(
        prompt,
        user_id=request_obj.user_id,
        stage=request_obj.stage,
        output_kind=...
    )
```

**Context 汇聚点**:
```
User Prompt = Static Context (JSON) + 用户需求 + 工具列表
              ↓
         Loom Runtime
              ↓
Dynamic Context (Schema) 注入 ← Context Retriever
              ↓
         Final Prompt to LLM
```

---

### 步骤 3: Dynamic Context 检索（Runtime Layer）

**位置**: Loom 内部 + `context_retriever.py`

```python
# Loom 内部流程（简化）
async def run(self, prompt: str, **kwargs):
    # 1. 检索 context
    if self.context_retriever:
        docs = await self.context_retriever.retrieve(prompt)
        formatted = self.context_retriever.format_documents(docs)

        # 2. 注入到 messages
        if inject_as == "system":
            system_message = system_instructions + "\n\n" + formatted
        else:
            prompt = formatted + "\n\n" + prompt

    # 3. 调用 LLM
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]
    response = await llm.generate(messages)
```

---

## 🔍 当前问题诊断

### 从日志看到的流程

```
[14:18:48.121] 📋 Context retriever enabled: True
[14:18:48.122] 🔍 [ContextRetriever.retrieve] 被Loom调用
[14:18:48.122] ✅ [SchemaContextRetriever] 检索到 1 个相关表
[14:18:48.122]    返回的表: ['online_retail']
[14:18:48.122] ✅ [ContextRetriever] 检索完成，返回 1 个相关表结构
[14:18:48.122] 📋 [完整上下文内容] - 这是将要传递给 Agent 的上下文:
================================================================================
### 表: online_retail
**列信息**:
- **InvoiceNo** (varchar(255))
- **StockCode** (varchar(255))
- **InvoiceDate** (datetimev2(0))
...
⚠️ **重要提醒**：请只使用上述表和列，不要臆造不存在的表名或列名！
================================================================================

[14:18:51.087] ✅ Agent生成SQL完成:
    SELECT * FROM sales WHERE sale_date BETWEEN {{start_date}} AND {{end_date}}
                      ^^^^^ 臆造的表！   ^^^^^^^^^^ 臆造的列！
```

### 问题定位

#### ✅ Context Retriever 正常工作
- 检索到了 `online_retail` 表
- 格式化了完整的列信息
- 返回了正确的 Schema Context

#### ❌ Agent 忽略了 Schema Context

可能的原因：

**1. Schema Context 的优先级不够高**

从日志看不出 Schema Context 是注入到 system message 还是 user message。

需要检查：
```python
context_retriever = ContextRetriever(
    retriever=stage_aware_retriever,
    top_k=5,
    inject_as="system"  # ← 这个参数是否生效？
)
```

**2. Static Context 中的信息干扰**

User Prompt 中的 Static Context（JSON）可能包含了混淆信息：
```json
{
  "task_driven_context": {
    "business_command": "周期：数据时间范围",
    "requirements": "为占位符 周期：数据时间范围 生成SQL"
  }
}
```

这个需求太模糊，没有提到具体要查询什么表。

**3. Schema Context 的格式不够强制**

虽然有提醒，但可能不够醒目：
```
⚠️ **重要提醒**：请只使用上述表和列，不要臆造不存在的表名或列名！
```

vs. 优化后：
```
⚠️⚠️⚠️ **关键约束 - 请务必遵守** ⚠️⚠️⚠️
你**必须且只能**使用以下列出的表和列。
**禁止臆造任何不存在的表名或列名！**
**违反此约束将导致**：
- ❌ SQL 语法错误
- ❌ 执行失败
```

---

## ✅ 优化方案（基于 Context 工程）

### 方案 1: 强化 Dynamic Context 优先级 🔴

#### 1.1 确保注入到 System Message

**检查点**:
```python
# placeholders.py 或初始化 context_retriever 的地方
context_retriever = ContextRetriever(
    retriever=stage_aware_retriever,
    top_k=5,
    auto_retrieve=True,
    inject_as="system"  # 🔥 确保这个参数生效
)
```

**验证方法**:
在日志中添加：
```python
logger.info(f"Context Retriever inject_as: {context_retriever.inject_as}")
```

#### 1.2 优化 Schema Context 格式

**已完成** ✅: `context_retriever.py:402-506` 已优化
- 前置多层强调
- 明确禁止臆造
- 说明违反后果

---

### 方案 2: 简化 Static Context 🟠

#### 2.1 减少 JSON Context 的干扰

**位置**: `facade.py:157-187`

**优化思路**:
```python
def _compose_prompt(self, request: AgentRequest) -> str:
    # ❌ 当前：将整个 context 转为 JSON
    context_json = json.dumps(request.context, ...)

    # ✅ 优化：只保留关键信息，避免干扰
    essential_context = {
        "task_type": request.context.get("task_driven_context", {}).get("mode"),
        "data_source_id": request.context.get("data_source", {}).get("id"),
        # 移除 available_tools（已通过 tool_section 展示）
        # 移除 system_config（不需要给 Agent）
        # 移除 schema（由 Dynamic Context 提供）
    }
    context_json = json.dumps(essential_context, ...)
```

**效果**:
- 减少 JSON 噪音
- 突出 Schema Context 的重要性

---

### 方案 3: 改进业务需求描述 🟡

#### 3.1 增强 task_prompt 的明确性

**位置**: `placeholder_service.py:141-200`

**问题**:
```python
task_prompt = f"""
### 业务需求
周期：数据时间范围  # ← 太模糊

### 具体目标
为占位符 周期：数据时间范围 生成SQL  # ← 没有说明查询什么
```

**优化**:
```python
task_prompt = f"""
### 业务需求
{request.business_command}

### 具体目标
{request.target_objective or request.requirements}

### ⚠️ 数据约束
**你只能使用以下数据源中的表**：
- 数据源ID: {data_source_config.get('data_source_id')}
- 数据库: {data_source_config.get('database_name')}

**详细表结构将在下方的「数据表结构信息」中提供，请严格遵守！**

{time_window_desc}
```

**效果**:
- 在 User Prompt 中也强调了数据约束
- 引导 Agent 关注 Schema Context

---

## 🧪 验证和测试

### 测试 1: 检查 Context 注入位置

**添加日志**:

```python
# runtime.py or context_retriever.py
logger.info("=" * 80)
logger.info(f"Context 注入位置: {inject_as}")
logger.info(f"Context 将被注入到: {'System Message' if inject_as == 'system' else 'User Message'}")
logger.info("=" * 80)
```

### 测试 2: 检查最终 Prompt 结构

**添加日志**:

```python
# Loom 内部或 facade.py
logger.info("=" * 80)
logger.info("最终发送给 LLM 的 Messages:")
logger.info("=" * 80)
for msg in messages:
    logger.info(f"Role: {msg['role']}")
    logger.info(f"Content (前500字符): {msg['content'][:500]}")
    logger.info("-" * 80)
```

### 测试 3: A/B 对比测试

**场景 A**: 使用当前 Context 配置
**场景 B**: 使用优化后的 Context 配置

对比指标：
- SQL 生成准确率
- 表名正确率
- 列名正确率
- 时间占位符格式正确率

---

## 📊 Context 工程优化路线图

### Phase 1: 验证和诊断（1-2 小时）
- [ ] 确认 Context Retriever inject_as 参数
- [ ] 添加日志跟踪 Context 注入位置
- [ ] 检查最终 LLM Messages 结构

### Phase 2: 优化 Dynamic Context（已完成 ✅）
- [x] 强化 Schema Context 格式化
- [x] 多层强调约束
- [x] 明确禁止臆造

### Phase 3: 简化 Static Context（可选）
- [ ] 精简 JSON Context
- [ ] 突出关键信息
- [ ] 移除干扰信息

### Phase 4: 增强业务需求（推荐）
- [ ] 改进 task_prompt 明确性
- [ ] 在 User Prompt 中引导 Agent
- [ ] 强调 Schema Context 重要性

### Phase 5: 测试和验证（必须）
- [ ] A/B 对比测试
- [ ] 统计准确率提升
- [ ] 收集用户反馈

---

## 💡 核心洞察

### Context 工程的本质

**不是**：给 Agent 提供信息
**而是**：**引导** Agent **优先关注** 正确的信息

### Context 的三要素

1. **内容** (What)：提供什么信息
2. **位置** (Where)：信息放在哪里（system vs user, 前 vs 后）
3. **格式** (How)：如何呈现信息（醒目 vs 平淡）

### 当前问题的根源

| 要素 | 当前状态 | 理想状态 |
|------|----------|----------|
| **内容** | ✅ Schema 信息完整 | ✅ 已满足 |
| **位置** | ⏳ 不确定（需验证 inject_as） | System Message 开头 |
| **格式** | ✅ 已优化（多层强调） | ✅ 已改进 |

**结论**：重点检查 **位置** 要素！

---

## 🎯 下一步行动

### 立即执行（最关键！）

1. **验证 Context Retriever 的 inject_as 参数**
   ```bash
   cd backend
   grep -r "inject_as" app/services/
   ```

2. **添加日志跟踪 Context 注入位置**
   - 在 `context_retriever.py` 或 Loom 内部
   - 记录 Context 被注入到哪个 message role

3. **检查最终 LLM Messages**
   - 在 `runtime.py` 或 Loom 调用前
   - 打印完整的 messages 结构

### 如果发现问题

**问题 A**: Context 没有注入到 System Message
**解决**: 确保 `inject_as="system"` 并检查 Loom 实现

**问题 B**: Static Context JSON 干扰 Schema Context
**解决**: 精简 JSON，只保留关键信息

**问题 C**: 业务需求太模糊
**解决**: 改进 task_prompt，明确查询目标

---

## 📁 相关文件

### Context 构建
- `placeholder_service.py:141-200` - Task Prompt 构建
- `facade.py:157-187` - Static Context 组装

### Context 检索
- `context_retriever.py` - Dynamic Context 检索和格式化
- `context_manager.py` - Stage-aware Context 管理

### Context 注入
- `runtime.py:247-249` - Context Retriever 传递
- Loom 内部 - Context 实际注入逻辑（需要查看 Loom 源码）

---

这份文档完整解析了你们的 **Context 工程架构**，现在可以精准定位问题并优化！
