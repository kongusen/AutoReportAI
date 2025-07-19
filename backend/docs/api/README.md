# AutoReportAI API 文档

## 概述

AutoReportAI API 是一个基于 FastAPI 构建的 RESTful API，提供智能报告生成系统的完整功能。本文档提供了 API 的使用指南、最佳实践和详细的端点说明。

## 🚀 快速开始

### 1. 基础信息

- **API 版本**: v1.0.0
- **基础 URL**: `http://localhost:8000/api/v1`
- **文档 URL**: `http://localhost:8000/api/v1/docs` (Swagger UI)
- **ReDoc URL**: `http://localhost:8000/api/v1/redoc` (ReDoc)
- **OpenAPI 规范**: `http://localhost:8000/api/v1/openapi.json`

### 2. 认证

所有 API 请求都需要有效的 JWT 令牌进行认证。

```bash
# 获取访问令牌
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

响应示例：
```json
{
  "success": true,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

### 3. 使用令牌

在后续请求中包含 Authorization 头：

```bash
curl -X GET "http://localhost:8000/api/v1/templates" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 📚 API 使用指南

### 统一响应格式

所有 API 响应都遵循统一的格式：

```json
{
  "success": true,
  "message": "操作成功",
  "data": {
    // 实际数据内容
  },
  "error": null,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 错误处理

错误响应格式：

```json
{
  "success": false,
  "message": "错误描述",
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "details": {
      // 错误详细信息
    }
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

常见错误代码：
- `400`: 请求参数错误
- `401`: 未授权访问
- `403`: 权限不足
- `404`: 资源不存在
- `422`: 数据验证失败
- `429`: 请求频率超限
- `500`: 服务器内部错误

### 分页

列表接口支持分页参数：

```bash
curl -X GET "http://localhost:8000/api/v1/templates?skip=0&limit=20" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

参数说明：
- `skip`: 跳过的记录数（默认: 0）
- `limit`: 返回的记录数（默认: 100，最大: 1000）

### 过滤和排序

支持多种过滤条件：

```bash
# 按名称过滤模板
curl -X GET "http://localhost:8000/api/v1/templates?name=报告模板" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 按创建时间排序
curl -X GET "http://localhost:8000/api/v1/templates?sort=created_at&order=desc" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 🔧 核心功能使用示例

### 1. 模板管理

#### 创建模板

```bash
curl -X POST "http://localhost:8000/api/v1/templates" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "月度投诉分析报告",
    "description": "月度投诉数据分析报告模板",
    "content": "本月共收到{{统计:投诉总数}}件投诉，其中{{区域:主要投诉地区}}占比最高。",
    "template_type": "docx",
    "is_public": false
  }'
```

#### 上传模板文件

```bash
curl -X POST "http://localhost:8000/api/v1/templates/upload" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@template.docx" \
  -F "name=投诉分析模板" \
  -F "description=投诉数据分析报告模板" \
  -F "is_public=false"
```

### 2. 智能占位符处理

#### 分析占位符

```bash
curl -X POST "http://localhost:8000/api/v1/intelligent-placeholders/analyze" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_content": "本月{{统计:投诉总数}}件投诉中，{{区域:主要投诉地区}}占比最高。",
    "analysis_options": {
      "include_context": true,
      "confidence_threshold": 0.7
    }
  }'
```

#### 字段匹配验证

```bash
curl -X POST "http://localhost:8000/api/v1/intelligent-placeholders/field-matching" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "placeholder_text": "{{统计:投诉总数}}",
    "placeholder_type": "统计",
    "description": "投诉总数",
    "data_source_id": 1,
    "matching_options": {
      "confidence_threshold": 0.8,
      "max_suggestions": 5
    }
  }'
```

### 3. 智能报告生成

```bash
curl -X POST "http://localhost:8000/api/v1/intelligent-placeholders/generate-report" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "123e4567-e89b-12d3-a456-426614174000",
    "data_source_id": 1,
    "processing_config": {
      "llm_provider": "openai",
      "llm_model": "gpt-4",
      "enable_caching": true,
      "quality_check": true
    },
    "output_config": {
      "format": "docx",
      "include_charts": true,
      "quality_report": true
    },
    "email_config": {
      "recipients": ["user@example.com"],
      "subject": "智能生成报告",
      "include_summary": true
    }
  }'
```

### 4. 数据源管理

#### 创建数据源

```bash
curl -X POST "http://localhost:8000/api/v1/data-sources" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "投诉数据库",
    "description": "投诉管理系统数据库",
    "connection_type": "postgresql",
    "connection_config": {
      "host": "localhost",
      "port": 5432,
      "database": "complaints",
      "username": "user",
      "password": "password"
    }
  }'
```

## 🔐 安全最佳实践

### 1. 令牌管理

- 定期刷新访问令牌
- 安全存储令牌，避免在客户端代码中硬编码
- 使用 HTTPS 传输敏感数据

### 2. 请求限制

API 实施了请求频率限制：
- 每分钟最多 60 个请求
- 超出限制将返回 429 状态码

### 3. 数据验证

- 所有输入数据都经过严格验证
- 使用参数化查询防止 SQL 注入
- 敏感数据加密存储

## 📊 监控和调试

### 健康检查

```bash
# 基础健康检查
curl -X GET "http://localhost:8000/api/v1/health"

# 详细健康检查
curl -X GET "http://localhost:8000/api/v1/health/detailed" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 服务模块健康检查
curl -X GET "http://localhost:8000/api/v1/health/services" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 数据库健康检查
curl -X GET "http://localhost:8000/api/v1/health/database" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 版本信息

```bash
curl -X GET "http://localhost:8000/api/v1/version"
```

## 🚀 性能优化

### 1. 缓存策略

- 使用 Redis 缓存频繁查询的数据
- 智能占位符处理结果缓存
- API 响应缓存

### 2. 异步处理

- 长时间运行的任务使用后台处理
- WebSocket 实时通知任务状态
- 批量操作支持

### 3. 数据库优化

- 查询优化和索引设计
- 连接池管理
- 分页查询减少内存使用

## 📝 开发工具

### Postman 集合

我们提供了完整的 Postman 集合，包含所有 API 端点的示例请求。

### SDK 和客户端库

- Python SDK: `pip install autoreportai-sdk`
- JavaScript SDK: `npm install autoreportai-js`
- TypeScript 类型定义

### 测试环境

- 测试环境 URL: `http://test.autoreportai.com/api/v1`
- 测试账户: `test@example.com` / `testpassword`

## 🆘 支持和帮助

### 文档资源

- [API 参考文档](http://localhost:8000/api/v1/docs)
- [开发者指南](./developer-guide.md)
- [常见问题解答](./faq.md)
- [错误代码参考](./error-codes.md)

### 联系支持

- 邮箱: support@autoreportai.com
- 技术支持: tech@autoreportai.com
- GitHub Issues: https://github.com/autoreportai/issues

### 更新日志

查看 [CHANGELOG.md](./CHANGELOG.md) 了解最新更新和变更。

---

**最后更新**: 2024-01-01  
*