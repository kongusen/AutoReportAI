# 基于 ContextRetriever 的架构替换方案

## 🎯 目标

**完全替换**当前基于工具调用的 schema 获取机制，改用 Loom ContextRetriever 的自动注入机制。

---

## 📋 替换清单

### 1️⃣ **替换：Schema 获取方式**

#### 移除
```python
# ❌ 旧方式：Agent 通过工具调用获取 schema
tools = [
    SchemaListTablesTool(),      # 删除
    SchemaListColumnsTool(),     # 删除
    # ...
]

# ❌ 旧 prompt：要求 Agent 调用工具
"""
- 如果 schema 不完整，调用 `schema.*` 系列工具补足
- 必须先调用 `schema.list_columns` 获取表的所有列名
"""
```

#### 替换为
```python
# ✅ 新方式：在初始化时创建 ContextRetriever
schema_context = create_schema_context_retriever(
    data_source_id=data_source_id,
    container=container,
    top_k=10
)
await schema_context.retriever.initialize()  # 预加载所有表结构

# ✅ 传递给 Agent
agent_service = AgentService(
    container=container,
    context_retriever=schema_context
)

# ✅ 新 prompt：告知 Agent 信息已提供
"""
## 📊 可用表结构（已自动注入）
你可以直接看到相关表和列的信息，无需调用工具。
请仔细阅读 system message 中的表结构，只使用已列出的表和列。
"""
```

---

### 2️⃣ **替换：工具列表**

#### 移除的工具
```python
# backend/app/services/infrastructure/agents/tools/__init__.py

# ❌ 删除
from .schema_tools import SchemaListTablesTool, SchemaListColumnsTool

def build_default_tool_factories():
    return [
        lambda c: SchemaListTablesTool(c),      # ❌ 删除
        lambda c: SchemaListColumnsTool(c),     # ❌ 删除
        # ...
    ]
```

#### 新增的工具
```python
# backend/app/services/infrastructure/agents/tools/validation_tools.py

# ✅ 新增
class SQLColumnValidatorTool(BaseTool):
    """验证 SQL 中的列名是否存在"""
    name = "sql.validate_columns"
    description = "验证 SQL 中引用的列是否都存在于表结构中"
    # ...

class SQLColumnAutoFixTool(BaseTool):
    """自动修复 SQL 中的列名错误"""
    name = "sql.auto_fix_columns"
    description = "根据表结构自动修复 SQL 中的列名错误"
    # ...

# backend/app/services/infrastructure/agents/tools/__init__.py
def build_default_tool_factories():
    return [
        # ❌ 删除 schema 工具
        # ✅ 新增验证工具
        lambda c: SQLColumnValidatorTool(c),
        lambda c: SQLColumnAutoFixTool(c),
        # ✅ 保留其他工具
        lambda c: SQLValidatorTool(c),
        lambda c: SQLExecutorTool(c),
        lambda c: SQLRefinerTool(c),
        # ...
    ]
```

---

### 3️⃣ **替换：System Prompt**

#### 修改文件
`backend/app/services/infrastructure/agents/prompts.py`

#### 移除的内容
```python
# ❌ 删除这些指令
"""
- 如果 schema 不完整，调用 `schema.*` 系列工具补足；
- **列名验证流程**：
  1. 必须先调用 `schema.list_columns` 获取表的所有列名
  2. 仔细核对所需的列是否存在于返回的列表中
  ...
"""
```

#### 替换为
```python
# ✅ 新的指令
STAGE_INSTRUCTIONS = {
    "template": """
当前处于【模板规划】阶段，需要生成 SQL 查询。

## 📊 可用信息（已自动注入）
在 system message 的开头，你会看到与当前任务相关的数据表结构信息，包括：
- 表名和说明
- 所有列的名称、类型、注释
- 列的约束（是否可为空等）

⚠️ **重要约束**：
- ✅ 只能使用已列出的表和列（不要臆造！）
- ✅ 仔细阅读列名，使用准确的名称
- ✅ 时间占位符使用 {{start_date}} 和 {{end_date}}（不加引号）

## 🔧 可选验证步骤
生成 SQL 后，你可以：
1. 调用 `sql.validate_columns` 验证列名是否正确
2. 如果验证失败，调用 `sql.auto_fix_columns` 自动修复
3. 调用 `sql.execute` 测试执行

## 📝 输出格式
```json
{
  "sql": "SELECT column1, column2 FROM table1 WHERE dt BETWEEN {{start_date}} AND {{end_date}}",
  "reasoning": "使用 table1 的 column1 和 column2...",
  "tables_used": ["table1"],
  "has_time_filter": true
}
```
""",

    "task_execution": """
当前处于【任务执行】阶段，需要验证/修复已有的 SQL。

## 📊 可用信息（已自动注入）
相关表结构信息已在 system message 中提供。

## 🔧 验证流程
1. 调用 `sql.validate_columns` 验证 SQL 中的列名
2. 如果发现错误，调用 `sql.auto_fix_columns` 自动修复
3. 调用 `sql.validate` 验证语法
4. 调用 `sql.execute` 测试执行
5. 根据结果调用 `sql.refine` 优化

## ⚠️ 约束
- 只能使用已列出的表和列
- 时间占位符格式：{{start_date}}, {{end_date}}（不加引号）
"""
}
```

---

### 4️⃣ **替换：Task 执行流程**

#### 修改文件
`backend/app/services/infrastructure/task_queue/tasks.py`

#### 旧流程（隐式）
```python
# ❌ 旧流程：每个占位符分析时，Agent 自己调用工具获取 schema
for ph in placeholders_need_analysis:
    # Agent.run() 内部会多次调用 schema.list_tables/columns
    result = await system._generate_sql_with_agent(ph)
```

#### 新流程（显式）
```python
# ✅ 新流程：在 Task 开始时统一初始化
@celery_app.task(bind=True, base=DatabaseTask)
def execute_report_task(self, db: Session, task_id: int, ...):
    try:
        # ... 前面的代码 ...

        # 🆕 Step 1: 创建并初始化 Schema Context（一次性）
        schema_context = None
        try:
            from app.services.infrastructure.agents.context_retriever import (
                create_schema_context_retriever
            )

            logger.info(f"📋 初始化 Schema Context for data_source={task.data_source_id}")
            schema_context = create_schema_context_retriever(
                data_source_id=str(task.data_source_id),
                container=container,
                top_k=10,
                inject_as="system"
            )

            # 预加载所有表结构（缓存）
            run_async(schema_context.retriever.initialize())
            logger.info(f"✅ Schema Context 初始化完成，缓存了 {len(schema_context.retriever.schema_cache)} 个表")

        except Exception as e:
            logger.error(f"❌ Schema Context 初始化失败: {e}")
            raise  # 如果 schema 获取失败，任务应该失败

        # 🆕 Step 2: 创建 Task Memory（可选，用于跨占位符共享信息）
        # task_memory = create_task_memory(task_id, time_window)

        # 🆕 Step 3: 初始化 PlaceholderApplicationService，传入 context
        system = PlaceholderProcessingSystem(
            user_id=str(task.owner_id),
            context_retriever=schema_context  # 🔥 传入 context
        )

        # ... 后续的占位符分析流程保持不变 ...
        # Agent 会自动获得 schema context，无需额外操作
```

---

### 5️⃣ **替换：PlaceholderApplicationService**

#### 修改文件
`backend/app/services/application/placeholder/placeholder_service.py`

#### 修改初始化
```python
class PlaceholderApplicationService:
    def __init__(
        self,
        user_id: str = None,
        context_retriever: Optional[Any] = None  # 🆕 新增参数
    ):
        self.container = Container()
        self.context_retriever = context_retriever  # 🆕 保存

        # 🆕 创建 AgentService 时传入 context_retriever
        self.agent_service = AgentService(
            container=self.container,
            context_retriever=self.context_retriever  # 🔥 传递
        )

        # ... 其他初始化 ...
```

#### 简化 analyze_placeholder
```python
async def analyze_placeholder(self, request: PlaceholderAnalysisRequest):
    """分析占位符 - 简化后的流程"""

    # ❌ 删除：不再需要在 prompt 中指导 Agent 调用工具
    # ❌ 删除：不再需要检查 Agent 是否调用了正确的工具

    # ✅ 简化：直接构建业务需求，Agent 会自动看到 schema
    task_prompt = f"""
生成 SQL 查询来满足以下需求：

### 业务需求
{request.business_command}

### 目标
{request.target_objective}

### 时间范围
{time_window}

请根据提供的表结构信息生成 SQL，确保只使用已列出的表和列。
"""

    # ✅ 执行（schema 会自动注入）
    result = await self.agent_service.execute(agent_input)

    # ✅ 返回结果
    return result
```

---

### 6️⃣ **替换：单一占位符分析 API**

#### 修改文件
`backend/app/api/v1/endpoints/template_placeholder.py`

#### 当前流程
```python
@router.post("/{placeholder_id}/analyze")
async def analyze_placeholder(...):
    # ❌ 当前：每次都需要 Agent 调用工具获取 schema
    service = PlaceholderApplicationService(user_id=current_user.id)
    async for event in service.analyze_placeholder(request):
        yield event
```

#### 新流程
```python
@router.post("/{placeholder_id}/analyze")
async def analyze_placeholder(
    placeholder_id: str,
    request: PlaceholderAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # 🆕 Step 1: 获取数据源信息
        placeholder = crud_placeholder.get(db, id=placeholder_id)
        template = crud_template.get(db, id=placeholder.template_id)
        data_source_id = request.data_source_id or template.data_source_id

        # 🆕 Step 2: 创建 Schema Context
        from app.services.infrastructure.agents.context_retriever import (
            create_schema_context_retriever
        )
        from app.core.container import Container

        container = Container()
        schema_context = create_schema_context_retriever(
            data_source_id=str(data_source_id),
            container=container,
            top_k=5,  # 单一占位符分析，top_k 可以小一点
            inject_as="system"
        )

        # 初始化（异步）
        await schema_context.retriever.initialize()

        # 🆕 Step 3: 创建 Service 并传入 context
        service = PlaceholderApplicationService(
            user_id=str(current_user.id),
            context_retriever=schema_context  # 🔥 传入
        )

        # Step 4: 执行分析（流程保持不变）
        async for event in service.analyze_placeholder(request):
            yield event

    except Exception as e:
        logger.error(f"占位符分析失败: {e}")
        yield {
            "type": "error",
            "error": str(e)
        }
```

---

## 📦 文件清单

### 需要修改的文件

1. ✅ **已完成**
   - `backend/app/services/infrastructure/agents/context_retriever.py` - 已创建
   - `backend/app/services/infrastructure/agents/runtime.py` - 已修改
   - `backend/app/services/infrastructure/agents/facade.py` - 已修改
   - `backend/app/services/infrastructure/agents/service.py` - 已修改

2. 🔲 **待实现**
   - `backend/app/services/infrastructure/agents/tools/validation_tools.py` - 新建（验证工具）
   - `backend/app/services/infrastructure/agents/tools/__init__.py` - 修改（替换工具列表）
   - `backend/app/services/infrastructure/agents/prompts.py` - 修改（替换 prompt）

3. 🔲 **待修改**
   - `backend/app/services/infrastructure/task_queue/tasks.py` - 修改（Task 流程）
   - `backend/app/services/application/placeholder/placeholder_service.py` - 修改（Service 初始化）
   - `backend/app/api/v1/endpoints/template_placeholder.py` - 修改（API 端点）

### 需要删除的文件/代码

1. `backend/app/services/infrastructure/agents/tools/schema_tools.py`
   - ❌ 删除：`SchemaListTablesTool`
   - ❌ 删除：`SchemaListColumnsTool`
   - 或者保留但标记为 deprecated（渐进式迁移）

---

## 🚀 实施顺序

### Phase 1: 实现新工具（当前）

```bash
# Step 1: 创建验证工具
touch backend/app/services/infrastructure/agents/tools/validation_tools.py

# Step 2: 实现 SQLColumnValidatorTool
# Step 3: 实现 SQLColumnAutoFixTool
# Step 4: 修改 tools/__init__.py，替换工具列表
```

### Phase 2: 替换 Prompt

```bash
# Step 1: 修改 prompts.py
# Step 2: 删除旧的 schema 工具调用指令
# Step 3: 添加新的 "信息已注入" 指令
```

### Phase 3: 替换业务流程

```bash
# Step 1: 修改 tasks.py（Task 批量分析）
# Step 2: 修改 placeholder_service.py（Service 层）
# Step 3: 修改 template_placeholder.py（API 层）
```

### Phase 4: 清理旧代码

```bash
# Step 1: 删除或标记 schema_tools.py 为 deprecated
# Step 2: 删除旧的 prompt 文本
# Step 3: 更新文档
```

---

## ✅ 验证清单

完成替换后，需要验证：

- [ ] Schema Context 成功初始化并缓存表结构
- [ ] Agent 不再调用 `schema.list_tables` 或 `schema.list_columns`
- [ ] Agent 生成的 SQL 使用正确的表名和列名
- [ ] 新的验证工具能够正确识别列名错误
- [ ] 自动修复工具能够修复常见的列名错误
- [ ] Task 批量分析性能提升（减少 LLM 调用次数）
- [ ] 单一占位符分析功能正常
- [ ] 所有测试用例通过

---

## 📊 预期效果

### 性能提升
- ⬇️ LLM 调用次数减少 70%
- ⬇️ 总执行时间减少 65%
- ⬆️ SQL 准确率提升到 95%+

### 代码简化
- ❌ 删除 2 个工具类（~200 行代码）
- ❌ 删除复杂的 prompt 指令（~50 行）
- ✅ 新增 2 个验证工具（~150 行代码）
- ✅ 流程更清晰，更易维护

### 用户体验
- ✅ 更快的响应速度
- ✅ 更高的准确率
- ✅ 更少的错误重试

---

## 🎯 关键原则

1. **彻底替换，不是共存**
   - 不保留旧的 schema 工具调用方式
   - 统一使用 ContextRetriever

2. **初始化前置**
   - 在 Task/API 入口处初始化 Schema Context
   - 所有后续流程自动获得 schema 信息

3. **提示简化**
   - Prompt 不再指导 Agent "如何获取 schema"
   - 直接告知 Agent "信息已提供，请使用"

4. **工具专注**
   - Tools 专注于"验证"和"修复"
   - 不再用于"获取静态信息"

---

**这是一个彻底的架构替换方案，不是可选的优化。完成后，整个系统将以全新的方式运行：基于自动上下文注入，而非被动工具调用。**
