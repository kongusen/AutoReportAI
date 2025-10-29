# 混合SQL执行策略架构设计

**日期**: 2025-10-26
**版本**: 1.0
**状态**: 设计中

---

## 🎯 设计目标

实现一个智能的 SQL 执行策略，在保证性能和稳定性的同时，提供自动错误修正能力：

1. **首次生成**：使用静态验证（快速、不连接数据库）
2. **首次执行**：在 ETL 阶段执行 SQL
3. **失败重试**：如果执行失败，允许 Agent 执行 1 次 SQL 进行验证和修正
4. **限制次数**：最多重试 1 次，避免无限循环

---

## 🏗️ 架构设计

### 整体流程

```
┌─────────────────────────────────────────────────────────────┐
│                    SQL Generation Stage                     │
│                   (静态验证，不连接数据库)                   │
├─────────────────────────────────────────────────────────────┤
│  1. Schema 探索（CachedSchemaListTablesTool）               │
│  2. SQL 生成                                                │
│  3. 静态验证（SQLValidateTool, SQLColumnValidatorTool）    │
│  4. 返回 SQL                                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     ETL Execution Stage                     │
│                    (执行 SQL，获取数据)                      │
├─────────────────────────────────────────────────────────────┤
│  1. 使用 SQLExecuteTool 执行 SQL                            │
│  2. 检查执行结果                                            │
│     ├─ 成功 → 返回数据 ✅                                   │
│     └─ 失败 → 提取错误信息 ❌                               │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼ (if failed)
┌─────────────────────────────────────────────────────────────┐
│                  SQL Retry Generation Stage                 │
│            (带错误上下文，允许执行 SQL 验证)                │
├─────────────────────────────────────────────────────────────┤
│  1. 提供错误信息和原始 SQL                                  │
│  2. Agent 分析错误原因                                      │
│  3. 生成修正后的 SQL                                        │
│  4. 🔥 允许执行 1 次 SQL 验证（SQLExecuteTool）            │
│  5. 返回修正后的 SQL                                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   ETL Re-Execution Stage                    │
│                 (执行修正后的 SQL)                          │
├─────────────────────────────────────────────────────────────┤
│  1. 使用 SQLExecuteTool 执行修正后的 SQL                    │
│  2. 返回结果（成功或失败，不再重试）                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 📐 核心组件设计

### 1. 执行模式（Execution Mode）

```python
from enum import Enum

class SQLExecutionMode(str, Enum):
    """SQL 执行模式"""
    STATIC_ONLY = "static_only"      # 仅静态验证（默认）
    ALLOW_EXECUTION = "allow_execution"  # 允许执行 SQL 验证
```

### 2. 重试上下文（Retry Context）

```python
@dataclass
class SQLRetryContext:
    """SQL 重试上下文"""
    original_sql: str                    # 原始 SQL
    error_message: str                   # 执行错误信息
    error_type: str                      # 错误类型（语法/列不存在/超时等）
    execution_time: Optional[float]      # 执行耗时
    placeholder_id: str                  # 占位符 ID
    placeholder_name: str                # 占位符名称
    retry_count: int = 0                 # 当前重试次数
    max_retries: int = 1                 # 最大重试次数
```

### 3. ETL 阶段增强

```python
async def _stage_etl_execution(
    self,
    context: OrchestratorContext,
    result: StageResult,
) -> AsyncIterator[Dict[str, Any]]:
    """
    ETL 执行阶段（增强版）

    支持自动重试：
    1. 执行所有 SQL
    2. 收集失败的 SQL
    3. 如果有失败，触发重试机制
    """

    # 第一次执行
    exec_results = await self._execute_sql_batch(context, ...)

    # 提取失败的 SQL
    failed_sqls = [r for r in exec_results if not r["success"]]

    if failed_sqls:
        yield {
            "type": "stage_warning",
            "message": f"发现 {len(failed_sqls)} 个 SQL 执行失败，启动自动修正..."
        }

        # 触发重试
        retry_results = await self._retry_failed_sqls(
            context=context,
            failed_sqls=failed_sqls,
        )

        # 合并结果
        exec_results = self._merge_results(exec_results, retry_results)

    # 返回最终结果
    context.shared_data["etl_results"] = exec_results
    result.output = {"results": exec_results}
```

### 4. SQL 重试机制

```python
async def _retry_failed_sqls(
    self,
    context: OrchestratorContext,
    failed_sqls: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    重试失败的 SQL

    Args:
        context: 执行上下文
        failed_sqls: 失败的 SQL 列表

    Returns:
        重试后的结果列表
    """
    retry_results = []

    for failed_sql in failed_sqls:
        # 构建重试上下文
        retry_context = SQLRetryContext(
            original_sql=failed_sql["sql"],
            error_message=failed_sql["error"],
            error_type=self._classify_error(failed_sql["error"]),
            placeholder_id=failed_sql["placeholder_id"],
            placeholder_name=failed_sql["placeholder_name"],
            retry_count=0,
            max_retries=1,
        )

        # 调用 Agent 重新生成 SQL（允许执行验证）
        retry_result = await self._regenerate_sql_with_error_context(
            context=context,
            retry_context=retry_context,
            execution_mode=SQLExecutionMode.ALLOW_EXECUTION,  # 🔥 关键：允许执行
        )

        if retry_result["success"]:
            # 执行修正后的 SQL
            exec_result = await self._execute_single_sql(
                context=context,
                sql=retry_result["sql"],
                placeholder_id=retry_context.placeholder_id,
                placeholder_name=retry_context.placeholder_name,
            )
            retry_results.append(exec_result)
        else:
            # 重试仍失败，返回原始错误
            retry_results.append(failed_sql)

    return retry_results
```

### 5. 带错误上下文的 SQL 重新生成

```python
async def _regenerate_sql_with_error_context(
    self,
    context: OrchestratorContext,
    retry_context: SQLRetryContext,
    execution_mode: SQLExecutionMode,
) -> Dict[str, Any]:
    """
    基于错误上下文重新生成 SQL

    Args:
        context: 执行上下文
        retry_context: 重试上下文（包含错误信息）
        execution_mode: 执行模式（是否允许执行 SQL）

    Returns:
        新的 SQL 和验证结果
    """
    from app.services.application.placeholder.placeholder_service import PlaceholderApplicationService
    from app.services.domain.placeholder.types import PlaceholderAnalysisRequest

    ph_service = PlaceholderApplicationService(user_id=context.user_id)

    # 获取原始占位符信息
    original_placeholder = next(
        (p for p in context.shared_data.get("placeholders", [])
         if p.get("id") == retry_context.placeholder_id),
        None
    )

    if not original_placeholder:
        return {"success": False, "error": "Placeholder not found"}

    # 🔥 构建带错误信息的请求
    request = PlaceholderAnalysisRequest(
        placeholder_id=retry_context.placeholder_id,
        business_command=original_placeholder.get("description", ""),
        requirements=original_placeholder.get("requirements", ""),
        target_objective=original_placeholder.get("objective", "数据查询"),
        context={
            "placeholder_context_snippet": original_placeholder.get("context_text", ""),
            "time_window": context.time_window,
            "schedule": context.schedule,
            # 🔥 关键：提供错误上下文
            "previous_attempt": {
                "sql": retry_context.original_sql,
                "error": retry_context.error_message,
                "error_type": retry_context.error_type,
            },
            # 🔥 关键：设置执行模式
            "execution_mode": execution_mode.value,
        },
        data_source_info={
            "id": str(context.data_source.id),
            "source_type": context.data_source.source_type.value,
            "database_name": getattr(context.data_source, 'doris_database', 'default_db'),
        },
    )

    # 执行重新生成
    sql_result = None
    async for event in ph_service.analyze_placeholder(request):
        if event.get("type") == "sql_generation_complete":
            sql_result = event.get("content")
            break
        elif event.get("type") in ["sql_generation_failed", "analysis_error"]:
            return {"success": False, "error": event.get("content")}

    if sql_result and sql_result.sql_query:
        return {
            "success": True,
            "sql": sql_result.sql_query,
            "metadata": sql_result.metadata,
        }

    return {"success": False, "error": "SQL regeneration failed"}
```

### 6. 错误分类（Error Classification）

```python
def _classify_error(self, error_message: str) -> str:
    """
    分类 SQL 执行错误

    Args:
        error_message: 错误信息

    Returns:
        错误类型
    """
    error_msg_lower = error_message.lower()

    # 语法错误
    if any(kw in error_msg_lower for kw in ["syntax", "parser", "unexpected"]):
        return "syntax_error"

    # 列不存在
    if any(kw in error_msg_lower for kw in ["column", "field", "unknown column"]):
        return "column_not_found"

    # 表不存在
    if any(kw in error_msg_lower for kw in ["table", "relation", "unknown table"]):
        return "table_not_found"

    # 连接错误
    if any(kw in error_msg_lower for kw in ["connection", "timeout", "refused"]):
        return "connection_error"

    # 权限错误
    if any(kw in error_msg_lower for kw in ["permission", "access denied", "forbidden"]):
        return "permission_error"

    # 其他错误
    return "unknown_error"
```

---

## 🔧 PlaceholderApplicationService 修改

需要支持：
1. 接收错误上下文
2. 根据 `execution_mode` 决定是否允许执行 SQL

```python
# placeholder_service.py

async def analyze_placeholder(
    self,
    request: PlaceholderAnalysisRequest,
) -> AsyncIterator[Dict[str, Any]]:
    """
    分析占位符并生成 SQL

    支持重试模式：如果 request.context 包含 previous_attempt，
    会将错误信息传递给 Agent，并根据 execution_mode 决定是否允许执行 SQL
    """

    # 检查是否是重试请求
    previous_attempt = request.context.get("previous_attempt")
    execution_mode = request.context.get("execution_mode", "static_only")

    # 构建 Agent 输入
    agent_input = {
        "placeholder": {...},
        "data_source": {...},
        "context": {...},
    }

    # 如果是重试，添加错误信息
    if previous_attempt:
        agent_input["retry_context"] = {
            "previous_sql": previous_attempt["sql"],
            "error_message": previous_attempt["error"],
            "error_type": previous_attempt["error_type"],
            "guidance": self._generate_error_guidance(previous_attempt),
        }

    # 🔥 根据执行模式配置工具
    if execution_mode == "allow_execution":
        # 允许执行 SQL 验证（但限制次数）
        tools = self._get_tools_with_execution(max_executions=1)
    else:
        # 仅静态验证
        tools = self._get_static_validation_tools()

    # 调用 Agent
    result = await self.agent_service.execute_agent(
        agent_name="sql_generator",
        input_data=agent_input,
        tools=tools,
    )

    ...
```

---

## 📊 提示词优化

### 重试模式的 Prompt 增强

```python
def _build_retry_prompt(self, retry_context: Dict[str, Any]) -> str:
    """构建重试模式的 Prompt"""
    return f"""
## 🔧 SQL 执行失败 - 需要修正

### 原始 SQL
```sql
{retry_context['previous_sql']}
```

### 执行错误
- **错误类型**: {retry_context['error_type']}
- **错误信息**: {retry_context['error_message']}

### 错误分析指导
{retry_context['guidance']}

### 你的任务
1. 分析错误原因
2. 修正 SQL
3. **你可以执行 1 次 SQL 来验证修正是否成功**（使用 sql_execute 工具）
4. 返回修正后的 SQL

### 注意
- 你有 **1 次** 执行 SQL 的机会来验证修正
- 确保修正后的 SQL 能够成功执行
- 如果不确定，先使用 sql_validate 工具进行静态验证
"""

def _generate_error_guidance(self, previous_attempt: Dict[str, Any]) -> str:
    """根据错误类型生成指导建议"""
    error_type = previous_attempt["error_type"]

    guidance_map = {
        "syntax_error": """
- 检查 SQL 语法是否正确
- 确认 SELECT/FROM/WHERE 等关键字的使用
- 检查括号、引号是否匹配
- 验证函数调用是否正确
        """,
        "column_not_found": """
- 使用 cached_schema_list_columns 工具确认列名是否正确
- 检查列名大小写是否匹配
- 确认表别名是否正确
- 检查是否使用了不存在的派生列
        """,
        "table_not_found": """
- 使用 cached_schema_list_tables 工具确认表名是否正确
- 检查表名大小写是否匹配
- 确认数据库名是否正确
        """,
        "connection_error": """
- 这是数据库连接问题，不是 SQL 问题
- SQL 可能是正确的，但无法执行
- 返回当前 SQL，并标注为"连接错误"
        """,
    }

    return guidance_map.get(error_type, "检查 SQL 语法和逻辑，确保所有引用的表和列都存在")
```

---

## 🎯 实现优先级

### Phase 1: 核心重试机制（本次实现）
1. ✅ 定义 `SQLExecutionMode` 和 `SQLRetryContext`
2. ✅ 实现 `_classify_error` 错误分类
3. ✅ 实现 `_retry_failed_sqls` 重试逻辑
4. ✅ 修改 `_stage_etl_execution` 支持重试
5. ✅ 实现 `_regenerate_sql_with_error_context`

### Phase 2: Prompt 和工具优化（后续）
1. ⏳ 优化重试模式的 Prompt
2. ⏳ 实现 `_generate_error_guidance`
3. ⏳ 添加执行次数限制
4. ⏳ 添加详细日志和监控

### Phase 3: 高级特性（可选）
1. ⏳ 支持多轮重试（最多 2 次）
2. ⏳ 添加 SQL 执行采样（LIMIT 10）
3. ⏳ 添加执行时间监控和超时控制

---

## 📈 预期效果

### 成功率提升
- **当前方案**: 静态验证，SQL 错误无法自动修正
- **混合方案**: 自动检测并修正 ~80% 的常见 SQL 错误

### 性能影响
- **90% 场景**: 无影响（静态验证，不连接数据库）
- **10% 场景**: 额外 1 次数据库连接（重试时）
- **整体影响**: 极小（大部分 SQL 首次即可成功）

### 稳定性
- **数据库连接稳定**: 快速生成，偶尔重试
- **数据库连接不稳定**: 静态验证为主，最小化连接次数

---

## 🔍 监控指标

建议跟踪以下指标：

1. **首次成功率**: 不需要重试的 SQL 占比
2. **重试成功率**: 重试后成功的 SQL 占比
3. **常见错误类型分布**: 用于优化 Prompt
4. **执行时间分布**: 监控性能影响
5. **数据库连接次数**: 确保不会频繁连接

---

## 🎉 总结

混合执行策略的核心优势：

1. **平衡性**: 兼顾性能、稳定性、准确性
2. **智能性**: 自动检测错误并修正
3. **可控性**: 限制重试次数，避免无限循环
4. **可观测性**: 详细的日志和监控指标

这是一个**渐进增强**的方案：
- 默认情况下不影响性能
- 遇到错误时自动启用修正
- 最小化数据库连接次数
- 提供明确的错误反馈

