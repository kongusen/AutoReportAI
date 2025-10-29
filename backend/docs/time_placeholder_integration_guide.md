# 时间占位符集成指南

## 概述

本文档介绍了在占位符分析过程中新增的时间占位符生成功能。该功能能够自动生成时间占位符，支持后续不同周期任务中的快速时间参数替换。

## 功能特性

### 1. 自动时间占位符生成
- 基于时间窗口、cron表达式或执行时间自动生成时间占位符
- 支持多种时间格式和周期（日、周、月、季度、年）
- 生成SQL时间过滤条件占位符

### 2. 时间占位符类型
- **基础时间占位符**: `start_date`, `end_date`, `execution_date`, `current_date`
- **SQL过滤占位符**: `{time_column}_filter`, `{time_column}_between`, `{time_column}_range`
- **时间范围占位符**: `time_range`, `period_description`, `date_range`
- **周期相关占位符**: `period_type`, `data_range`, `period_key`

### 3. 集成到现有任务流程
- 单个占位符分析任务
- 批量占位符分析任务
- 带上下文占位符分析任务

## API 接口

### 1. 单个占位符异步分析

```http
POST /v1/placeholders/analyze-async
```

**请求参数:**
```json
{
  "placeholder_name": "销售数据统计",
  "placeholder_text": "统计昨日销售数据",
  "template_id": "template_123",
  "data_source_id": "ds_456",
  "time_window": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-01"
  },
  "time_column": "sale_date",
  "data_range": "day"
}
```

**返回结果:**
```json
{
  "success": true,
  "data": {
    "task_id": "celery_task_123",
    "status": "submitted",
    "message": "占位符分析任务已提交"
  }
}
```

### 2. 批量占位符异步分析

```http
POST /v1/placeholders/batch-analyze-async
```

**请求参数:**
```json
{
  "template_id": "template_123",
  "data_source_id": "ds_456",
  "placeholders": [
    {
      "name": "销售数据统计",
      "text": "统计昨日销售数据"
    },
    {
      "name": "用户活跃度",
      "text": "统计昨日用户活跃度"
    }
  ],
  "time_window": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-01"
  },
  "time_column": "created_at",
  "data_range": "day"
}
```

### 3. 带上下文占位符异步分析

```http
POST /v1/placeholders/analyze-with-context-async
```

**请求参数:**
```json
{
  "placeholder_name": "销售数据统计",
  "placeholder_text": "统计昨日销售数据",
  "template_id": "template_123",
  "data_source_id": "ds_456",
  "context_data": {
    "time_window": {
      "start_date": "2024-01-01",
      "end_date": "2024-01-01"
    },
    "cron_expression": "0 9 * * *",
    "data_range": "day",
    "time_column": "sale_date"
  }
}
```

### 4. 任务状态查询

```http
GET /v1/placeholders/task-status/{task_id}
```

**返回结果:**
```json
{
  "success": true,
  "data": {
    "task_id": "celery_task_123",
    "status": "completed",
    "state": "SUCCESS",
    "progress": 100,
    "message": "任务执行完成",
    "result": {
      "analysis_result": { ... },
      "time_placeholders": {
        "start_date": "2024-01-01",
        "end_date": "2024-01-01",
        "execution_date": "2024-01-02",
        "sale_date_filter": "sale_date = '{{start_date}}'",
        "sale_date_between": "sale_date BETWEEN '{{start_date}}' AND '{{end_date}}'",
        "time_range": "2024-01-01 至 2024-01-01",
        "period_description": "数据日期: 2024-01-01",
        "period_type": "日",
        "data_range": "day",
        "period_key": "daily"
      },
      "time_context": {
        "data_start_time": "2024-01-01",
        "data_end_time": "2024-01-01",
        "execution_time": "2024-01-02T09:00:00",
        "period": "day"
      },
      "time_placeholder_count": 10
    },
    "time_placeholders": { ... },
    "time_context": { ... },
    "time_placeholder_count": 10
  }
}
```

## 时间占位符使用示例

### 1. SQL 中的时间占位符替换

```sql
-- 原始SQL
SELECT * FROM sales 
WHERE sale_date = '{{start_date}}' 
  AND created_at BETWEEN '{{start_date}}' AND '{{end_date}}'

-- 替换后的SQL
SELECT * FROM sales 
WHERE sale_date = '2024-01-01' 
  AND created_at BETWEEN '2024-01-01' AND '2024-01-01'
```

### 2. 时间过滤条件占位符

```sql
-- 使用生成的时间过滤占位符
SELECT * FROM sales 
WHERE {{sale_date_filter}}

-- 或使用范围过滤
SELECT * FROM sales 
WHERE {{sale_date_between}}
```

### 3. 时间范围描述

```python
# 在报告生成中使用时间范围描述
report_title = f"销售数据报告 - {time_placeholders['period_description']}"
time_range = time_placeholders['time_range']  # "2024-01-01 至 2024-01-01"
```

## 配置参数

### 1. 时间窗口配置
```json
{
  "time_window": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-01"
  }
}
```

### 2. Cron 表达式配置
```json
{
  "cron_expression": "0 9 * * *",  // 每天上午9点执行
  "execution_time": "2024-01-02T09:00:00"
}
```

### 3. 数据范围配置
- `day`: 日数据
- `week`: 周数据
- `month`: 月数据
- `quarter`: 季度数据
- `year`: 年数据

## 集成到现有任务流程

### 1. 在 execute_report_task 中使用

```python
# 在任务执行流程中，当 USE_CELERY_PLACEHOLDER_ANALYSIS=true 时
if config.USE_CELERY_PLACEHOLDER_ANALYSIS:
    # 为每个占位符触发异步分析任务
    for placeholder in placeholders:
        task_result = analyze_single_placeholder_task.delay(
            placeholder_name=placeholder.name,
            placeholder_text=placeholder.text,
            template_id=template_id,
            data_source_id=data_source_id,
            user_id=user_id,
            time_window=time_window,
            time_column=time_column,
            data_range=data_range
        )
        
        # 等待任务完成，获取时间占位符
        result = task_result.get()
        time_placeholders = result.get('time_placeholders', {})
        
        # 使用时间占位符进行SQL替换
        sql_with_time = replace_sql_placeholders(
            generated_sql, 
            time_placeholders
        )
```

### 2. 时间占位符验证

```python
from app.utils.time_placeholder_generator import time_placeholder_generator

# 验证SQL中的时间占位符
validation_result = time_placeholder_generator.validate_time_placeholders(
    sql=generated_sql,
    time_placeholders=time_placeholders
)

if not validation_result['is_valid']:
    missing_placeholders = validation_result['missing_placeholders']
    logger.warning(f"SQL中缺少时间占位符: {missing_placeholders}")
```

## 最佳实践

### 1. 时间占位符命名规范
- 使用描述性的占位符名称
- 保持与数据库字段名的一致性
- 使用标准的时间格式 (YYYY-MM-DD)

### 2. 错误处理
- 始终检查时间占位符生成是否成功
- 提供默认的时间值作为回退
- 记录时间占位符生成和替换的日志

### 3. 性能优化
- 批量分析时共享时间上下文
- 缓存常用的时间占位符
- 避免重复生成相同的时间占位符

## 故障排除

### 1. 时间占位符生成失败
- 检查时间窗口参数是否正确
- 验证cron表达式格式
- 确认执行时间格式

### 2. SQL替换失败
- 检查占位符格式是否正确 ({{placeholder}})
- 验证时间占位符是否存在于生成的字典中
- 确认SQL语法正确

### 3. 任务执行超时
- 检查 `PLACEHOLDER_ANALYSIS_TIMEOUT` 配置
- 优化时间占位符生成逻辑
- 考虑使用缓存机制

## 更新日志

### v1.0.0 (2024-01-02)
- 新增时间占位符生成工具类
- 集成到单个、批量和带上下文的占位符分析任务
- 更新API接口文档和返回结果
- 支持多种时间格式和周期
