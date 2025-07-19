# API 端点详细文档

## 📋 目录

- [认证端点](#认证端点)
- [用户管理](#用户管理)
- [模板管理](#模板管理)
- [智能占位符](#智能占位符)
- [数据源管理](#数据源管理)
- [报告生成](#报告生成)
- [系统监控](#系统监控)

## 🔐 认证端点

### POST /api/v1/auth/login

用户登录获取访问令牌。

**请求体**:
```json
{
  "username": "string",
  "password": "string"
}
```

**响应**:
```json
{
  "success": true,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800,
    "user": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "username": "john_doe",
      "email": "john@example.com",
      "full_name": "John Doe",
      "is_active": true
    }
  }
}
```

**错误响应**:
```json
{
  "success": false,
  "message": "用户名或密码错误",
  "error": {
    "code": "INVALID_CREDENTIALS",
    "details": {}
  }
}
```

**cURL 示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "secure_password"
  }'
```

---

## 👥 用户管理

### GET /api/v1/users/me

获取当前用户信息。

**请求头**:
```
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "success": true,
  "message": "用户信息获取成功",
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "john_doe",
    "email": "john@example.com",
    "full_name": "John Doe",
    "is_active": true,
    "created_at": "2024-01-01T10:00:00Z",
    "last_login": "2024-01-01T12:00:00Z",
    "preferences": {
      "language": "zh-CN",
      "timezone": "Asia/Shanghai"
    }
  }
}
```

**cURL 示例**:
```bash
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 📄 模板管理

### GET /api/v1/templates

获取模板列表。

**查询参数**:
- `skip` (int, 可选): 跳过的记录数，默认 0
- `limit` (int, 可选): 返回的记录数，默认 100
- `include_public` (bool, 可选): 是否包含公共模板，默认 true
- `name` (string, 可选): 按名称过滤
- `template_type` (string, 可选): 按类型过滤

**响应**:
```json
{
  "success": true,
  "message": "模板列表获取成功",
  "data": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "name": "月度投诉分析报告",
      "description": "月度投诉数据分析报告模板",
      "template_type": "docx",
      "is_public": false,
      "created_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-01T11:00:00Z",
      "user_id": "user123",
      "file_size": 2048,
      "placeholder_count": 5
    }
  ],
  "pagination": {
    "total": 25,
    "skip": 0,
    "limit": 100,
    "has_more": false
  }
}
```

**cURL 示例**:
```bash
curl -X GET "http://localhost:8000/api/v1/templates?skip=0&limit=20&include_public=true" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### POST /api/v1/templates

创建新模板。

**请求体**:
```json
{
  "name": "月度投诉分析报告",
  "description": "月度投诉数据分析报告模板",
  "content": "本月共收到{{统计:投诉总数}}件投诉，其中{{区域:主要投诉地区}}占比最高。",
  "template_type": "docx",
  "is_public": false,
  "tags": ["投诉", "月报", "分析"]
}
```

**响应**:
```json
{
  "success": true,
  "message": "模板创建成功",
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "月度投诉分析报告",
    "description": "月度投诉数据分析报告模板",
    "content": "本月共收到{{统计:投诉总数}}件投诉，其中{{区域:主要投诉地区}}占比最高。",
    "template_type": "docx",
    "is_public": false,
    "created_at": "2024-01-01T10:00:00Z",
    "user_id": "user123",
    "file_size": 256,
    "placeholder_count": 2
  }
}
```

### POST /api/v1/templates/upload

上传模板文件。

**请求体** (multipart/form-data):
- `file`: 模板文件
- `name`: 模板名称
- `description`: 模板描述
- `is_public`: 是否公开 (可选，默认 false)

**响应**:
```json
{
  "success": true,
  "message": "模板上传成功",
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "投诉分析模板",
    "description": "投诉数据分析报告模板",
    "template_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "original_filename": "template.docx",
    "file_size": 15360,
    "is_public": false,
    "created_at": "2024-01-01T10:00:00Z"
  }
}
```

**cURL 示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/templates/upload" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@template.docx" \
  -F "name=投诉分析模板" \
  -F "description=投诉数据分析报告模板" \
  -F "is_public=false"
```

### GET /api/v1/templates/{template_id}

获取特定模板详情。

**路径参数**:
- `template_id` (UUID): 模板ID

**响应**:
```json
{
  "success": true,
  "message": "模板获取成功",
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "月度投诉分析报告",
    "description": "月度投诉数据分析报告模板",
    "content": "本月共收到{{统计:投诉总数}}件投诉...",
    "template_type": "docx",
    "is_public": false,
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T11:00:00Z",
    "user_id": "user123",
    "file_size": 2048,
    "placeholder_count": 5,
    "placeholders": [
      {
        "text": "{{统计:投诉总数}}",
        "type": "统计",
        "position": 5
      }
    ]
  }
}
```

### PUT /api/v1/templates/{template_id}

更新模板。

**请求体**:
```json
{
  "name": "更新后的模板名称",
  "description": "更新后的描述",
  "content": "更新后的内容",
  "is_public": true
}
```

### DELETE /api/v1/templates/{template_id}

删除模板。

**响应**:
```json
{
  "success": true,
  "message": "模板删除成功",
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "deleted_at": "2024-01-01T12:00:00Z"
  }
}
```

---

## 🧠 智能占位符

### POST /api/v1/intelligent-placeholders/analyze

分析模板中的占位符。

**请求体**:
```json
{
  "template_content": "本月{{统计:投诉总数}}件投诉中，{{区域:主要投诉地区}}占比最高。",
  "template_id": "123e4567-e89b-12d3-a456-426614174000",
  "data_source_id": 1,
  "analysis_options": {
    "include_context": true,
    "confidence_threshold": 0.7,
    "context_window": 50
  }
}
```

**响应**:
```json
{
  "success": true,
  "placeholders": [
    {
      "placeholder_text": "{{统计:投诉总数}}",
      "placeholder_type": "统计",
      "description": "投诉总数",
      "position": 2,
      "context_before": "本月",
      "context_after": "件投诉中",
      "confidence": 0.95
    },
    {
      "placeholder_text": "{{区域:主要投诉地区}}",
      "placeholder_type": "区域",
      "description": "主要投诉地区",
      "position": 15,
      "context_before": "投诉中，",
      "context_after": "占比最高",
      "confidence": 0.88
    }
  ],
  "total_count": 2,
  "type_distribution": {
    "统计": 1,
    "区域": 1
  },
  "validation_result": {
    "is_valid": true,
    "warnings": [],
    "errors": []
  },
  "processing_errors": [],
  "estimated_processing_time": 30
}
```

**cURL 示例**:
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

### POST /api/v1/intelligent-placeholders/field-matching

验证占位符的字段匹配。

**请求体**:
```json
{
  "placeholder_text": "{{统计:投诉总数}}",
  "placeholder_type": "统计",
  "description": "投诉总数",
  "data_source_id": 1,
  "context": "本月投诉总数件投诉中",
  "matching_options": {
    "confidence_threshold": 0.8,
    "max_suggestions": 5,
    "include_transformations": true,
    "semantic_matching": true
  }
}
```

**响应**:
```json
{
  "success": true,
  "placeholder_understanding": {
    "semantic_meaning": "统计投诉的总数量",
    "data_type": "integer",
    "calculation_needed": "COUNT",
    "aggregation_type": "SUM",
    "confidence": 0.92
  },
  "field_suggestions": [
    {
      "field_name": "complaint_count",
      "match_score": 0.95,
      "match_reason": "字段名称和语义高度匹配",
      "data_transformation": "COUNT(*)",
      "validation_rules": ["NOT_NULL", "POSITIVE_INTEGER"]
    },
    {
      "field_name": "total_complaints",
      "match_score": 0.88,
      "match_reason": "语义匹配，需要聚合计算",
      "data_transformation": "SUM(complaint_amount)",
      "validation_rules": ["NOT_NULL"]
    }
  ],
  "best_match": {
    "field_name": "complaint_count",
    "match_score": 0.95,
    "match_reason": "字段名称和语义高度匹配",
    "data_transformation": "COUNT(*)",
    "validation_rules": ["NOT_NULL", "POSITIVE_INTEGER"]
  },
  "confidence_score": 0.93,
  "processing_metadata": {
    "llm_provider": "openai",
    "processing_time": 1.2,
    "data_source_fields": 25
  }
}
```

### POST /api/v1/intelligent-placeholders/generate-report

使用智能占位符处理生成报告。

**请求体**:
```json
{
  "template_id": "123e4567-e89b-12d3-a456-426614174000",
  "data_source_id": 1,
  "processing_config": {
    "llm_provider": "openai",
    "llm_model": "gpt-4",
    "enable_caching": true,
    "quality_check": true,
    "auto_optimization": false
  },
  "output_config": {
    "format": "docx",
    "include_charts": true,
    "quality_report": true,
    "output_filename": "智能报告_2024-01.docx"
  },
  "email_config": {
    "recipients": ["user@example.com", "manager@example.com"],
    "subject": "智能生成报告 - 2024年1月",
    "include_summary": true,
    "send_immediately": false
  }
}
```

**响应**:
```json
{
  "success": true,
  "task_id": "task_123e4567-e89b-12d3-a456-426614174000",
  "report_id": null,
  "processing_summary": {
    "task_id": "task_123e4567-e89b-12d3-a456-426614174000",
    "template_id": "123e4567-e89b-12d3-a456-426614174000",
    "data_source_id": 1,
    "placeholder_count": 5,
    "llm_provider": "openai",
    "processing_options": {
      "llm_model": "gpt-4",
      "enable_caching": true,
      "quality_check": true
    },
    "started_at": "2024-01-01T10:00:00Z",
    "estimated_completion": "2024-01-01T10:05:00Z"
  },
  "placeholder_results": [
    {
      "placeholder": "{{统计:投诉总数}}",
      "type": "统计",
      "description": "投诉总数",
      "confidence": 0.95,
      "status": "pending"
    }
  ],
  "quality_assessment": null,
  "file_path": null,
  "email_status": null
}
```

### GET /api/v1/intelligent-placeholders/task/{task_id}/status

查询智能报告生成任务状态。

**路径参数**:
- `task_id` (string): 任务ID

**响应**:
```json
{
  "task_id": "task_123e4567-e89b-12d3-a456-426614174000",
  "status": "processing",
  "progress": 75,
  "message": "正在处理占位符 3/5",
  "started_at": "2024-01-01T10:00:00Z",
  "estimated_completion": "2024-01-01T10:05:00Z",
  "current_step": "placeholder_processing",
  "steps_completed": [
    "template_analysis",
    "field_matching",
    "data_extraction"
  ],
  "steps_remaining": [
    "content_generation",
    "quality_check"
  ],
  "result": null,
  "error": null
}
```

**任务状态说明**:
- `pending`: 任务已创建，等待处理
- `processing`: 任务正在处理中
- `completed`: 任务已完成
- `failed`: 任务失败
- `cancelled`: 任务已取消

### GET /api/v1/intelligent-placeholders/statistics

获取智能占位符处理统计信息。

**响应**:
```json
{
  "understanding_statistics": {
    "total_processed": 1250,
    "success_rate": 0.94,
    "average_confidence": 0.87,
    "type_distribution": {
      "统计": 450,
      "区域": 320,
      "周期": 280,
      "图表": 200
    },
    "processing_time": {
      "average": 2.3,
      "median": 1.8,
      "p95": 5.2
    }
  },
  "system_statistics": {
    "supported_placeholder_types": ["周期", "区域", "统计", "图表"],
    "active_llm_providers": ["openai", "claude"],
    "cache_enabled": true,
    "cache_hit_rate": 0.73,
    "quality_check_enabled": true
  },
  "user_statistics": {
    "templates_processed": 45,
    "reports_generated": 23,
    "average_placeholders_per_template": 4.2
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

## 🗄️ 数据源管理

### GET /api/v1/data-sources

获取数据源列表。

**查询参数**:
- `skip` (int): 跳过记录数
- `limit` (int): 返回记录数
- `connection_type` (string): 按连接类型过滤

**响应**:
```json
{
  "success": true,
  "message": "数据源列表获取成功",
  "data": [
    {
      "id": 1,
      "name": "投诉数据库",
      "description": "投诉管理系统数据库",
      "connection_type": "postgresql",
      "is_active": true,
      "created_at": "2024-01-01T10:00:00Z",
      "last_tested": "2024-01-01T11:30:00Z",
      "test_status": "success",
      "table_count": 15,
      "total_records": 125000
    }
  ]
}
```

### POST /api/v1/data-sources

创建新数据源。

**请求体**:
```json
{
  "name": "投诉数据库",
  "description": "投诉管理系统数据库",
  "connection_type": "postgresql",
  "connection_config": {
    "host": "localhost",
    "port": 5432,
    "database": "complaints",
    "username": "db_user",
    "password": "secure_password",
    "ssl_mode": "require"
  },
  "test_connection": true
}
```

**响应**:
```json
{
  "success": true,
  "message": "数据源创建成功",
  "data": {
    "id": 1,
    "name": "投诉数据库",
    "description": "投诉管理系统数据库",
    "connection_type": "postgresql",
    "is_active": true,
    "created_at": "2024-01-01T10:00:00Z",
    "connection_test": {
      "status": "success",
      "message": "连接测试成功",
      "response_time": 0.15
    }
  }
}
```

---

## 📊 报告生成

### GET /api/v1/reports

获取报告列表。

**响应**:
```json
{
  "success": true,
  "message": "报告列表获取成功",
  "data": [
    {
      "id": "report_123e4567-e89b-12d3-a456-426614174000",
      "name": "2024年1月投诉分析报告",
      "template_id": "123e4567-e89b-12d3-a456-426614174000",
      "data_source_id": 1,
      "status": "completed",
      "created_at": "2024-01-01T10:00:00Z",
      "completed_at": "2024-01-01T10:05:00Z",
      "file_path": "/reports/2024-01-complaint-analysis.docx",
      "file_size": 2048000,
      "quality_score": 0.92
    }
  ]
}
```

### GET /api/v1/reports/{report_id}

获取特定报告详情。

**响应**:
```json
{
  "success": true,
  "message": "报告详情获取成功",
  "data": {
    "id": "report_123e4567-e89b-12d3-a456-426614174000",
    "name": "2024年1月投诉分析报告",
    "template_id": "123e4567-e89b-12d3-a456-426614174000",
    "data_source_id": 1,
    "status": "completed",
    "created_at": "2024-01-01T10:00:00Z",
    "completed_at": "2024-01-01T10:05:00Z",
    "processing_time": 300,
    "file_path": "/reports/2024-01-complaint-analysis.docx",
    "file_size": 2048000,
    "quality_score": 0.92,
    "placeholder_results": [
      {
        "placeholder": "{{统计:投诉总数}}",
        "resolved_value": "1,234",
        "confidence": 0.95,
        "processing_time": 1.2
      }
    ],
    "quality_assessment": {
      "overall_score": 0.92,
      "content_quality": 0.94,
      "data_accuracy": 0.91,
      "formatting_quality": 0.90,
      "suggestions": [
        "建议增加图表说明",
        "部分数据可以添加趋势分析"
      ]
    }
  }
}
```

---

## 🔍 系统监控

### GET /api/v1/health

基础健康检查。

**响应**:
```json
{
  "status": "healthy",
  "version": "v1",
  "timestamp": "2024-01-01T12:00:00Z",
  "message": "API is operational"
}
```

### GET /api/v1/health/detailed

详细健康检查。

**响应**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "services": {
    "database": {
      "status": "healthy",
      "response_time": 0.05,
      "connection_pool": {
        "active": 5,
        "idle": 10,
        "max": 20
      }
    },
    "redis": {
      "status": "healthy",
      "response_time": 0.02,
      "memory_usage": "45MB",
      "connected_clients": 3
    },
    "llm_services": {
      "openai": {
        "status": "healthy",
        "response_time": 1.2,
        "rate_limit_remaining": 4500
      }
    }
  },
  "system_metrics": {
    "cpu_usage": 0.25,
    "memory_usage": 0.68,
    "disk_usage": 0.45
  }
}
```

### GET /api/v1/health/services

服务模块健康检查。

**响应**:
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "overall_status": "healthy",
  "services": {
    "intelligent_placeholder": {
      "status": "healthy",
      "message": "intelligent_placeholder service is available"
    },
    "report_generation": {
      "status": "healthy",
      "message": "report_generation service is available"
    },
    "data_processing": {
      "status": "healthy",
      "message": "data_processing service is available"
    },
    "ai_integration": {
      "status": "healthy",
      "message": "ai_integration service is available"
    },
    "notification": {
      "status": "healthy",
      "message": "notification service is available"
    }
  }
}
```

### GET /api/v1/health/database

数据库连接健康检查。

**响应**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "database": {
    "connection": "successful",
    "basic_query": "successful",
    "user_count": 150,
    "template_count": 45,
    "report_count": 230
  },
  "message": "Database is operational"
}
```

### GET /api/v1/version

获取API版本信息。

**响应**:
```json
{
  "version": "v1",
  "status": "active",
  "supported_versions": ["v1"],
  "current_version": "v1",
  "build_info": {
    "build_time": "2024-01-01T08:00:00Z",
    "commit_hash": "abc123def456",
    "environment": "production"
  }
}
```

---

## 📝 通用响应格式

### 成功响应

所有成功的API响应都遵循以下格式：

```json
{
  "success": true,
  "message": "操作成功描述",
  "data": {
    // 实际数据内容
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 错误响应

所有错误响应都遵循以下格式：

```json
{
  "success": false,
  "message": "错误描述",
  "error": {
    "code": "ERROR_CODE",
    "details": {
      // 错误详细信息
    }
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 分页响应

包含分页信息的响应格式：

```json
{
  "success": true,
  "message": "数据获取成功",
  "data": [
    // 数据项列表
  ],
  "pagination": {
    "total": 100,
    "skip": 0,
    "limit": 20,
    "has_more": true,
    "current_page": 1,
    "total_pages": 5
  }
}
```

---

**最后更新**: 2024-01-01  
**文档版本**: v1.0.0