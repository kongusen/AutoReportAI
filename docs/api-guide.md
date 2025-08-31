# AutoReportAI API 使用指南

本文档提供 AutoReportAI RESTful API 的详细使用说明。

## 🌐 API 基础信息

- **Base URL**: `http://localhost:8000/api`
- **API Version**: v1
- **Content-Type**: `application/json`
- **认证方式**: Bearer Token (JWT)

## 🔐 认证

### 用户注册
```http
POST /v1/auth/register
Content-Type: application/json

{
  "username": "admin",
  "email": "admin@example.com", 
  "password": "password"
}
```

### 用户登录
```http
POST /v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin&password=password
```

**响应示例:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

### 使用 Token
所有需要认证的请求都需要在 Header 中包含：
```http
Authorization: Bearer <access_token>
```

## 📊 核心 API 端点

### 1. 健康检查

#### 基础健康检查
```http
GET /health
```

#### 详细健康检查
```http
GET /health/detailed
```

**响应示例:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-29T16:54:56.857355",
  "version": "2.0.0",
  "environment": "development",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "services": {
      "status": "healthy"
    }
  }
}
```

### 2. 数据源管理

#### 获取数据源列表
```http
GET /v1/data-sources/
Authorization: Bearer <token>
```

#### 创建数据源
```http
POST /v1/data-sources/
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "MyDorisDataSource",
  "source_type": "doris",
  "doris_fe_hosts": ["192.168.61.30"],
  "doris_query_port": 9030,
  "doris_username": "root",
  "doris_password": "password",
  "doris_database": "default",
  "is_active": true
}
```

#### 测试数据源连接
```http
POST /v1/data-sources/{data_source_id}/test-connection
Authorization: Bearer <token>
```

### 3. 模板管理

#### 获取模板列表
```http
GET /v1/templates/
Authorization: Bearer <token>
```

#### 上传模板
```http
POST /v1/templates/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=@template.docx&name=MyTemplate&description=Template description
```

#### 解析模板占位符
```http
POST /v1/templates/{template_id}/parse-placeholders
Authorization: Bearer <token>
```

### 4. 占位符管理 (DAG架构)

#### 获取占位符列表
```http
GET /v1/placeholders/
Authorization: Bearer <token>
```

#### 获取模板的占位符
```http
GET /v1/placeholders/?template_id={template_id}
Authorization: Bearer <token>
```

#### 创建占位符
```http
POST /v1/placeholders/
Authorization: Bearer <token>
Content-Type: application/json

{
  "template_id": "template-uuid",
  "placeholder_name": "sales_data",
  "placeholder_text": "{{sales_data}}",
  "placeholder_type": "data",
  "content_type": "chart",
  "is_required": true,
  "execution_order": 1
}
```

#### DAG架构智能分析 (未来功能)
```http
POST /v1/placeholders/analyze
Authorization: Bearer <token>
Content-Type: application/json

{
  "template_id": "template-uuid",
  "analysis_mode": "template_sql_generation",
  "context": {
    "data_source_id": "datasource-uuid",
    "time_context": "monthly"
  }
}
```

### 5. 报告生成

#### 获取报告列表
```http
GET /v1/reports/
Authorization: Bearer <token>
```

#### 生成报告
```http
POST /v1/reports/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "template_id": "template-uuid",
  "data_source_id": "datasource-uuid",
  "output_format": "docx",
  "parameters": {
    "start_date": "2025-01-01",
    "end_date": "2025-01-31"
  }
}
```

### 6. 任务调度

#### 获取任务列表
```http
GET /v1/task-scheduler/tasks
Authorization: Bearer <token>
```

#### 创建定时任务
```http
POST /v1/task-scheduler/tasks
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Monthly Report",
  "template_id": "template-uuid",
  "data_source_id": "datasource-uuid",
  "schedule_expression": "0 0 1 * *",
  "is_active": true,
  "config": {
    "output_format": "docx",
    "email_recipients": ["user@example.com"]
  }
}
```

### 7. 图表测试

#### 获取支持的图表类型
```http
GET /v1/chart-test/chart-types
Authorization: Bearer <token>
```

#### 测试图表生成
```http
POST /v1/chart-test/test-chart
Authorization: Bearer <token>
Content-Type: application/json

{
  "chart_type": "bar",
  "data": {
    "labels": ["Q1", "Q2", "Q3", "Q4"],
    "datasets": [
      {
        "label": "Sales",
        "data": [100, 200, 150, 300]
      }
    ]
  },
  "options": {
    "title": "Quarterly Sales Report"
  }
}
```

### 8. LLM服务器管理

#### 获取LLM服务器列表
```http
GET /v1/llm-servers/
Authorization: Bearer <token>
```

#### 创建LLM服务器配置
```http
POST /v1/llm-servers/
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "OpenAI GPT-4",
  "provider": "openai",
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-...",
  "model_name": "gpt-4",
  "is_active": true
}
```

## 🔄 DAG架构智能流程

AutoReportAI 的核心优势在于 DAG (有向无环图) 架构，支持以下智能流程：

### 占位符分析流程

1. **模板场景 - SQL生成**
   ```http
   POST /v1/placeholders/analyze
   {
     "mode": "template_sql_generation",
     "template_content": "...",
     "template_id": "uuid",
     "user_id": "uuid"
   }
   ```

2. **模板场景 - 图表测试**
   ```http
   POST /v1/placeholders/analyze
   {
     "mode": "template_chart_testing",
     "placeholder_text": "{{sales_chart}}",
     "stored_sql_id": "sql-uuid",
     "test_data": {...}
   }
   ```

3. **任务场景 - SQL验证**
   ```http
   POST /v1/placeholders/analyze
   {
     "mode": "task_sql_validation",
     "task_id": "task-uuid",
     "execution_date": "2025-01-31",
     "task_period_config": {
       "period": "monthly",
       "start_date": "2025-01-01"
     }
   }
   ```

4. **任务场景 - 图表生成**
   ```http
   POST /v1/placeholders/analyze
   {
     "mode": "task_chart_generation", 
     "placeholder_text": "{{sales_chart}}",
     "etl_data": {...},
     "task_period_config": {
       "period": "weekly"
     }
   }
   ```

## 📝 响应格式

所有API响应都遵循统一格式：

### 成功响应
```json
{
  "success": true,
  "data": {...},
  "message": "操作成功",
  "timestamp": "2025-08-29T16:54:56.857355"
}
```

### 错误响应
```json
{
  "error": true,
  "message": "错误描述",
  "code": "ERROR_CODE",
  "details": {...},
  "timestamp": "2025-08-29T16:54:56.857355"
}
```

## 📊 状态码说明

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 🔍 调试和监控

### API 文档
访问 `http://localhost:8000/docs` 查看交互式 API 文档

### 监控端点
- **健康检查**: `/health`
- **详细健康检查**: `/health/detailed`
- **系统指标**: `/v1/system/metrics`
- **LLM监控**: `/v1/llm/status`

## 💡 最佳实践

1. **认证管理**
   - 定期刷新 Access Token
   - 安全存储 API 密钥

2. **错误处理**
   - 实现重试机制
   - 记录详细错误日志

3. **性能优化**
   - 使用分页查询大量数据
   - 合理设置请求超时时间

4. **DAG流程优化**
   - 根据场景选择合适的分析模式
   - 合理配置上下文参数

## 📚 更多资源

- [DAG架构设计文档](./AGENTS_DAG_ARCHITECTURE.md)
- [开发环境搭建](./development-setup.md)
- [部署指南](./deployment-guide.md)

---

*最后更新：2025-08-29*