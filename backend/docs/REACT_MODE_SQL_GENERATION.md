# ReAct模式SQL生成

## 什么是ReAct模式？

**ReAct** = **Reasoning** (推理) + **Acting** (行动)

这是一种让AI Agent自主使用工具完成任务的模式，而不是由我们手动编排步骤。

### Before（手动编排）

```python
# 我们告诉Agent每一步做什么
Step 1: 调用 schema.list_tables
Step 2: 调用 schema.list_columns
Step 3: 生成SQL
Step 4: 调用 sql.validate
Step 5: 如果失败，调用 sql.refine
```

### After（ReAct自主）

```python
# 我们只告诉Agent任务目标和可用工具
# Agent自己决定何时使用什么工具

Agent: "我需要生成SQL，首先让我看看有哪些表..."
Agent: [使用工具] schema.list_tables
Agent: "好的，我找到了ods_refund表，让我看看它的列..."
Agent: [使用工具] schema.list_columns(tables=["ods_refund"])
Agent: "我看到有dt列可以作为时间过滤，现在生成SQL..."
Agent: [生成] SELECT ... WHERE dt = '{{start_date}}'
Agent: "让我验证一下这个SQL..."
Agent: [使用工具] sql.validate(sql=...)
Agent: "验证通过！任务完成。"
```

## 实现变化

### 修改的文件

**`backend/app/services/application/placeholder/placeholder_service.py`**

#### Before（手动步骤）
```python
async def analyze_placeholder(self, request):
    # Step 1: 手动调用
    schema_info = await self._discover_schema(...)

    # Step 2: 手动调用
    sql = await self._generate_sql_with_schema(...)

    # Step 3: 手动调用
    validation = await self._validate_sql(...)

    # Step 4: 手动调用
    if not validation["is_valid"]:
        sql = await self._refine_sql(...)
```

#### After（ReAct模式）
```python
async def analyze_placeholder(self, request):
    # 构建任务描述
    task_prompt = """
    你是SQL生成专家。使用可用工具完成任务：

    ## 任务
    生成SQL查询满足: {业务需求}

    ## 可用工具
    - schema.list_tables
    - schema.list_columns
    - sql.validate
    - sql.execute
    - sql.refine

    ## 约束
    - 必须包含时间过滤
    - 只能使用实际存在的列

    现在开始ReAct！
    """

    # Agent自主执行
    result = await self.agent_service.execute(agent_input)

    # Agent会自己决定使用哪些工具
```

## 可用工具

Agent可以自主使用以下工具：

### 1. schema.list_tables
**功能**: 列出数据源中的所有表

**输入**:
```json
{
  "data_source": {
    "data_source_id": "...",
    "database_name": "yjg"
  }
}
```

**输出**:
```json
{
  "success": true,
  "tables": ["ods_refund", "ods_order", ...],
  "message": "发现 10 个表"
}
```

### 2. schema.list_columns
**功能**: 获取指定表的列信息

**输入**:
```json
{
  "data_source": {...},
  "tables": ["ods_refund", "ods_order"]
}
```

**输出**:
```json
{
  "success": true,
  "columns": {
    "ods_refund": ["refund_id", "dt", "amount", ...],
    "ods_order": ["order_id", "date", ...]
  },
  "schema_summary": "**ods_refund**: refund_id(VARCHAR), dt(DATE), ..."
}
```

### 3. sql.validate
**功能**: 验证SQL的正确性

**输入**:
```json
{
  "sql": "SELECT ...",
  "schema": {...},
  "require_time_filter": true
}
```

**输出**:
```json
{
  "success": true,
  "is_valid": false,
  "errors": ["缺少时间过滤条件"],
  "suggestions": ["使用: WHERE dt = '{{start_date}}'"]
}
```

### 4. sql.execute
**功能**: 执行SQL测试（LIMIT 5）

**输入**:
```json
{
  "sql": "SELECT ...",
  "data_source": {...}
}
```

**输出**:
```json
{
  "success": true,
  "rows": [...],
  "columns": ["col1", "col2"],
  "row_count": 5
}
```

### 5. sql.refine
**功能**: 基于错误优化SQL

**输入**:
```json
{
  "original_sql": "SELECT ...",
  "errors": ["缺少时间过滤"],
  "schema": {...}
}
```

**输出**:
```json
{
  "success": true,
  "refined_sql": "SELECT ... WHERE dt = '{{start_date}}'",
  "reasoning": "添加了时间过滤条件"
}
```

## Agent工作流示例

### 典型的ReAct流程

```
User: 统计退货金额
↓
Agent思考: 我需要找到存储退货数据的表
↓
Agent行动: 调用 schema.list_tables
↓
Agent观察: 找到 ods_refund 表
↓
Agent思考: 我需要知道这个表有哪些列
↓
Agent行动: 调用 schema.list_columns(tables=["ods_refund"])
↓
Agent观察: 列有 [refund_id, dt, amount, flow_status, ...]
↓
Agent思考: 我可以用amount列，dt列做时间过滤
↓
Agent行动: 生成SQL
  SELECT SUM(amount) AS total_refund_amount
  FROM ods_refund
  WHERE dt = '{{start_date}}'
  AND flow_status = '退货成功'
↓
Agent思考: 让我验证这个SQL
↓
Agent行动: 调用 sql.validate(sql=...)
↓
Agent观察: 验证通过，包含时间过滤
↓
Agent思考: 可以测试一下
↓
Agent行动: 调用 sql.execute(sql=..., limit=5)
↓
Agent观察: 执行成功，返回5行数据
↓
Agent完成: 返回最终SQL
```

## 优势

### 1. 自主决策
- ✅ Agent自己决定何时使用哪个工具
- ✅ 根据观察结果调整策略
- ✅ 可以跳过不必要的步骤

### 2. 自我修复
```python
# Agent发现错误会自动修复
Agent: 调用 sql.validate
Result: 缺少时间过滤
Agent: 自动调用 sql.refine 添加时间过滤
Agent: 重新验证 → 通过
```

### 3. 灵活性
```python
# 简单查询：少用工具
Agent: list_tables → list_columns → 生成SQL → 完成

# 复杂查询：多次迭代
Agent: list_tables → list_columns → 生成SQL → validate →
       refine → validate → execute → refine → validate → 完成
```

### 4. 可观测性
```python
# Agent的每一步都有日志
[Agent] 🤔 思考: 需要探索schema
[Agent] 🔧 使用工具: schema.list_tables
[Agent] 👀 观察: 找到10个表
[Agent] 🤔 思考: 选择ods_refund表
[Agent] 🔧 使用工具: schema.list_columns
...
```

## 与Loom框架的集成

### Loom Agent配置

系统使用Loom框架的Agent，已经配置好工具：

```python
# backend/app/services/infrastructure/agents/runtime.py

class LoomAgentRuntime:
    def __init__(self, agent, tools, config):
        self._agent = agent  # Loom Agent实例
        self._tools = tools  # 注册的工具

    async def run(self, prompt, **kwargs):
        # Agent自主使用工具
        return await self._agent.run(prompt)
```

### 工具注册

```python
# backend/app/services/infrastructure/agents/tools/__init__.py

DEFAULT_TOOL_SPECS = (
    ("...schema_tools", "SchemaListTablesTool"),
    ("...schema_tools", "SchemaListColumnsTool"),
    ("...sql_tools", "SQLValidateTool"),
    ("...sql_tools", "SQLExecuteTool"),
    ("...sql_tools", "SQLRefineTool"),
    # ...
)

# 这些工具已经注册，Agent可以直接使用
```

## 配置选项

### 默认配置（推荐）

```python
# ReAct模式已经默认启用
service = PlaceholderApplicationService(user_id="user-123")
result = await service.analyze_placeholder(request)
# Agent会自主使用工具
```

### 调整Agent迭代次数

如果Agent需要更多尝试：

```python
# backend/app/services/infrastructure/agents/config.py

config = LoomAgentConfig(
    runtime=RuntimeConfig(
        max_iterations=20  # 允许Agent最多迭代20次
    )
)
```

### 启用详细日志

```python
import logging
logging.getLogger("app.services.infrastructure.agents").setLevel(logging.DEBUG)

# 可以看到Agent的每一步
# [DEBUG] Agent使用工具: schema.list_tables
# [DEBUG] 工具返回: {...}
# [DEBUG] Agent思考: ...
```

## 监控和调试

### Agent工具调用记录

```python
# 在返回的metadata中
{
    "generation_method": "react_autonomous",
    "agent_metadata": {
        "tools_used": [
            "schema.list_tables",
            "schema.list_columns",
            "sql.validate"
        ],
        "iterations": 5,
        "total_time": 3.2
    }
}
```

### 查看Agent推理过程

```python
# 查看日志
[INFO] 🤖 启动ReAct模式 - Agent将自主使用工具生成SQL
[DEBUG] Agent iteration 1: 使用 schema.list_tables
[DEBUG] Agent iteration 2: 使用 schema.list_columns
[DEBUG] Agent iteration 3: 生成SQL并验证
[DEBUG] Agent iteration 4: 优化SQL
[DEBUG] Agent iteration 5: 最终验证通过
[INFO] ✅ Agent生成SQL完成
```

## 与之前的对比

### 代码量

| 模式 | 代码行数 | 复杂度 |
|------|---------|--------|
| 手动编排 | ~400行 | 高（需要管理每个步骤） |
| ReAct模式 | ~150行 | 低（Agent自己决定） |

### 灵活性

| 场景 | 手动编排 | ReAct模式 |
|------|---------|-----------|
| 简单查询 | 执行所有步骤 | Agent可以跳过不必要步骤 ✅ |
| 复杂查询 | 固定迭代次数 | Agent可以多次尝试直到成功 ✅ |
| 错误修复 | 需要预先编写逻辑 | Agent自动使用sql.refine ✅ |
| 新工具 | 需要修改代码 | Agent自动发现并使用 ✅ |

### 可维护性

**手动编排**:
```python
# 增加新步骤需要修改代码
# 步骤顺序改变需要重构
# 错误处理逻辑复杂
```

**ReAct模式**:
```python
# 增加新工具只需注册
# Agent自己决定使用顺序
# 错误处理由Agent自动完成
```

## 总结

通过启用ReAct模式，系统现在让Agent：

1. ✅ **自主探索** - Agent自己调用schema工具探索数据库
2. ✅ **智能生成** - 基于探索结果生成SQL
3. ✅ **自我验证** - 自动调用validate检查SQL
4. ✅ **自动修复** - 发现错误自动调用refine优化
5. ✅ **迭代优化** - 多次尝试直到生成高质量SQL

这是真正的**智能Agent**，而不是机械地执行预定义步骤！🚀

## 下一步

1. **监控效果** - 观察Agent的工具使用模式
2. **优化提示** - 根据Agent表现调整task_prompt
3. **增加工具** - 添加更多工具供Agent使用
4. **改进反馈** - 让Agent根据执行结果自我学习
