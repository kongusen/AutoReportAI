# Backend-Old Agent 完整处理流程分析

> 基于 `/Users/shan/work/uploads/AutoReportAI/backend` 的稳定SQL生成机制分析

## 一、核心架构：PTAV循环

### 1.1 PTAV单步骤循环模式

**Plan-Tool-Active-Validate** 是backend-old的核心执行模式：

```
┌─────────────────────────────────────────────────┐
│  Plan (计划)                                     │
│  ├─ Agent分析当前状态                             │
│  ├─ 检测是否处于SQL修复循环                       │
│  └─ 决策下一步单个动作                            │
└──────────────┬──────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────┐
│  Tool (工具执行)                                 │
│  ├─ 执行Agent决定的单个工具                       │
│  ├─ schema.list_tables                           │
│  ├─ schema.get_columns                           │
│  ├─ sql_generation (LLM直接生成)                 │
│  ├─ sql.validate                                 │
│  ├─ sql.refine                                   │
│  └─ sql.execute                                  │
└──────────────┬──────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────┐
│  Active (分析结果)                                │
│  ├─ Agent分析工具执行结果                         │
│  ├─ 提取关键信息                                  │
│  └─ 判断执行是否成功                              │
└──────────────┬──────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────┐
│  Validate (验证目标)                              │
│  ├─ 检查是否达成目标                              │
│  ├─ SQL修复循环逻辑 (最多3次)                     │
│  ├─ 智能退出检测                                  │
│  └─ 决定是否继续循环                              │
└──────────────┬──────────────────────────────────┘
               │
               ├─ 继续 → 返回Plan
               └─ 完成 → 返回最终结果
```

### 1.2 关键特性

1. **单步骤执行**：每次只执行一个操作，立即返回给Agent分析
2. **Agent主导**：所有决策由Agent做出，工具只执行
3. **真实验证**：通过实际数据库执行验证SQL正确性
4. **状态维护**：在循环中维护execution_context和资源池

---

## 二、ResourcePool模式（关键创新）

### 2.1 设计理念

**问题**：传统模式下，上下文会不断累积，导致token消耗过大，影响LLM性能

**解决方案**：精简记忆 + 详细资源按需提取

```
传统模式（累积上下文）：
┌─────────────────────────────────────┐
│  Iteration 1                        │
│  ├─ schema (5KB)                    │
│  └─ context (1KB)                   │   6KB
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│  Iteration 2                        │
│  ├─ schema (5KB)                    │
│  ├─ context1 (1KB)                  │
│  └─ context2 (1KB)                  │   7KB
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│  Iteration 3                        │
│  ├─ schema (5KB)                    │
│  ├─ context1 (1KB)                  │
│  ├─ context2 (1KB)                  │
│  └─ context3 (1KB)                  │   8KB  ← 持续增长
└─────────────────────────────────────┘

ResourcePool模式（精简记忆）：
┌───────────────────────────────────────────────┐
│  ResourcePool (持久存储)                       │
│  ├─ column_details (完整)                      │
│  ├─ schema_summary (完整)                      │
│  ├─ template_context (完整)                    │
│  ├─ current_sql                                │
│  └─ validation_history                         │
└───────────────────────────────────────────────┘
         ↑ 存储              ↓ 按需提取
┌─────────────────────────────────────┐
│  ContextMemory (轻量级传递)          │
│  ├─ has_sql: true                   │
│  ├─ schema_available: true          │
│  ├─ available_tables: [list]        │  只需2KB
│  ├─ database_validated: true        │
│  └─ sql_length: 250                 │
└─────────────────────────────────────┘
```

### 2.2 核心组件

#### ContextMemory (精简记忆)
```python
@dataclass
class ContextMemory:
    # 状态标记（布尔值）
    has_sql: bool = False
    schema_available: bool = False
    database_validated: bool = False
    sql_executed_successfully: bool = False

    # 表名列表（不含字段详情）
    available_tables: List[str] = []

    # 简要标识
    sql_length: int = 0
    sql_fix_attempts: int = 0
    last_error_summary: str = ""

    # 时间范围（精简）
    time_range: Optional[Dict[str, str]] = None
    recommended_time_column: Optional[str] = None
```

#### ResourcePool (资源池)
```python
class ResourcePool:
    def update(self, updates: Dict[str, Any]) -> None:
        """增量更新，不删除已有信息"""
        # column_details: 合并而不是覆盖
        # sql_history: 追加而不是覆盖
        # validation_history: 追加而不是覆盖

    def get(self, key: str) -> Any:
        """返回深拷贝，避免外部修改"""

    def get_lightweight_memory(self) -> Dict[str, Any]:
        """提取精简记忆用于步骤间传递"""

    def extract_for_step(self, step_type: str) -> Dict[str, Any]:
        """为特定步骤提取上下文"""
        # plan: 只需要精简记忆
        # sql_generation: 需要column_details + template_context
        # sql_validation: 需要current_sql + column_details
        # sql_refinement: 需要SQL + 错误 + schema
```

### 2.3 使用场景

**在orchestrator.py中的应用**：

```python
# 初始化ResourcePool
resource_pool = ResourcePool() if use_resource_pool else None

# 在PTAV循环中更新ResourcePool
if use_resource_pool and resource_pool:
    updates = {}
    if context.get("column_details"):
        updates["column_details"] = context["column_details"]
    if context.get("recommended_time_column"):
        updates["recommended_time_column"] = context["recommended_time_column"]
    resource_pool.update(updates)

# 传递轻量级ContextMemory到下一轮
context_memory = resource_pool.build_context_memory()
tdc["context_memory"] = context_memory.to_dict()
```

---

## 三、SQL修复循环（智能错误处理）

### 3.1 修复循环触发条件

在`orchestrator.py._validate_goal_achievement()`中：

```python
if not exec_result.get("success") and current_sql:
    issues = context.get("issues", [])
    if issues:
        sql_fix_attempts = execution_context.get("sql_fix_attempts", 0)
        if sql_fix_attempts < 3:  # 最多3次修复尝试
            # 进入修复循环
```

### 3.2 智能错误诊断

**错误分类** (`_summarize_sql_errors`):
- 字段名不存在 (Unknown column)
- 表名不存在 (table not found)
- SQL语法错误 (syntax, parse error)
- 权限错误 (permission denied)

**修复策略标记**:
```python
has_column_details = bool(execution_context.get("column_details"))
execution_context["needs_schema_refresh"] = not has_column_details
execution_context["needs_sql_regeneration"] = has_column_details
```

### 3.3 Agent驱动的修复决策

**在planner.py中构建SQL修复提示词**：

```markdown
## 修复策略提示

1. **字段名/表名不存在**
   - 没有详细字段信息 → 先调用 schema.get_columns
   - 已有详细字段信息 → 使用 sql_generation 重新生成
   - **不要**用 sql.refine 修复字段名错误

2. **SQL语法错误**
   - 使用 sql.refine 修复语法问题

3. **时间字段选择错误**
   - 有详细字段信息 → sql_generation 重新生成
   - 没有详细字段信息 → schema.get_columns

4. **权限/连接错误**
   - 无法修复，标记为失败
```

**关键决策点**：
- Agent自主分析错误根本原因
- Agent选择修复策略（schema.get_columns / sql_generation / sql.refine）
- 系统只提供标记和提示，不硬编码修复逻辑

---

## 四、Context管理机制

### 4.1 Schema信息完整性保护

**在executor.py._reduce_context()中**：

```python
# ❌ 错误做法（当前版本）：删除column_details
if isinstance(context.get("column_details"), dict):
    details = context["column_details"]
    # 只保留3个表，每个表只保留20列
    if len(details) > 3:
        context["column_details"] = dict(list(details.items())[:3])

# ✅ 正确做法（backend-old）：保留所有表
if isinstance(context.get("column_details"), dict):
    details = context["column_details"]
    # 不再删除任何表的信息，保留完整的column_details
    # 如果某些表的列数过多（超过100列），可以适当裁剪
    for table, cols in list(details.items()):
        if isinstance(cols, dict) and len(cols) > 100:
            limited = {k: v for i, (k, v) in enumerate(cols.items()) if i < 100}
            details[table] = limited
    context["column_details"] = details
```

**为什么重要**：
- PTAV循环中，Agent可能在多轮迭代中引用不同的表
- 如果删除了column_details，后续轮次Agent就无法生成正确的SQL
- 关键原则：**column_details必须在PTAV循环的所有迭代中保持**

### 4.2 SQL生成提示词的字段显示

**在executor.py._build_sql_generation_prompt()中**：

```python
# ❌ 错误做法（当前版本）：只显示前10个字段
for table, cols_data in column_details.items():
    field_names = list(cols_data.keys())[:10]  # 只显示10个
    schema_details.append(f"{table}: {', '.join(field_names)}...")

# ✅ 正确做法（backend-old）：显示所有字段带类型和注释
for table, cols_data in column_details.items():
    field_descs = []
    for field_name, field_info in cols_data.items():  # 显示所有字段
        desc = field_name
        if field_info.get("type"):
            desc += f"({field_info['type']})"
        if field_info.get("comment"):
            desc += f" - {field_info['comment']}"
        field_descs.append(desc)
    schema_details.append(f"**{table}** ({len(cols_data)}列):\n    {fields_text}")
```

**为什么重要**：
- LLM需要看到完整的字段列表才能正确选择字段
- 字段类型和注释帮助LLM理解业务语义
- 只显示部分字段会导致LLM选择错误的字段

### 4.3 template_context保留

**在orchestrator.py._update_ai_with_context()中**：

```python
# ✅ 保留原始的template_context，避免丢失业务语义
if not tdc.get("template_context") and not tdc.get("template_context_snippet"):
    original_tdc = getattr(ai, 'task_driven_context', {}) or {}
    if original_tdc.get("template_context"):
        tdc["template_context"] = original_tdc["template_context"]
        self._logger.info(f"保留原始template_context")
```

---

## 五、LLM智能表选择

### 5.1 传统方式的问题

```python
# ❌ 硬编码关键词匹配（当前版本）
def _infer_table_keywords(self, description: str) -> List[str]:
    keywords = []
    if any(kw in description for kw in ["退货", "退款", "return", "refund"]):
        keywords.extend(["return", "refund"])
    return keywords
```

**缺陷**：
- 只支持固定的业务场景（退货/退款）
- 无法适应新的业务需求
- 关键词匹配不准确

### 5.2 LLM驱动的智能选择

**在executor.py._select_tables_with_llm()中**：

```python
async def _select_tables_with_llm(
    self,
    candidates: List[str],
    placeholder_desc: str,
    template_context: str,
    user_id: str,
    max_tables: int = 3
) -> List[str]:
    """使用LLM智能选择与需求最相关的表"""

    prompt = f"""
你是数据库专家。请从候选表中选择与业务需求最相关的表。

业务需求: {placeholder_desc}
模板上下文: {template_context}

候选表:
{chr(10).join([f"{i+1}. {t}" for i, t in enumerate(candidates)])}

请返回JSON:
{{
    "selected_tables": ["table1", "table2"],
    "reason": "选择原因"
}}
"""

    # 调用LLM分析
    result = await self._call_llm(llm_service, prompt, user_id)
    return result["selected_tables"]
```

**优势**：
- 基于语义理解选择表
- 适应任何业务场景
- 利用template_context提供更多上下文

---

## 六、智能退出机制

### 6.1 检测模式

**在orchestrator.py._analyze_execution_pattern()中**：

```python
def _analyze_execution_pattern(self, execution_context, iteration):
    """分析执行模式，判断是否应该智能退出"""

    # 1. 同一动作连续失败3次
    if len(set(last_3_actions)) == 1 and not any(last_3_success):
        return {"should_exit": True, "reason": f"重复执行{action}失败3次"}

    # 2. 多次尝试后仍无Schema信息
    if iteration > 3 and not execution_context.get("tables"):
        if schema_attempts >= 2:
            return {"should_exit": True, "reason": "多次尝试后仍无Schema信息"}

    # 3. 数据库连接频繁失败
    if connection_failures >= 3:
        return {"should_exit": True, "reason": "数据库连接频繁失败"}

    # 4. 5轮后仍无SQL生成
    if iteration > 5 and not has_sql:
        return {"should_exit": True, "reason": "5轮后仍无SQL生成"}
```

### 6.2 目标达成判断

```python
def _validate_goal_achievement(self, ai, execution_context, exec_result):
    # 1. SQL生成且数据库验证成功
    if (current_sql and
        context.get("sql_executed_successfully") and
        context.get("execution_result", {}).get("rows")):
        return {"goal_achieved": True}

    # 2. SQL通过语法验证但数据库连接失败（也算成功）
    if (current_sql and
        context.get("database_validated") is False and
        not context.get("issues") and
        "connection" in str(context.get("database_error"))):
        return {"goal_achieved": True, "note": "建议检查数据源连接"}

    # 3. 进入SQL修复循环
    if not exec_result.get("success") and current_sql and issues:
        # 最多3次修复尝试
```

---

## 七、核心设计理念总结

### 7.1 Agent优先原则

- **所有决策由Agent做出**：不硬编码业务逻辑
- **工具只执行**：工具是被动的，Agent是主动的
- **单步骤循环**：每次只执行一个操作，立即返回给Agent分析

### 7.2 Context管理原则

- **保留关键信息**：column_details, template_context必须保持
- **完整字段显示**：LLM需要看到所有字段才能正确决策
- **精简传递**：使用ResourcePool + ContextMemory减少token消耗

### 7.3 智能修复原则

- **Agent诊断**：由Agent分析错误根本原因
- **多策略支持**：schema刷新、SQL重新生成、语法修复
- **有限重试**：最多3次修复尝试，避免无限循环

### 7.4 稳定性保障

- **智能退出**：检测无效循环模式并及时退出
- **真实验证**：通过实际数据库执行验证SQL
- **状态维护**：在PTAV循环中维护完整的执行上下文

---

## 八、关键差异对比

| 特性 | Backend-Old (稳定版) | Backend (当前版) |
|------|---------------------|------------------|
| **Context管理** | ResourcePool模式，精简记忆 | 累积模式，context逐渐增大 |
| **Schema保留** | 保留所有表的column_details | 只保留3个表，每表20列 |
| **字段显示** | 显示所有字段带类型注释 | 只显示前10个字段 |
| **表选择** | LLM智能选择 (_select_tables_with_llm) | 硬编码关键词匹配 |
| **SQL修复** | Agent驱动，智能诊断修复策略 | 简单的if-else逻辑 |
| **Pre-SQL分析** | GatingController + ContextCurator | 简单的前置检查 |
| **智能退出** | 多种模式检测 | 基础的超时退出 |

---

## 九、为什么Backend-Old能稳定生成SQL

### 关键成功因素

1. **完整的Schema信息**
   - LLM看到所有表和所有字段
   - 带类型和注释，帮助理解业务语义
   - 在整个PTAV循环中保持，不被删除

2. **Agent驱动的决策**
   - 不硬编码业务逻辑
   - Agent自主分析问题并选择修复策略
   - LLM智能选择相关表

3. **智能的修复循环**
   - 准确诊断错误类型
   - 根据错误类型选择正确的修复策略
   - 最多3次尝试，有限重试

4. **精简的上下文传递**
   - ResourcePool模式避免token膨胀
   - ContextMemory只传递关键状态
   - 按需从ResourcePool提取详细信息

5. **完善的退出机制**
   - 检测重复失败模式
   - 检测无进展状态
   - 及时退出避免资源浪费

---

## 十、迁移建议

### 优先级P0（必须恢复）

1. **executor.py._reduce_context()** - 保留所有column_details
2. **executor.py._build_sql_generation_prompt()** - 显示所有字段带类型注释
3. **ResourcePool模式** - 精简上下文传递

### 优先级P1（强烈建议）

1. **executor.py._select_tables_with_llm()** - LLM智能表选择
2. **orchestrator.py SQL修复循环** - Agent驱动的智能修复
3. **planner.py SQL修复提示词** - 增强的修复策略引导

### 优先级P2（可选优化）

1. **GatingController** - Pre-condition检查
2. **ContextCurator** - Context组装优化
3. **智能退出机制** - 多种模式检测

### 迁移策略

**不建议**：直接复制整个agents文件夹
- 可能覆盖当前版本的其他改进
- 缺少对差异的理解
- 难以维护和调试

**建议**：选择性恢复
- 逐个文件/方法进行对比和恢复
- 理解每个变化的原因和影响
- 保留当前版本中有价值的改进
- 充分测试每次恢复

---

## 十一、实现路径

### 阶段1：Core Fixes（核心修复）

```bash
# 1. 恢复executor.py的关键方法
- _reduce_context: 保留所有column_details
- _build_sql_generation_prompt: 显示所有字段
- _select_tables_with_llm: LLM智能表选择

# 2. 复制ResourcePool相关文件
- resource_pool.py (ContextMemory + ResourcePool)
- context_curator.py (ContextCurator)
- gating_controller.py (GatingController)
```

### 阶段2：Enhanced Loop（增强循环）

```bash
# 3. 更新orchestrator.py
- ResourcePool初始化和更新
- SQL修复循环逻辑
- 智能退出机制
- _update_ai_with_context增强

# 4. 更新planner.py
- _build_sql_fix_prompt: SQL修复提示词
- _analyze_sql_fix_context: 修复上下文分析
```

### 阶段3：Context & Prompt（上下文和提示词）

```bash
# 5. 更新context_prompt_controller.py
- ResourcePool模式支持
- build_plan_prompt: 完整字段显示

# 6. 更新types.py
- ContextModeEnum
- PlaceholderInfo (Agent层)
```

### 阶段4：Testing（测试）

```bash
# 7. 完整测试
- 基础SQL生成
- SQL修复循环
- 复杂业务场景
- 边界情况处理
```

---

## 附录：关键代码片段

### A. ResourcePool初始化（orchestrator.py）

```python
# 初始化ResourcePool - 使用精简记忆模式
use_resource_pool = getattr(settings, 'ENABLE_CONTEXT_CURATION', True)
resource_pool = ResourcePool() if use_resource_pool else None

if use_resource_pool:
    self._logger.info(f"🗄️ [PTAV循环] 启用ResourcePool模式（精简记忆）")
```

### B. Column Details保留（executor.py）

```python
# column_details 保留所有表（不再删除！）
if isinstance(context.get("column_details"), dict):
    details = context["column_details"]
    # 不再删除任何表的信息，保留完整的column_details
    for table, cols in list(details.items()):
        if isinstance(cols, dict) and len(cols) > 100:
            limited = {k: v for i, (k, v) in enumerate(cols.items()) if i < 100}
            details[table] = limited
    context["column_details"] = details
```

### C. SQL修复提示词（planner.py）

```python
return f"""
你是SQL修复专家。当前SQL验证失败，需要你**智能分析错误原因**并制定修复策略。

## 修复策略提示
1. **字段名/表名不存在** → schema.get_columns 或 sql_generation
2. **SQL语法错误** → sql.refine
3. **时间字段选择错误** → sql_generation (有schema) 或 schema.get_columns (无schema)

## 重要提示
- **优先诊断**：先判断错误根本原因
- **单步执行**：每次只执行一个修复步骤
- **字段名错误必须重新生成**：有column_details时用sql_generation，不用sql.refine
"""
```

---

**文档版本**: 1.0
**分析日期**: 2025-10-17
**分析者**: Claude Code
**目的**: 为backend当前版本提供恢复指导
