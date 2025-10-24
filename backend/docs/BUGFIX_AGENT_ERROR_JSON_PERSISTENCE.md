# BugFix: Agent错误JSON被持久化到数据库导致ETL失败

## 问题描述

在ETL执行阶段，从数据库读取的SQL不是有效的SQL语句，而是一个错误JSON：

```
尝试的SQL: {"success": false, "error": "response_format_invalid", "original_response": "", "fallback_used": "error_json_wrapper"}
```

这导致Doris执行失败：

```
errCode = 2, detailMessage = Syntax error in line 1:
{"success": false, "error": ...
^
Encountered: {
Expected
```

## 根本原因

### 数据流程

正常流程应该是：
1. **Agent生成SQL** → 占位符分析阶段
2. **验证并持久化** → 存储到 `placeholder.generated_sql`
3. **ETL执行** → 从数据库读取 `generated_sql` 执行查询

但实际发生的是：
1. Agent执行失败或返回非SQL格式
2. Container的JSON validation fallback创建错误JSON
3. **错误JSON被当作SQL持久化到数据库** ❌
4. ETL从数据库读取这个错误JSON并尝试执行
5. Doris报语法错误

### 问题链条

#### 1. Agent返回错误JSON

从 `backend/app/core/container.py:318-328`：

```python
# Step 4: Ultimate fallback - create error JSON
error_response = {
    "success": False,
    "error": "response_format_invalid",
    "original_response": response[:200] + "..." if len(response) > 200 else response,
    "fallback_used": "error_json_wrapper"
}
```

当Loom Agent执行失败或返回非JSON/非SQL格式时，Container会创建这个错误JSON作为fallback。

#### 2. 输出解析未检测错误格式

在 `backend/app/services/application/placeholder/placeholder_service.py:210-248` (修复前)：

```python
# 修复前的代码
if isinstance(output, dict):
    generated_sql = output.get("sql", "")  # ✅ 正常情况
    # ...
elif isinstance(output, str):
    try:
        parsed = json.loads(output)
        generated_sql = parsed.get("sql", output)  # ❌ Bug：如果没有sql键，fallback到整个JSON！
```

**Bug**: 当`parsed`是错误JSON（没有`sql`键）时，`parsed.get("sql", output)` 会fallback到`output`，即整个错误JSON字符串被赋值给`generated_sql`。

#### 3. 缺乏SQL格式验证

修复前没有检查 `generated_sql` 是否真的是SQL：
- 没有检查是否以 `SELECT`/`WITH` 开头
- 没有检查是否是JSON格式（不应该是）
- 错误JSON通过了所有检查

#### 4. 错误JSON被持久化

在 `backend/app/services/infrastructure/task_queue/tasks.py:444`：

```python
if sql_result.get("success"):
    ph.generated_sql = sql_result["sql"]  # ← 错误JSON被存储
    ph.sql_validated = True  # ← 错误地标记为已验证
    db.commit()
```

#### 5. ETL读取并尝试执行

在 `tasks.py:602-617`：

```python
final_sql = ph.generated_sql  # ← 从数据库读取错误JSON
# ... 占位符替换 ...
query_result = await connector.execute_query(final_sql)  # ← 尝试执行JSON
```

Doris收到的SQL是：
```json
{"success": false, "error": "response_format_invalid", ...}
```

自然报语法错误。

## 修复方案

### 1. 增强错误检测（placeholder_service.py:210-267）

```python
if isinstance(output, dict):
    # ✅ 检查是否是错误响应
    if output.get("success") is False or ("error" in output and "sql" not in output):
        error_msg = output.get("error", "Agent返回错误格式")
        logger.error(f"❌ Agent返回错误响应: {error_msg}, 完整输出: {output}")
        raise RuntimeError(f"Agent执行失败: {error_msg}")

    generated_sql = output.get("sql", "")
    # ...
elif isinstance(output, str):
    try:
        parsed = json.loads(output)

        # ✅ 检查是否是错误响应
        if parsed.get("success") is False or ("error" in parsed and "sql" not in parsed):
            error_msg = parsed.get("error", "Agent返回错误格式")
            raise RuntimeError(f"Agent执行失败: {error_msg}")

        # ✅ 修复：如果没有sql键，返回空字符串而不是整个JSON
        generated_sql = parsed.get("sql", "")
```

### 2. 增加SQL格式验证（placeholder_service.py:249-267）

```python
# 验证生成的SQL
if not generated_sql or not generated_sql.strip():
    raise RuntimeError("Agent未能生成有效的SQL")

# ✅ 额外验证：确保是SQL语句而不是JSON
sql_stripped = generated_sql.strip()
if sql_stripped.startswith("{") and sql_stripped.endswith("}"):
    try:
        json.loads(sql_stripped)
        raise RuntimeError("Agent返回的是JSON而不是SQL语句")
    except json.JSONDecodeError:
        pass  # 不是有效JSON，可能是特殊的SQL

# ✅ 验证是否以SELECT/WITH开头
sql_upper = sql_stripped.upper()
if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
    raise RuntimeError(f"生成的内容不是有效的SQL查询: {sql_stripped[:100]}...")
```

### 3. 统一异常事件类型（placeholder_service.py:295-304）

```python
except Exception as e:
    logger.error(f"占位符分析失败: {e}")

    # ✅ 统一使用 sql_generation_failed 事件，方便下游处理
    yield {
        "type": "sql_generation_failed",
        "placeholder_id": request.placeholder_id,
        "error": str(e),
        "timestamp": datetime.now().isoformat()
    }
```

**修复前**：异常时yield `analysis_error` 事件，但 `_generate_sql_with_agent` 不监听这个事件。

**修复后**：统一使用 `sql_generation_failed`，被下游正确处理。

## 修复效果

### 修复前

1. Agent返回错误JSON
2. 错误JSON被当作SQL持久化到数据库
3. ETL读取并尝试执行JSON
4. Doris报语法错误
5. ❌ 所有占位符ETL失败

### 修复后

1. Agent返回错误JSON
2. ✅ 错误检测逻辑识别出这是错误响应
3. ✅ 抛出RuntimeError: "Agent执行失败: response_format_invalid"
4. ✅ yield `sql_generation_failed` 事件
5. ✅ `_generate_sql_with_agent` 返回 `{"success": False, "error": "..."}`
6. ✅ tasks.py 检查到 `success=False`，**不持久化到数据库**
7. ✅ 日志记录清晰的错误信息
8. ✅ 其他占位符继续处理

## 保护层级

修复后有多层保护机制：

### Layer 1: 错误响应检测
```python
if output.get("success") is False or ("error" in output and "sql" not in output):
    raise RuntimeError(f"Agent执行失败: {error_msg}")
```

### Layer 2: 空值检查
```python
if not generated_sql or not generated_sql.strip():
    raise RuntimeError("Agent未能生成有效的SQL")
```

### Layer 3: JSON格式检查
```python
if sql_stripped.startswith("{") and sql_stripped.endswith("}"):
    try:
        json.loads(sql_stripped)
        raise RuntimeError("Agent返回的是JSON而不是SQL语句")
```

### Layer 4: SQL语法基本检查
```python
if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
    raise RuntimeError(f"生成的内容不是有效的SQL查询")
```

### Layer 5: 持久化前的success检查
```python
# tasks.py:442
if sql_result.get("success"):
    ph.generated_sql = sql_result["sql"]
else:
    # 不持久化，记录错误
    logger.error(f"❌ 占位符 {ph.placeholder_name} SQL生成失败: {error_msg}")
```

## 日志输出改进

### 修复前
```
[ERROR] 占位符分析失败: 'NoneType' object has no attribute 'tables'
```
信息不足，无法定位问题。

### 修复后
```
[ERROR] ❌ Agent返回错误响应: response_format_invalid, 完整输出: {"success": false, "error": "response_format_invalid", "original_response": "", "fallback_used": "error_json_wrapper"}
[ERROR] 占位符分析失败: Agent执行失败: response_format_invalid
[ERROR] ❌ 占位符 统计:退货原因... SQL生成失败: Agent执行失败: response_format_invalid
```

清晰显示：
1. Agent返回了什么
2. 为什么被拒绝
3. 哪个占位符受影响

## 下一步调查

虽然修复了症状（防止错误JSON被持久化），但需要调查根本原因：

### 为什么Agent返回 `response_format_invalid`？

可能原因：
1. ⚠️ Loom Agent没有正确使用工具（schema.list_tables等）
2. ⚠️ Agent的输出不是预期的JSON格式
3. ⚠️ Agent执行超时或其他异常

### 建议排查步骤

1. **启用Agent调试日志**：
```python
logging.getLogger("app.services.infrastructure.agents").setLevel(logging.DEBUG)
```

2. **检查Agent工具注册**：
确认ReAct模式下工具是否正确注册和可用。

3. **检查Agent提示词**：
验证 `analyze_placeholder` 中构建的 `task_prompt` 是否清晰。

4. **测试单个占位符**：
使用单个占位符测试ReAct流程，查看Agent的完整输出。

## 相关文档

- [ReAct模式SQL生成](./REACT_MODE_SQL_GENERATION.md)
- [ReAct模式schema=None修复](./BUGFIX_REACT_SCHEMA_NONE.md)
- [手动验证删除说明](./MANUAL_VALIDATION_REMOVAL.md)

## 总结

这个bug揭示了数据流程中缺乏充分的验证和错误处理：

### 问题
- ❌ Agent错误被静默通过
- ❌ 错误JSON被当作SQL持久化
- ❌ ETL执行时才发现问题（太晚了）

### 修复
- ✅ 多层验证机制
- ✅ 及时识别和拒绝错误响应
- ✅ 防止错误数据持久化
- ✅ 清晰的错误日志

### 教训
**"在数据流经数据库之前，必须经过严格验证"**

这符合你强调的PTAV原则：Plan → Tool → Action → **Validate**

验证不仅在Agent层，也应该在持久化层！
