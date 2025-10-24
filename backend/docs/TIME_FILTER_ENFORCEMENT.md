# 时间过滤强制机制

## 问题背景

用户反馈：所有占位符都是基于时间周期的统计，但Agent生成的SQL可能遗漏时间过滤条件。

### 示例

❌ **错误的SQL**（没有时间过滤）:
```sql
SELECT SUM(amount) AS total_refund_amount
FROM ods_refund
WHERE flow_status = '退货成功' AND is_deleted = 0;
```
**问题**: 统计了全部历史数据，而不是周期内的数据

✅ **正确的SQL**（有时间过滤）:
```sql
SELECT COUNT(*) AS total_refund_requests
FROM ods_refund
WHERE dt = '{{start_date}}' AND is_deleted = 0;
```
**正确**: 只统计指定日期的数据

## 解决方案

### 1. 强化SQL生成提示

在Step 2 SQL Generation阶段，明确要求Agent必须添加时间过滤：

```python
## ⚠️ 时间过滤要求（必须遵守）
**这是一个基于时间周期的统计查询，必须包含时间过滤条件！**

- 可用的时间字段: dt, date, create_time, ...
- 必须在WHERE子句中使用时间字段进行过滤
- 推荐使用占位符格式: WHERE dt = '{{start_date}}'
```

### 2. 增强SQL验证

在Step 3 SQL Validation阶段，检查是否包含时间过滤：

```python
# 验证结果
{
    "is_valid": False,
    "errors": ["⚠️ 缺少时间过滤条件！这是基于时间周期的统计查询"],
    "suggestions": [
        "请添加时间过滤，可用的时间字段: dt, date",
        "示例: WHERE dt = '{{start_date}}'",
        "或: WHERE dt BETWEEN '{{start_date}}' AND '{{end_date}}'"
    ],
    "has_time_filter": False
}
```

### 3. 自动修复机制

在Step 3.5 SQL Refinement阶段，如果检测到缺少时间过滤，自动触发Agent修复：

```python
# 流程
1. 检测到缺少时间过滤
2. 触发refinement
3. Agent在原SQL基础上添加时间过滤
4. 重新验证
5. 返回修复后的SQL
```

## 代码修改

### 修改的方法

1. **`_generate_sql_with_schema`** - 增强时间过滤要求
   - 识别schema中的时间字段
   - 在prompt中明确要求使用时间过滤
   - 提供具体的时间字段和占位符格式

2. **`_validate_sql`** - 增加时间过滤检查
   - 新增参数: `require_time_filter=True`
   - 检查SQL中是否使用了时间字段
   - 返回 `has_time_filter` 标志

3. **`_identify_time_columns`** - 识别时间字段
   - 识别常见的时间字段名模式
   - 返回所有可用的时间字段列表

4. **`_refine_sql_add_time_filter`** - 自动添加时间过滤
   - 使用Agent智能添加时间条件
   - 保持原SQL逻辑不变
   - 返回优化后的SQL

### 主流程变化

```python
Step 1: Schema Discovery
  ↓
Step 2: SQL Generation (强化：必须包含时间过滤)
  ↓
Step 3: SQL Validation (增强：检查时间过滤)
  ↓
Step 3.5: SQL Refinement (新增：自动修复缺少时间过滤)
  ↓
Step 4: SQL Test
```

## 使用效果

### Before（之前）
```sql
-- Agent生成的SQL
SELECT SUM(amount) FROM ods_refund WHERE flow_status = '退货成功'

-- 验证结果：通过 ✅（但实际有问题）
-- 统计结果：全部历史数据 ❌
```

### After（现在）
```sql
-- Agent生成的SQL
SELECT SUM(amount) FROM ods_refund WHERE flow_status = '退货成功'

-- 验证结果：失败 ❌
-- 错误：⚠️ 缺少时间过滤条件！

-- 自动Refinement触发
-- Agent优化后的SQL：
SELECT SUM(amount) FROM ods_refund
WHERE flow_status = '退货成功'
AND dt = '{{start_date}}'  -- ✅ 自动添加了时间过滤

-- 验证结果：通过 ✅
-- 统计结果：周期内数据 ✅
```

## 时间字段识别

系统会自动识别以下时间字段模式：

### 完全匹配
- `dt`, `date`, `time`, `datetime`, `timestamp`
- `created`, `updated`, `deleted`
- `create_time`, `update_time`, `delete_time`
- `created_at`, `updated_at`, `deleted_at`

### 后缀匹配
- `*_date` (例如: `start_date`, `end_date`, `order_date`)
- `*_time` (例如: `refund_time`, `pay_time`)
- `*_at` (例如: `confirmed_at`, `cancelled_at`)
- `*_datetime`, `*_timestamp`

### 前缀匹配
- `date_*`, `time_*`, `dt_*`

## 占位符格式

系统推荐使用以下占位符格式：

### 单日期
```sql
WHERE dt = '{{start_date}}'
```

### 日期范围
```sql
WHERE dt BETWEEN '{{start_date}}' AND '{{end_date}}'
```

### 多条件
```sql
WHERE dt = '{{start_date}}'
AND flow_status = '退货成功'
AND is_deleted = 0
```

## 验证流程

```
SQL生成
  ↓
识别时间字段: [dt, date, create_time]
  ↓
检查SQL中是否使用了时间字段
  ↓
  ├─ 是 → has_time_filter=true ✅
  │         验证通过
  │
  └─ 否 → has_time_filter=false ❌
            错误: "缺少时间过滤条件"
            建议: ["使用dt字段", "WHERE dt = '{{start_date}}'"]
            ↓
          触发Refinement
            ↓
          Agent添加时间过滤
            ↓
          重新验证 → 通过 ✅
```

## 事件输出

### 验证失败事件
```json
{
  "type": "stage_completed",
  "stage": "sql_validation",
  "message": "SQL验证发现问题",
  "data": {
    "is_valid": false,
    "has_time_filter": false,
    "errors": ["⚠️ 缺少时间过滤条件！这是基于时间周期的统计查询"],
    "suggestions": [
      "请添加时间过滤，可用的时间字段: dt, date",
      "示例: WHERE dt = '{{start_date}}'"
    ]
  }
}
```

### Refinement事件
```json
{
  "type": "stage_started",
  "stage": "sql_refinement",
  "message": "SQL缺少时间过滤，正在优化..."
}

{
  "type": "stage_completed",
  "stage": "sql_refinement",
  "message": "SQL优化完成，已添加时间过滤",
  "data": {
    "refined_sql": "SELECT ... WHERE dt = '{{start_date}}'",
    "refinement_reasoning": "添加了dt字段作为时间过滤条件",
    "validation_result": {
      "is_valid": true,
      "has_time_filter": true
    }
  }
}
```

## 配置选项

### 禁用时间过滤检查（特殊情况）

如果某些占位符确实不需要时间过滤，可以在请求中设置：

```python
request.context = {
    "require_time_filter": False  # 禁用时间过滤检查
}
```

**注意**: 这只应该在非常特殊的情况下使用，比如统计全局配置信息等。

## 优势

1. ✅ **防止统计错误** - 确保所有周期性统计都包含时间过滤
2. ✅ **自动修复** - 无需手动干预，Agent自动添加时间条件
3. ✅ **智能识别** - 自动识别多种时间字段模式
4. ✅ **清晰提示** - 提供具体的修复建议和示例
5. ✅ **质量保证** - 修复后重新验证，确保SQL正确

## 总结

通过三层保障机制：
1. **生成阶段** - 明确要求添加时间过滤
2. **验证阶段** - 检查是否包含时间过滤
3. **修复阶段** - 自动添加缺失的时间过滤

确保所有基于时间周期的统计查询都包含正确的时间过滤条件，从根本上避免统计错误。
