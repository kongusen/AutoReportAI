# API 端点自动生成文档

**生成时间**: 2025-07-18 15:55:41
**API版本**: 1.0.0

## 端点列表

### 版本信息

#### GET /api/v1/versions/

**摘要**: List All Versions
**描述**: 获取所有版本信息

```bash
curl -X GET "http://localhost:8000/api/v1/versions/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/versions/{version}

**摘要**: Get Specific Version
**描述**: 获取特定版本信息

```bash
curl -X GET "http://localhost:8000/api/v1/versions/{version}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 认证

#### POST /api/v1/auth/access-token

**摘要**: Login Access Token
**描述**: OAuth2 compatible token login, get an access token for future requests.

```bash
curl -X POST "http://localhost:8000/api/v1/auth/access-token" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 用户管理

#### GET /api/v1/users/me

**摘要**: Read User Me
**描述**: Get current user.

```bash
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/users/{user_id}

**摘要**: Read User By Id
**描述**: Get a specific user by id.

```bash
curl -X GET "http://localhost:8000/api/v1/users/{user_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### AI提供商

#### POST /api/v1/ai-providers/

**摘要**: Create Ai Provider
**描述**: Create a new AI provider configuration.

```bash
curl -X POST "http://localhost:8000/api/v1/ai-providers/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/ai-providers/

**摘要**: Read Ai Providers
**描述**: Retrieve AI providers.

```bash
curl -X GET "http://localhost:8000/api/v1/ai-providers/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/ai-providers/active

**摘要**: Get Active Ai Provider
**描述**: Get the currently active AI provider configuration.

```bash
curl -X GET "http://localhost:8000/api/v1/ai-providers/active" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### PUT /api/v1/ai-providers/{provider_id}

**摘要**: Update Ai Provider
**描述**: Update an AI provider configuration.

```bash
curl -X PUT "http://localhost:8000/api/v1/ai-providers/{provider_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### DELETE /api/v1/ai-providers/{provider_id}

**摘要**: Delete Ai Provider
**描述**: Delete an AI provider configuration.

```bash
curl -X DELETE "http://localhost:8000/api/v1/ai-providers/{provider_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/ai-providers/{provider_id}

**摘要**: Get Ai Provider
**描述**: Get a specific AI provider by ID.

```bash
curl -X GET "http://localhost:8000/api/v1/ai-providers/{provider_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/ai-providers/{provider_id}/test

**摘要**: Test Ai Provider Connection
**描述**: Test the connection to an AI provider.

```bash
curl -X POST "http://localhost:8000/api/v1/ai-providers/{provider_id}/test" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/ai-providers/{provider_id}/activate

**摘要**: Activate Ai Provider
**描述**: Activate an AI provider (deactivates all others).

```bash
curl -X POST "http://localhost:8000/api/v1/ai-providers/{provider_id}/activate" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/ai-providers/{provider_id}/deactivate

**摘要**: Deactivate Ai Provider
**描述**: Deactivate an AI provider.

```bash
curl -X POST "http://localhost:8000/api/v1/ai-providers/{provider_id}/deactivate" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/ai-providers/{provider_id}/models

**摘要**: Get Ai Provider Models
**描述**: Get available models for an AI provider.

```bash
curl -X GET "http://localhost:8000/api/v1/ai-providers/{provider_id}/models" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/ai-providers/health

**摘要**: Check Ai Providers Health
**描述**: Check the health status of all AI providers.

```bash
curl -X GET "http://localhost:8000/api/v1/ai-providers/health" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 数据源管理

#### POST /api/v1/data-sources/

**摘要**: Create Data Source
**描述**: Create a new data source.

```bash
curl -X POST "http://localhost:8000/api/v1/data-sources/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/data-sources/

**摘要**: Read Data Sources
**描述**: Retrieve data sources.

```bash
curl -X GET "http://localhost:8000/api/v1/data-sources/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/data-sources/{source_id}

**摘要**: Get Data Source
**描述**: Get a specific data source by ID.

```bash
curl -X GET "http://localhost:8000/api/v1/data-sources/{source_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### PUT /api/v1/data-sources/{source_id}

**摘要**: Update Data Source
**描述**: Update a data source.

```bash
curl -X PUT "http://localhost:8000/api/v1/data-sources/{source_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### DELETE /api/v1/data-sources/{source_id}

**摘要**: Delete Data Source
**描述**: Delete a data source.

```bash
curl -X DELETE "http://localhost:8000/api/v1/data-sources/{source_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/data-sources/{source_id}/test

**摘要**: Test Data Source Connection
**描述**: Test the connection to a data source.

```bash
curl -X POST "http://localhost:8000/api/v1/data-sources/{source_id}/test" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/data-sources/{source_id}/preview

**摘要**: Preview Data Source
**描述**: Preview data from a data source.

```bash
curl -X GET "http://localhost:8000/api/v1/data-sources/{source_id}/preview" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 增强数据源

#### POST /api/v1/enhanced-data-sources/

**摘要**: Create Enhanced Data Source
**描述**: 创建增强版数据源

```bash
curl -X POST "http://localhost:8000/api/v1/enhanced-data-sources/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/enhanced-data-sources/

**摘要**: Read Enhanced Data Sources
**描述**: 获取增强版数据源列表

```bash
curl -X GET "http://localhost:8000/api/v1/enhanced-data-sources/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/enhanced-data-sources/{data_source_id}

**摘要**: Read Enhanced Data Source
**描述**: 获取指定增强版数据源

```bash
curl -X GET "http://localhost:8000/api/v1/enhanced-data-sources/{data_source_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### PUT /api/v1/enhanced-data-sources/{data_source_id}

**摘要**: Update Enhanced Data Source
**描述**: 更新增强版数据源

```bash
curl -X PUT "http://localhost:8000/api/v1/enhanced-data-sources/{data_source_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/enhanced-data-sources/{data_source_id}/build-query

**摘要**: Build Wide Table Query
**描述**: 构建宽表查询

```bash
curl -X POST "http://localhost:8000/api/v1/enhanced-data-sources/{data_source_id}/build-query" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/enhanced-data-sources/{data_source_id}/validate-sql

**摘要**: Validate Sql Query
**描述**: 验证SQL查询

```bash
curl -X POST "http://localhost:8000/api/v1/enhanced-data-sources/{data_source_id}/validate-sql" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### MCP分析

#### POST /api/v1/mcp-analytics/analyze

**摘要**: Analyze Data
**描述**: 执行单种统计分析

```bash
curl -X POST "http://localhost:8000/api/v1/mcp-analytics/analyze" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/mcp-analytics/analyze/batch

**摘要**: Batch Analyze Data
**描述**: 批量执行多种统计分析

```bash
curl -X POST "http://localhost:8000/api/v1/mcp-analytics/analyze/batch" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/mcp-analytics/operations

**摘要**: List Analytics Operations
**描述**: 列出所有支持的统计分析操作

```bash
curl -X GET "http://localhost:8000/api/v1/mcp-analytics/operations" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/mcp-analytics/analyze/sample

**摘要**: Get Sample Analysis
**描述**: 获取示例分析数据

```bash
curl -X POST "http://localhost:8000/api/v1/mcp-analytics/analyze/sample" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 任务管理

#### GET /api/v1/tasks/

**摘要**: Read Tasks
**描述**: Retrieve tasks.

```bash
curl -X GET "http://localhost:8000/api/v1/tasks/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/tasks/

**摘要**: Create Task
**描述**: Create new task.

```bash
curl -X POST "http://localhost:8000/api/v1/tasks/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/tasks/{task_id}

**摘要**: Read Task
**描述**: Get task by ID.

```bash
curl -X GET "http://localhost:8000/api/v1/tasks/{task_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### PUT /api/v1/tasks/{task_id}

**摘要**: Update Task
**描述**: Update a task.

```bash
curl -X PUT "http://localhost:8000/api/v1/tasks/{task_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### DELETE /api/v1/tasks/{task_id}

**摘要**: Delete Task
**描述**: Delete a task.

```bash
curl -X DELETE "http://localhost:8000/api/v1/tasks/{task_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### ETL作业

#### POST /api/v1/etl-jobs/

**摘要**: Create Etl Job
**描述**: Create new ETL job. (Superuser only)

```bash
curl -X POST "http://localhost:8000/api/v1/etl-jobs/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/etl-jobs/

**摘要**: Read Etl Jobs
**描述**: Retrieve ETL jobs.

```bash
curl -X GET "http://localhost:8000/api/v1/etl-jobs/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/etl-jobs/{id}

**摘要**: Read Etl Job
**描述**: Get ETL job by ID.

```bash
curl -X GET "http://localhost:8000/api/v1/etl-jobs/{id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### PUT /api/v1/etl-jobs/{id}

**摘要**: Update Etl Job
**描述**: Update an ETL job. (Superuser only)

```bash
curl -X PUT "http://localhost:8000/api/v1/etl-jobs/{id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### DELETE /api/v1/etl-jobs/{id}

**摘要**: Delete Etl Job
**描述**: Delete an ETL job. (Superuser only)

```bash
curl -X DELETE "http://localhost:8000/api/v1/etl-jobs/{id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/etl-jobs/{id}/run

**摘要**: Trigger Etl Job
**描述**: Manually trigger an ETL job to run. (Superuser only)

```bash
curl -X POST "http://localhost:8000/api/v1/etl-jobs/{id}/run" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/etl-jobs/{id}/status

**摘要**: Get Etl Job Status
**描述**: Get the status of an ETL job.

```bash
curl -X GET "http://localhost:8000/api/v1/etl-jobs/{id}/status" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/etl-jobs/{id}/validate

**摘要**: Validate Etl Job
**描述**: Validate ETL job configuration.

```bash
curl -X POST "http://localhost:8000/api/v1/etl-jobs/{id}/validate" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/etl-jobs/{id}/dry-run

**摘要**: Dry Run Etl Job
**描述**: Perform a dry run of an ETL job (validate without executing).

```bash
curl -X POST "http://localhost:8000/api/v1/etl-jobs/{id}/dry-run" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/etl-jobs/data-source/{data_source_id}/tables

**摘要**: List Data Source Tables
**描述**: List available tables/data from a data source.

```bash
curl -X GET "http://localhost:8000/api/v1/etl-jobs/data-source/{data_source_id}/tables" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 报告生成

#### GET /api/v1/reports/

**摘要**: Get Reports Root
**描述**: Get available report generation endpoints.

```bash
curl -X GET "http://localhost:8000/api/v1/reports/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/reports/generate

**摘要**: Generate Report
**描述**: Generate a complete report based on task configuration.

```bash
curl -X POST "http://localhost:8000/api/v1/reports/generate" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/reports/preview

**摘要**: Preview Report Data
**描述**: Preview what data would be used for report generation.

```bash
curl -X GET "http://localhost:8000/api/v1/reports/preview" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/reports/validate

**摘要**: Validate Report Configuration
**描述**: Validate that a template and data source are compatible for report generation.

```bash
curl -X POST "http://localhost:8000/api/v1/reports/validate" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/reports/status/{task_id}

**摘要**: Get Generation Status
**描述**: Get report generation status for a task.

```bash
curl -X GET "http://localhost:8000/api/v1/reports/status/{task_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/reports/test

**摘要**: Test Report Pipeline
**描述**: Test the report generation pipeline with sample data.

```bash
curl -X POST "http://localhost:8000/api/v1/reports/test" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 模板分析

#### POST /api/v1/template-analysis

**摘要**: Create Template
**描述**: Upload a new .docx template, parse it, and save it to the database.

```bash
curl -X POST "http://localhost:8000/api/v1/template-analysis" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/template-analysis

**摘要**: List Templates
**描述**: List all available templates.

```bash
curl -X GET "http://localhost:8000/api/v1/template-analysis" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/template-analysis/{template_id}

**摘要**: Get Template
**描述**: Get a single template by ID.

```bash
curl -X GET "http://localhost:8000/api/v1/template-analysis/{template_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### DELETE /api/v1/template-analysis/{template_id}

**摘要**: Delete Template
**描述**: Delete a template from the filesystem and the database.

```bash
curl -X DELETE "http://localhost:8000/api/v1/template-analysis/{template_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 历史记录

#### GET /api/v1/history/

**摘要**: Read Report History
**描述**: Retrieve report history.

```bash
curl -X GET "http://localhost:8000/api/v1/history/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/history/{history_id}

**摘要**: Read Report History Item
**描述**: Get specific report history item by ID.

```bash
curl -X GET "http://localhost:8000/api/v1/history/{history_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/history/task/{task_id}

**摘要**: Read Task History
**描述**: Get report history for a specific task.

```bash
curl -X GET "http://localhost:8000/api/v1/history/task/{task_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 用户配置

#### GET /api/v1/user-profile/me

**摘要**: Read User Profile
**描述**: 获取当前用户的配置

```bash
curl -X GET "http://localhost:8000/api/v1/user-profile/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### PUT /api/v1/user-profile/me

**摘要**: Update User Profile
**描述**: 更新当前用户的配置

```bash
curl -X PUT "http://localhost:8000/api/v1/user-profile/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/user-profile/me

**摘要**: Create User Profile
**描述**: 创建当前用户的配置

```bash
curl -X POST "http://localhost:8000/api/v1/user-profile/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 模板管理

#### GET /api/v1/templates/

**摘要**: Read Templates
**描述**: 获取模板列表

```bash
curl -X GET "http://localhost:8000/api/v1/templates/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/templates/

**摘要**: Create Template
**描述**: 创建模板

```bash
curl -X POST "http://localhost:8000/api/v1/templates/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/templates/upload

**摘要**: Upload Template
**描述**: 上传模板文件

```bash
curl -X POST "http://localhost:8000/api/v1/templates/upload" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/templates/{template_id}

**摘要**: Read Template
**描述**: 获取特定模板

```bash
curl -X GET "http://localhost:8000/api/v1/templates/{template_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### PUT /api/v1/templates/{template_id}

**摘要**: Update Template
**描述**: 更新模板

```bash
curl -X PUT "http://localhost:8000/api/v1/templates/{template_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### DELETE /api/v1/templates/{template_id}

**摘要**: Delete Template
**描述**: 删除模板

```bash
curl -X DELETE "http://localhost:8000/api/v1/templates/{template_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 邮件设置

#### GET /api/v1/email-settings/email-settings

**摘要**: Get Email Settings
**描述**: Get user email settings.

```bash
curl -X GET "http://localhost:8000/api/v1/email-settings/email-settings" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### PUT /api/v1/email-settings/email-settings

**摘要**: Update Email Settings
**描述**: Update user email settings.

```bash
curl -X PUT "http://localhost:8000/api/v1/email-settings/email-settings" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/email-settings/test-email

**摘要**: Test Email Connection
**描述**: Test email connection with provided settings.

```bash
curl -X POST "http://localhost:8000/api/v1/email-settings/test-email" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/email-settings/send-test-email

**摘要**: Send Test Email
**描述**: Send a test email.

```bash
curl -X POST "http://localhost:8000/api/v1/email-settings/send-test-email" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 学习功能

#### POST /api/v1/learning/errors/record

**摘要**: Record Error
**描述**: 记录错误信息

```bash
curl -X POST "http://localhost:8000/api/v1/learning/errors/record" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/learning/feedback/submit

**摘要**: Submit Feedback
**描述**: 提交用户反馈

```bash
curl -X POST "http://localhost:8000/api/v1/learning/feedback/submit" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/learning/knowledge/query

**摘要**: Query Knowledge Base
**描述**: 查询知识库获取建议

```bash
curl -X POST "http://localhost:8000/api/v1/learning/knowledge/query" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/learning/learning/success

**摘要**: Record Learning Success
**描述**: 记录学习成功案例

```bash
curl -X POST "http://localhost:8000/api/v1/learning/learning/success" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/learning/statistics/errors

**摘要**: Get Error Statistics
**描述**: 获取错误统计信息

```bash
curl -X GET "http://localhost:8000/api/v1/learning/statistics/errors" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/learning/metrics

**摘要**: Get Learning Metrics
**描述**: 获取学习指标

```bash
curl -X GET "http://localhost:8000/api/v1/learning/metrics" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/learning/errors/categories

**摘要**: Get Error Categories
**描述**: 获取错误分类和严重程度选项

```bash
curl -X GET "http://localhost:8000/api/v1/learning/errors/categories" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/learning/health

**摘要**: Health Check
**描述**: 学习服务健康检查

```bash
curl -X GET "http://localhost:8000/api/v1/learning/health" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 智能占位符

#### POST /api/v1/intelligent-placeholders/analyze

**摘要**: 分析占位符
**描述**: 分析模板中的占位符

- **template_content**: 模板内容
- **template_id**: 模板ID（可选）
- **data_source_id**: 数据源ID（可选）
- **analysis_options**: 分析选项

返回识别的占位符列表、类型分布和验证结果。

```bash
curl -X POST "http://localhost:8000/api/v1/intelligent-placeholders/analyze" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/intelligent-placeholders/field-matching

**摘要**: 字段匹配验证
**描述**: 验证占位符的字段匹配

- **placeholder_text**: 占位符文本
- **placeholder_type**: 占位符类型
- **description**: 占位符描述
- **data_source_id**: 数据源ID
- **context**: 上下文信息（可选）
- **matching_options**: 匹配选项

返回字段匹配建议和置信度评估。

```bash
curl -X POST "http://localhost:8000/api/v1/intelligent-placeholders/field-matching" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/intelligent-placeholders/generate-report

**摘要**: 智能报告生成
**描述**: 使用智能占位符处理生成报告

- **template_id**: 模板ID
- **data_source_id**: 数据源ID
- **processing_config**: 处理配置
- **output_config**: 输出配置
- **email_config**: 邮件配置（可选）

返回任务ID和处理摘要，报告将在后台生成。

```bash
curl -X POST "http://localhost:8000/api/v1/intelligent-placeholders/generate-report" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/intelligent-placeholders/task/{task_id}/status

**摘要**: 查询任务状态
**描述**: 查询智能报告生成任务状态

- **task_id**: 任务ID

返回任务状态、进度和结果信息。

```bash
curl -X GET "http://localhost:8000/api/v1/intelligent-placeholders/task/{task_id}/status" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/intelligent-placeholders/statistics

**摘要**: 获取处理统计
**描述**: 获取智能占位符处理统计信息

返回处理统计、性能指标和使用情况。

```bash
curl -X GET "http://localhost:8000/api/v1/intelligent-placeholders/statistics" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 数据分析

#### POST /api/v1/analysis/experimental-analysis

**摘要**: Run Experimental Analysis
**描述**: An experimental endpoint to test the AI-driven tool dispatcher pipeline.

This simulates the full AI orchestrator workflow:
1. Parses a `{{type:description}}` placeholder.
2. **Uses a real AI** to interpret the `description` and create tool parameters.
3. Uses the `ToolDispatcherService` to execute the task.

```bash
curl -X POST "http://localhost:8000/api/v1/analysis/experimental-analysis" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /api/v1/analysis/run-analysis/{data_source_id}

**摘要**: Run Analysis

```bash
curl -X POST "http://localhost:8000/api/v1/analysis/run-analysis/{data_source_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 未分类

#### GET /api/v1/version

**摘要**: Get Api Version
**描述**: 获取API版本信息

```bash
curl -X GET "http://localhost:8000/api/v1/version" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/health

**摘要**: Health Check
**描述**: 基础API健康检查

```bash
curl -X GET "http://localhost:8000/api/v1/health" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/health/detailed

**摘要**: Detailed Health Check
**描述**: 详细的服务健康检查

```bash
curl -X GET "http://localhost:8000/api/v1/health/detailed" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/health/services

**摘要**: Services Health Check
**描述**: 服务模块健康检查

```bash
curl -X GET "http://localhost:8000/api/v1/health/services" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /api/v1/health/database

**摘要**: Database Health Check
**描述**: 数据库连接健康检查

```bash
curl -X GET "http://localhost:8000/api/v1/health/database" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### POST /notifications/send

**摘要**: Send Notification
**描述**: 发送通知API（用于测试）

```bash
curl -X POST "http://localhost:8000/notifications/send" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /notifications/status

**摘要**: Get Notification Status
**描述**: 获取通知系统状态

```bash
curl -X GET "http://localhost:8000/notifications/status" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### GET /

**摘要**: Read Root

```bash
curl -X GET "http://localhost:8000/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```
