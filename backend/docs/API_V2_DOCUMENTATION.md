# AutoReportAI API v2 文档

## 概述

API v2 是 AutoReportAI 的全新现代化后端架构，基于 FastAPI 构建，提供 RESTful API 接口。该版本专注于多用户体系、权限管理、数据隔离和现代化的 API 设计。

## 架构特点

- **多用户体系**: 完整的用户认证和授权系统
- **数据隔离**: 用户级别的数据权限控制
- **统一响应格式**: 标准化的 API 响应结构
- **分页支持**: 所有列表接口支持分页
- **权限管理**: 细粒度的权限控制系统
- **版本化**: 支持 API 版本演进

## 基础信息

- **Base URL**: `http://localhost:8000/api/v2`
- **认证方式**: Bearer Token (JWT)
- **Content-Type**: `application/json`
- **响应格式**: 统一使用 `ApiResponse` 包装

## 认证

### 注册
```http
POST /api/v2/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "username",
  "password": "password123",
  "full_name": "Full Name"
}
```

### 登录
```http
POST /api/v2/auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=password123
```

### 获取当前用户信息
```http
GET /api/v2/auth/me
Authorization: Bearer <token>
```

## 统一响应格式

所有 API 响应都使用以下格式：

```json
{
  "success": true,
  "data": {...},
  "message": "操作成功",
  "error": null
}
```

### 分页响应格式

```json
{
  "success": true,
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "size": 10,
    "pages": 10,
    "has_next": true,
    "has_prev": false
  },
  "message": "获取成功"
}
```

## API 端点

### 1. 认证相关 (/api/v2/auth)

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /register | 用户注册 |
| POST | /login | 用户登录 |
| POST | /logout | 用户登出 |
| GET  | /me | 获取当前用户信息 |
| POST | /refresh | 刷新访问令牌 |

### 2. 用户管理 (/api/v2/users)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET  | / | 获取用户列表（管理员） |
| GET  | /me | 获取当前用户信息 |
| GET  | /{user_id} | 获取特定用户 |
| PUT  | /me | 更新当前用户信息 |
| PUT  | /{user_id} | 更新用户信息（管理员） |
| DELETE | /{user_id} | 删除用户（管理员） |
| POST | /{user_id}/activate | 激活用户（管理员） |
| POST | /{user_id}/deactivate | 禁用用户（管理员） |

### 3. 数据源管理 (/api/v2/data-sources)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET  | / | 获取数据源列表 |
| POST | / | 创建数据源 |
| GET  | /{data_source_id} | 获取特定数据源 |
| PUT  | /{data_source_id} | 更新数据源 |
| DELETE | /{data_source_id} | 删除数据源 |
| POST | /{data_source_id}/test | 测试数据源连接 |
| POST | /{data_source_id}/sync | 同步数据源 |
| POST | /upload | 上传文件作为数据源 |

### 4. 模板管理 (/api/v2/templates)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET  | / | 获取模板列表 |
| POST | / | 创建模板 |
| GET  | /{template_id} | 获取特定模板 |
| PUT  | /{template_id} | 更新模板 |
| DELETE | /{template_id} | 删除模板 |
| POST | /{template_id}/duplicate | 复制模板 |
| POST | /upload | 上传模板文件 |

### 5. 报告管理 (/api/v2/reports)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET  | / | 获取报告历史列表 |
| POST | /generate | 生成报告 |
| GET  | /{report_id} | 获取特定报告 |
| DELETE | /{report_id} | 删除报告 |
| POST | /{report_id}/regenerate | 重新生成报告 |
| GET  | /{report_id}/download | 下载报告 |

### 6. 任务管理 (/api/v2/tasks)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET  | / | 获取任务列表 |
| POST | / | 创建任务 |
| GET  | /{task_id} | 获取特定任务 |
| PUT  | /{task_id} | 更新任务 |
| DELETE | /{task_id} | 删除任务 |
| POST | /{task_id}/run | 运行任务 |
| POST | /{task_id}/enable | 启用任务 |
| POST | /{task_id}/disable | 禁用任务 |

### 7. ETL作业管理 (/api/v2/etl-jobs)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET  | / | 获取ETL作业列表 |
| POST | / | 创建ETL作业 |
| GET  | /{etl_job_id} | 获取特定ETL作业 |
| PUT  | /{etl_job_id} | 更新ETL作业 |
| DELETE | /{etl_job_id} | 删除ETL作业 |
| POST | /{etl_job_id}/run | 运行ETL作业 |
| POST | /{etl_job_id}/enable | 启用ETL作业 |
| POST | /{etl_job_id}/disable | 禁用ETL作业 |
| GET  | /{etl_job_id}/status | 获取ETL作业状态 |

### 8. AI提供商管理 (/api/v2/ai-providers)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET  | / | 获取AI提供商列表 |
| POST | / | 创建AI提供商 |
| GET  | /{ai_provider_id} | 获取特定AI提供商 |
| PUT  | /{ai_provider_id} | 更新AI提供商 |
| DELETE | /{ai_provider_id} | 删除AI提供商 |
| POST | /{ai_provider_id}/test | 测试AI提供商连接 |
| POST | /{ai_provider_id}/enable | 启用AI提供商 |
| POST | /{ai_provider_id}/disable | 禁用AI提供商 |

### 9. 仪表板 (/api/v2/dashboard)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET  | /stats | 获取仪表板统计数据 |
| GET  | /recent-activity | 获取最近活动 |
| GET  | /chart-data | 获取图表数据 |
| GET  | /system-health | 获取系统健康状态 |

### 10. 系统管理 (/api/v2/system)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET  | /health | 获取系统健康状态 |
| GET  | /metrics | 获取系统指标 |
| GET  | /logs | 获取系统日志 |
| POST | /maintenance | 触发系统维护 |
| GET  | /config | 获取系统配置 |
| PUT  | /config | 更新系统配置 |

## 查询参数

### 分页参数
- `skip`: 跳过的记录数 (默认: 0)
- `limit`: 返回的记录数 (默认: 100, 最大: 100)

### 搜索参数
- `search`: 搜索关键词
- `is_active`: 是否激活 (true/false)
- `source_type`: 数据源类型
- `template_type`: 模板类型
- `provider_type`: AI提供商类型

## 错误处理

### 错误响应格式
```json
{
  "success": false,
  "data": null,
  "message": "错误描述",
  "error": {
    "code": "ERROR_CODE",
    "details": "详细错误信息"
  }
}
```

### 常见错误码
- `400`: 请求参数错误
- `401`: 未授权
- `403`: 权限不足
- `404`: 资源不存在
- `422`: 验证错误
- `500`: 服务器内部错误

## 权限说明

### 权限级别
- `READ`: 读取权限
- `WRITE`: 写入权限
- `ADMIN`: 管理员权限

### 资源类型
- `USER`: 用户管理
- `DATA_SOURCE`: 数据源
- `TEMPLATE`: 模板
- `REPORT`: 报告
- `TASK`: 任务
- `ETL_JOB`: ETL作业
- `AI_PROVIDER`: AI提供商

## 使用示例

### 创建数据源
```bash
curl -X POST http://localhost:8000/api/v2/data-sources \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "销售数据",
    "source_type": "csv",
    "connection_string": "/data/sales.csv",
    "is_active": true
  }'
```

### 获取分页数据
```bash
curl -X GET "http://localhost:8000/api/v2/data-sources?skip=0&limit=10&search=sales" \
  -H "Authorization: Bearer <token>"
```

### 生成报告
```bash
curl -X POST http://localhost:8000/api/v2/reports/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "template-123",
    "data_source_id": 1
  }'
```

## 版本兼容性

- **v1 API**: 保持向后兼容，继续使用 `/api/v1/*`
- **v2 API**: 新的现代化接口，使用 `/api/v2/*`
- **推荐**: 新开发使用 v2 API，获得更好的性能和功能

## 开发指南

### 前端集成
1. 使用统一的 API 客户端
2. 处理分页响应
3. 实现错误处理
4. 添加加载状态
5. 缓存策略

### 最佳实践
1. 使用环境变量配置 API 地址
2. 实现请求/响应拦截器
3. 添加重试机制
4. 使用 TypeScript 类型定义
5. 实现权限检查

## 更新日志

### v2.0.0 (2024-01-01)
- 初始版本发布
- 多用户体系支持
- 统一响应格式
- 分页支持
- 权限管理
- 数据隔离
