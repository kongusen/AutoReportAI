# 占位符分析 Celery 任务集成指南

## 概述

本文档介绍如何将现有的单占位符分析能力复用到 Celery 任务机制中，实现异步、可扩展的占位符分析处理。

## 新增功能

### 1. Celery 任务

#### 单个占位符分析任务
- **任务名称**: `tasks.infrastructure.analyze_single_placeholder`
- **功能**: 使用完整的 Agent Pipeline 分析单个占位符
- **队列**: `infrastructure_queue`

#### 批量占位符分析任务
- **任务名称**: `tasks.infrastructure.batch_analyze_placeholders`
- **功能**: 并行处理多个占位符的分析
- **队列**: `infrastructure_queue`

#### 带上下文的占位符分析任务
- **任务名称**: `tasks.infrastructure.analyze_placeholder_with_context`
- **功能**: 支持更丰富的上下文信息传递
- **队列**: `infrastructure_queue`

### 2. API 端点

#### 异步单个占位符分析
```http
POST /v1/placeholders/analyze-async
```

#### 异步批量占位符分析
```http
POST /v1/placeholders/batch-analyze-async
```

#### 带上下文的异步占位符分析
```http
POST /v1/placeholders/analyze-with-context-async
```

#### 任务状态查询
```http
GET /v1/placeholders/task-status/{task_id}
```

#### 任务取消
```http
POST /v1/placeholders/cancel-task/{task_id}
```

## 配置选项

### 环境变量

```bash
# 启用 Celery 占位符分析（在任务执行中使用）
USE_CELERY_PLACEHOLDER_ANALYSIS=true

# 占位符分析超时时间（秒）
PLACEHOLDER_ANALYSIS_TIMEOUT=300
```

### 配置说明

- `USE_CELERY_PLACEHOLDER_ANALYSIS`: 控制是否在任务执行流程中使用 Celery 任务进行占位符分析
- `PLACEHOLDER_ANALYSIS_TIMEOUT`: 设置占位符分析任务的超时时间

## 使用示例

### 1. 异步单个占位符分析

```python
import requests

# 触发异步分析
response = requests.post('/v1/placeholders/analyze-async', json={
    "placeholder_name": "销售总额",
    "placeholder_text": "统计:本月销售总额",
    "template_id": "template-uuid",
    "data_source_id": "data-source-uuid",
    "template_context": {"period": "monthly"},
    "time_window": {
        "start": "2024-01-01 00:00:00",
        "end": "2024-01-31 23:59:59"
    },
    "execute_sql": True
})

task_id = response.json()["data"]["task_id"]

# 查询任务状态
status_response = requests.get(f'/v1/placeholders/task-status/{task_id}')
print(status_response.json())
```

### 2. 批量占位符分析

```python
# 触发批量分析
response = requests.post('/v1/placeholders/batch-analyze-async', json={
    "template_id": "template-uuid",
    "data_source_id": "data-source-uuid",
    "placeholders": [
        {"name": "销售总额", "text": "统计:本月销售总额"},
        {"name": "订单数量", "text": "统计:本月订单数量"},
        {"name": "客户数量", "text": "统计:本月新增客户数量"}
    ],
    "time_window": {
        "start": "2024-01-01 00:00:00",
        "end": "2024-01-31 23:59:59"
    }
})

task_id = response.json()["data"]["task_id"]
```

### 3. 带上下文的占位符分析

```python
# 触发带上下文的分析
response = requests.post('/v1/placeholders/analyze-with-context-async', json={
    "placeholder_name": "销售总额",
    "placeholder_text": "统计:本月销售总额",
    "template_id": "template-uuid",
    "data_source_id": "data-source-uuid",
    "context_data": {
        "business_context": {
            "department": "sales",
            "region": "north"
        },
        "time_context": {
            "period": "monthly",
            "fiscal_year": 2024
        },
        "document_context": {
            "template_type": "monthly_report",
            "section": "summary"
        }
    }
})
```

## 集成到现有任务执行流程

### 启用 Celery 占位符分析

在任务执行流程中，可以通过设置环境变量来启用 Celery 占位符分析：

```bash
export USE_CELERY_PLACEHOLDER_ANALYSIS=true
```

启用后，`execute_report_task` 将使用新的 Celery 任务进行占位符分析，而不是直接调用 Agent Pipeline。

### 优势

1. **异步处理**: 占位符分析在后台异步执行，不阻塞主任务
2. **可扩展性**: 可以独立扩展占位符分析 worker
3. **容错性**: 单个占位符分析失败不影响其他占位符
4. **监控**: 可以独立监控占位符分析任务的执行状态
5. **资源隔离**: 占位符分析任务可以运行在独立的 worker 上

## 监控和调试

### 任务状态查询

```python
# 查询任务状态
response = requests.get(f'/v1/placeholders/task-status/{task_id}')
status = response.json()["data"]

if status["status"] == "completed":
    result = status["result"]
    print(f"分析成功: {result['analysis_result']}")
elif status["status"] == "failed":
    print(f"分析失败: {status['error']}")
elif status["status"] == "running":
    print(f"分析中: {status['current_step']} ({status['progress']}%)")
```

### Celery 监控

可以通过 Celery 监控工具查看任务执行情况：

```bash
# 查看活跃任务
celery -A app.services.infrastructure.task_queue.celery_config inspect active

# 查看任务统计
celery -A app.services.infrastructure.task_queue.celery_config inspect stats
```

## 错误处理

### 常见错误

1. **任务超时**: 占位符分析超过配置的超时时间
2. **Agent Pipeline 失败**: 底层 Agent 分析失败
3. **数据源连接失败**: 无法连接到指定的数据源
4. **模板不存在**: 指定的模板ID不存在

### 错误恢复

- 任务失败时会记录详细的错误信息
- 可以通过任务状态查询获取错误详情
- 支持任务取消和重试机制

## 性能优化

### 批量处理

对于大量占位符，建议使用批量分析任务：

```python
# 将占位符分组处理
batch_size = 10
for i in range(0, len(placeholders), batch_size):
    batch = placeholders[i:i + batch_size]
    # 触发批量分析任务
```

### 资源管理

- 合理配置 Celery worker 数量
- 监控内存使用情况
- 设置适当的任务超时时间

## 迁移指南

### 从同步分析迁移到异步分析

1. **更新 API 调用**: 将同步的 `/analyze` 调用改为异步的 `/analyze-async`
2. **添加状态查询**: 实现任务状态查询逻辑
3. **处理异步结果**: 更新前端逻辑以处理异步返回的结果

### 配置更新

```bash
# 在 .env 文件中添加
USE_CELERY_PLACEHOLDER_ANALYSIS=true
PLACEHOLDER_ANALYSIS_TIMEOUT=300
```

## 总结

通过将占位符分析能力复用到 Celery 任务机制中，我们实现了：

1. **更好的可扩展性**: 可以独立扩展占位符分析处理能力
2. **更高的可靠性**: 异步处理避免了阻塞和超时问题
3. **更好的监控**: 可以独立监控和分析占位符处理性能
4. **更灵活的资源管理**: 可以根据需要调整占位符分析资源

这个集成保持了与现有 API 的兼容性，同时提供了更强大的异步处理能力。
