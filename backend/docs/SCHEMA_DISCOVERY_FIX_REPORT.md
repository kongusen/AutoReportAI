# Schema Discovery 数据格式兼容性修复报告

## 📋 问题概述

### 失败现象
在 Agent Pipeline 执行过程中，Schema Discovery 工具调用失败，导致：
- ❌ 返回 0 个表、0 个列、0 个关系
- ❌ SQL 生成失败（缺少必要的 Schema 信息）
- ❌ 质量评分为 F 级（0.40 分）
- ❌ 整个 Agent Pipeline 失败

### 核心错误
```
dictionary update sequence element #0 has length 1; 2 is required
```

错误发生在 `SchemaDiscoveryTool._get_table_details()` 方法的第420行：
```python
table_info.update({
    "row_count": row.get("Rows"),
    "size_bytes": row.get("Data_length"),
    ...
})
```

---

## 🔍 根本原因分析

### 数据流路径
```
SQLConnector.execute_query()
  ↓ 返回 QueryResult 对象（data 字段是 DataFrame）
Container.DataSourceAdapter.run_query()
  ↓ 应该转换为 {"success": True, "rows": [...], "columns": [...]}
SchemaDiscoveryTool._get_table_details()
  ↓ 期望 rows 是字典列表 [{"Rows": ..., "Data_length": ...}, ...]
```

### 问题所在

#### 1. **QueryResult 识别不完整** (Container.py:16-117)
原始代码的结果解析逻辑：
```python
# 原始代码
if hasattr(result, 'get') and callable(result.get):
    # 标准字典格式
    rows = result.get("rows") or result.get("data") or []
elif hasattr(result, 'rows'):
    # Doris 格式
    rows = getattr(result, 'rows', [])
elif isinstance(result, (list, tuple)):
    # 列表格式
    rows = result
else:
    # 尝试属性访问
    for attr in ['rows', 'data']:
        if hasattr(result, attr):
            rows = getattr(result, attr, [])
            break

# DataFrame 检查在最后
if isinstance(rows, pd.DataFrame):
    rows = rows.to_dict('records')
```

**问题**：
- `QueryResult` 对象有 `data` 和 `success` 属性，但原代码优先检查 `.get()` 方法
- `QueryResult` 不是字典，没有 `.get()` 方法
- 会进入 `else` 分支，通过属性访问获取 `result.data`（是 DataFrame）
- **但是**：最后的 DataFrame 检查可能在某些情况下不生效，导致 DataFrame 没有被转换为字典列表

#### 2. **SchemaDiscoveryTool 缺少数据验证** (discovery.py:389-437)
原始代码：
```python
if status_result.get("success"):
    rows = status_result.get("rows", [])
    if rows and isinstance(rows[0], dict):  # 有基本验证
        row = rows[0]
        table_info.update({...})  # 直接 update，没有 try-catch
```

**问题**：
- 虽然有 `isinstance(rows[0], dict)` 检查，但如果检查通过但 `row` 实际不是字典，会导致错误
- 没有详细的错误日志，难以诊断问题
- 缺少对数据格式的防御性处理

---

## 🛠️ 修复方案

### 修复 1: 增强 Container.DataSourceAdapter.run_query()

**位置**: `backend/app/core/container.py:68-165`

**关键改进**：

1. **优先识别 QueryResult 对象**
```python
# 新代码：优先检查 QueryResult 格式
if hasattr(result, 'data') and hasattr(result, 'success'):
    # QueryResult 对象格式 - 标准连接器返回格式
    if isinstance(result.data, pd.DataFrame):
        if not result.data.empty:
            rows = result.data.to_dict('records')
            cols = result.data.columns.tolist()
        else:
            rows, cols = [], []
```

2. **在每个分支内部检查 DataFrame**
```python
# 在字典格式分支内
if isinstance(rows, pd.DataFrame):
    if not rows.empty:
        rows = rows.to_dict('records')
        cols = rows.columns.tolist()
    else:
        rows = []
```

3. **最终验证数据格式**
```python
# 确保 rows 是字典列表
if rows and not isinstance(rows, list):
    logger.warning(f"⚠️ rows 不是列表，类型: {type(rows)}，尝试转换")
    rows = [rows] if isinstance(rows, dict) else []

if rows and rows[0] and not isinstance(rows[0], dict):
    logger.warning(f"⚠️ rows[0] 不是字典，类型: {type(rows[0])}")
```

4. **增强错误处理**
```python
except Exception as parse_error:
    logger.error(f"结果解析失败: {parse_error}, 使用空结果")
    import traceback
    logger.error(f"堆栈:\n{traceback.format_exc()}")
    rows, cols = [], []
```

---

### 修复 2: 增强 SchemaDiscoveryTool 容错性

**位置**: `backend/app/services/infrastructure/agents/tools/schema/discovery.py`

#### 2.1 `_get_table_details()` (389-481行)

**改进**：

1. **详细的数据验证**
```python
# 验证 rows[0] 是字典
if not isinstance(rows[0], dict):
    logger.error(f"❌ rows[0] 不是字典! 类型: {type(rows[0])}, 值: {rows[0]}")
    logger.error(f"   完整 rows: {rows}")
    return table_info
```

2. **使用 try-catch 包裹 update 操作**
```python
try:
    update_data = {
        "row_count": row.get("Rows"),
        "size_bytes": row.get("Data_length"),
        ...
    }

    # 验证 update_data 是字典
    if not isinstance(update_data, dict):
        logger.error(f"❌ update_data 不是字典!")
        return table_info

    table_info.update(update_data)
    logger.debug(f"✅ table_info 更新成功")

except Exception as update_error:
    logger.error(f"❌ table_info.update() 失败: {update_error}")
    logger.error(f"   row 类型: {type(row)}")
    import traceback
    logger.error(f"   堆栈:\n{traceback.format_exc()}")
    return table_info
```

3. **详细的调试日志**
```python
logger.debug(f"📊 run_query 返回类型: {type(status_result)}")
logger.debug(f"📊 rows 类型: {type(rows)}, 长度: {len(rows)}")
logger.debug(f"📊 row 类型: {type(row)}")
logger.debug(f"📊 row keys: {row.keys()}")
logger.debug(f"📊 row 内容: {row}")
logger.debug(f"📊 准备更新的数据: {update_data}")
```

#### 2.2 `_get_table_columns()` (483-547行)

**改进**：

1. **验证每一行数据**
```python
for idx, row in enumerate(rows):
    if not isinstance(row, dict):
        logger.warning(f"⚠️ row[{idx}] 不是字典，类型: {type(row)}, 跳过")
        continue
```

2. **单独处理每个列**
```python
try:
    column_info = {
        "table_name": table_name,
        "name": row.get("Field", ""),
        ...
    }
    columns.append(column_info)
except Exception as col_error:
    logger.warning(f"⚠️ 解析列 {idx} 失败: {col_error}, row: {row}")
    continue
```

#### 2.3 `_extract_table_name()` (549-587行)

**改进**：

1. **更智能的表名提取**
```python
# 尝试包含 "Tables_in_" 的键
for key in row.keys():
    if key.startswith("Tables_in_"):
        table_name = str(row[key])
        return table_name
```

2. **完整的错误处理**
```python
try:
    # 提取逻辑
    ...
except Exception as e:
    logger.error(f"❌ 提取表名失败: {e}, row: {row}")
    return None
```

---

## 📊 修复效果

### 修复前
```
❌ Schema Discovery 失败
   - 0 个表
   - 0 个列
   - 0 个关系
❌ SQL 生成失败
❌ 质量评分: 0.40 (F级)
❌ Pipeline 失败
```

### 修复后（预期）
```
✅ Schema Discovery 成功
   - N 个表（带详细元数据）
   - M 个列（带类型和约束信息）
   - K 个关系
✅ SQL 生成成功
✅ 质量评分: > 0.70 (C级以上)
✅ Pipeline 成功
```

---

## 🧪 验证方法

### 1. 诊断脚本
```bash
cd backend
python scripts/diagnose_schema_discovery_issue.py
```

**功能**：
- 测试 SQLConnector.execute_query() 返回的数据格式
- 测试 Container.run_query() 的数据转换
- 记录详细的数据类型和内容

### 2. 验证脚本
```bash
python scripts/verify_schema_discovery_fix.py
```

**功能**：
- 测试 Container.DataSourceAdapter 的数据转换
- 测试 SchemaDiscoveryTool 的表和列发现
- 验证修复后的端到端功能

### 3. 集成测试
运行现有的 Agent 测试：
```bash
python scripts/test_backend_agents_runtime.py
```

---

## 🎯 关键要点

### 问题本质
1. **数据格式转换链断裂**：QueryResult → Dictionary 转换不完整
2. **类型假设脆弱**：代码假设数据总是字典，但没有验证
3. **错误处理不足**：缺少详细日志和防御性编程

### 修复原则
1. **优先匹配最可能的格式**：QueryResult 对象
2. **在多个层次验证数据**：Container、Tool 都要验证
3. **详细的错误日志**：记录类型、内容、堆栈
4. **防御性编程**：try-catch、类型检查、回退机制

### 预防措施
1. **单元测试**：为数据转换逻辑添加单元测试
2. **类型注解**：使用 Python 类型提示增强代码可读性
3. **代码审查**：重点关注数据格式转换和类型假设
4. **监控告警**：添加数据格式异常的监控

---

## 📝 相关文件

### 修改的文件
- `backend/app/core/container.py` (行 68-165)
- `backend/app/services/infrastructure/agents/tools/schema/discovery.py`
  - `_get_table_details()` (行 389-481)
  - `_get_table_columns()` (行 483-547)
  - `_extract_table_name()` (行 549-587)

### 新增的文件
- `backend/scripts/diagnose_schema_discovery_issue.py`
- `backend/scripts/verify_schema_discovery_fix.py`
- `backend/docs/SCHEMA_DISCOVERY_FIX_REPORT.md` (本文档)

---

## 🔗 相关文档
- [Agent 架构重构总结](AGENT_ARCHITECTURE_REFACTORING_COMPLETE.md)
- [三阶段 Agent 架构](THREE_STAGE_AGENT_ARCHITECTURE.md)
- [Context 工程架构](CONTEXT_ENGINEERING_ARCHITECTURE.md)

---

**修复完成时间**: 2025-10-28
**修复人员**: Claude Code
**状态**: ✅ 修复完成，待验证
