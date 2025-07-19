# API 错误代码参考

## 📋 概述

本文档列出了 AutoReportAI API 中所有可能的错误代码、描述和解决方案。

## 🔐 认证错误 (AUTH_*)

### AUTH_001 - INVALID_CREDENTIALS
**描述**: 用户名或密码错误  
**HTTP状态码**: 401  
**解决方案**: 检查用户名和密码是否正确

```json
{
  "success": false,
  "message": "用户名或密码错误",
  "error": {
    "code": "AUTH_001",
    "details": {
      "username": "提供的用户名"
    }
  }
}
```

### AUTH_002 - TOKEN_EXPIRED
**描述**: 访问令牌已过期  
**HTTP状态码**: 401  
**解决方案**: 重新登录获取新的访问令牌

```json
{
  "success": false,
  "message": "访问令牌已过期",
  "error": {
    "code": "AUTH_002",
    "details": {
      "expired_at": "2024-01-01T12:00:00Z"
    }
  }
}
```

### AUTH_003 - TOKEN_INVALID
**描述**: 访问令牌无效或格式错误  
**HTTP状态码**: 401  
**解决方案**: 检查令牌格式，重新登录获取有效令牌

### AUTH_004 - TOKEN_MISSING
**描述**: 请求头中缺少访问令牌  
**HTTP状态码**: 401  
**解决方案**: 在请求头中添加 `Authorization: Bearer <token>`

### AUTH_005 - INSUFFICIENT_PERMISSIONS
**描述**: 权限不足，无法访问资源  
**HTTP状态码**: 403  
**解决方案**: 联系管理员获取相应权限

```json
{
  "success": false,
  "message": "权限不足，无法访问此资源",
  "error": {
    "code": "AUTH_005",
    "details": {
      "required_permission": "template:read",
      "user_permissions": ["template:create"]
    }
  }
}
```

## 📄 资源错误 (RESOURCE_*)

### RESOURCE_001 - NOT_FOUND
**描述**: 请求的资源不存在  
**HTTP状态码**: 404  
**解决方案**: 检查资源ID是否正确

```json
{
  "success": false,
  "message": "模板不存在",
  "error": {
    "code": "RESOURCE_001",
    "details": {
      "resource_type": "template",
      "resource_id": "123e4567-e89b-12d3-a456-426614174000"
    }
  }
}
```

### RESOURCE_002 - ALREADY_EXISTS
**描述**: 资源已存在，无法重复创建  
**HTTP状态码**: 409  
**解决方案**: 使用不同的名称或更新现有资源

```json
{
  "success": false,
  "message": "模板名称已存在",
  "error": {
    "code": "RESOURCE_002",
    "details": {
      "resource_type": "template",
      "conflicting_field": "name",
      "conflicting_value": "月度报告模板"
    }
  }
}
```

### RESOURCE_003 - ACCESS_DENIED
**描述**: 无权限访问指定资源  
**HTTP状态码**: 403  
**解决方案**: 确认资源所有权或获取访问权限

## ✅ 验证错误 (VALIDATION_*)

### VALIDATION_001 - REQUIRED_FIELD_MISSING
**描述**: 必填字段缺失  
**HTTP状态码**: 422  
**解决方案**: 提供所有必填字段

```json
{
  "success": false,
  "message": "必填字段缺失",
  "error": {
    "code": "VALIDATION_001",
    "details": {
      "missing_fields": ["name", "content"],
      "provided_fields": ["description"]
    }
  }
}
```

### VALIDATION_002 - INVALID_FORMAT
**描述**: 字段格式不正确  
**HTTP状态码**: 422  
**解决方案**: 检查字段格式要求

```json
{
  "success": false,
  "message": "邮箱格式不正确",
  "error": {
    "code": "VALIDATION_002",
    "details": {
      "field": "email",
      "provided_value": "invalid-email",
      "expected_format": "user@example.com"
    }
  }
}
```

### VALIDATION_003 - VALUE_OUT_OF_RANGE
**描述**: 字段值超出允许范围  
**HTTP状态码**: 422  
**解决方案**: 调整字段值到允许范围内

```json
{
  "success": false,
  "message": "分页限制超出范围",
  "error": {
    "code": "VALIDATION_003",
    "details": {
      "field": "limit",
      "provided_value": 1500,
      "min_value": 1,
      "max_value": 1000
    }
  }
}
```

### VALIDATION_004 - INVALID_FILE_TYPE
**描述**: 文件类型不支持  
**HTTP状态码**: 422  
**解决方案**: 使用支持的文件类型

```json
{
  "success": false,
  "message": "不支持的文件类型",
  "error": {
    "code": "VALIDATION_004",
    "details": {
      "provided_type": "image/png",
      "supported_types": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/pdf"]
    }
  }
}
```

### VALIDATION_005 - FILE_SIZE_EXCEEDED
**描述**: 文件大小超出限制  
**HTTP状态码**: 422  
**解决方案**: 压缩文件或使用更小的文件

```json
{
  "success": false,
  "message": "文件大小超出限制",
  "error": {
    "code": "VALIDATION_005",
    "details": {
      "file_size": 52428800,
      "max_size": 10485760,
      "max_size_human": "10MB"
    }
  }
}
```

## 🧠 智能占位符错误 (PLACEHOLDER_*)

### PLACEHOLDER_001 - PROCESSING_FAILED
**描述**: 占位符处理失败  
**HTTP状态码**: 500  
**解决方案**: 检查占位符格式，重试请求

```json
{
  "success": false,
  "message": "占位符处理失败",
  "error": {
    "code": "PLACEHOLDER_001",
    "details": {
      "placeholder": "{{统计:投诉总数}}",
      "error_reason": "无法解析占位符类型",
      "position": 5
    }
  }
}
```

### PLACEHOLDER_002 - FIELD_MATCHING_FAILED
**描述**: 字段匹配失败  
**HTTP状态码**: 422  
**解决方案**: 检查数据源字段或调整占位符描述

```json
{
  "success": false,
  "message": "字段匹配失败",
  "error": {
    "code": "PLACEHOLDER_002",
    "details": {
      "placeholder": "{{统计:投诉总数}}",
      "data_source_id": 1,
      "available_fields": ["complaint_id", "complaint_date", "status"],
      "match_confidence": 0.3
    }
  }
}
```

### PLACEHOLDER_003 - UNSUPPORTED_TYPE
**描述**: 不支持的占位符类型  
**HTTP状态码**: 422  
**解决方案**: 使用支持的占位符类型

```json
{
  "success": false,
  "message": "不支持的占位符类型",
  "error": {
    "code": "PLACEHOLDER_003",
    "details": {
      "provided_type": "未知类型",
      "supported_types": ["统计", "区域", "周期", "图表"]
    }
  }
}
```

### PLACEHOLDER_004 - LLM_SERVICE_UNAVAILABLE
**描述**: LLM服务不可用  
**HTTP状态码**: 503  
**解决方案**: 稍后重试或联系技术支持

```json
{
  "success": false,
  "message": "LLM服务暂时不可用",
  "error": {
    "code": "PLACEHOLDER_004",
    "details": {
      "llm_provider": "openai",
      "retry_after": 30
    }
  }
}
```

## 🗄️ 数据源错误 (DATASOURCE_*)

### DATASOURCE_001 - CONNECTION_FAILED
**描述**: 数据源连接失败  
**HTTP状态码**: 422  
**解决方案**: 检查连接配置和网络连通性

```json
{
  "success": false,
  "message": "数据源连接失败",
  "error": {
    "code": "DATASOURCE_001",
    "details": {
      "data_source_id": 1,
      "connection_type": "postgresql",
      "error_message": "连接超时",
      "host": "localhost",
      "port": 5432
    }
  }
}
```

### DATASOURCE_002 - QUERY_EXECUTION_FAILED
**描述**: 查询执行失败  
**HTTP状态码**: 500  
**解决方案**: 检查SQL语法或数据库权限

```json
{
  "success": false,
  "message": "查询执行失败",
  "error": {
    "code": "DATASOURCE_002",
    "details": {
      "data_source_id": 1,
      "query": "SELECT COUNT(*) FROM complaints",
      "error_message": "表 'complaints' 不存在"
    }
  }
}
```

### DATASOURCE_003 - INSUFFICIENT_PERMISSIONS
**描述**: 数据库权限不足  
**HTTP状态码**: 403  
**解决方案**: 检查数据库用户权限

## 📊 报告生成错误 (REPORT_*)

### REPORT_001 - GENERATION_FAILED
**描述**: 报告生成失败  
**HTTP状态码**: 500  
**解决方案**: 检查模板和数据源，重试生成

```json
{
  "success": false,
  "message": "报告生成失败",
  "error": {
    "code": "REPORT_001",
    "details": {
      "template_id": "123e4567-e89b-12d3-a456-426614174000",
      "data_source_id": 1,
      "error_stage": "content_generation",
      "error_message": "占位符处理失败"
    }
  }
}
```

### REPORT_002 - TEMPLATE_PROCESSING_ERROR
**描述**: 模板处理错误  
**HTTP状态码**: 422  
**解决方案**: 检查模板格式和占位符语法

### REPORT_003 - OUTPUT_FORMAT_UNSUPPORTED
**描述**: 不支持的输出格式  
**HTTP状态码**: 422  
**解决方案**: 使用支持的输出格式

```json
{
  "success": false,
  "message": "不支持的输出格式",
  "error": {
    "code": "REPORT_003",
    "details": {
      "requested_format": "xlsx",
      "supported_formats": ["docx", "pdf", "html"]
    }
  }
}
```

## 🔄 任务错误 (TASK_*)

### TASK_001 - NOT_FOUND
**描述**: 任务不存在  
**HTTP状态码**: 404  
**解决方案**: 检查任务ID是否正确

### TASK_002 - EXECUTION_TIMEOUT
**描述**: 任务执行超时  
**HTTP状态码**: 408  
**解决方案**: 简化任务或增加超时时间

```json
{
  "success": false,
  "message": "任务执行超时",
  "error": {
    "code": "TASK_002",
    "details": {
      "task_id": "task_123",
      "timeout_seconds": 300,
      "elapsed_seconds": 305
    }
  }
}
```

### TASK_003 - CANCELLED
**描述**: 任务已被取消  
**HTTP状态码**: 409  
**解决方案**: 重新创建任务

## 🌐 系统错误 (SYSTEM_*)

### SYSTEM_001 - INTERNAL_ERROR
**描述**: 系统内部错误  
**HTTP状态码**: 500  
**解决方案**: 联系技术支持

```json
{
  "success": false,
  "message": "系统内部错误",
  "error": {
    "code": "SYSTEM_001",
    "details": {
      "error_id": "err_123456789",
      "timestamp": "2024-01-01T12:00:00Z"
    }
  }
}
```

### SYSTEM_002 - SERVICE_UNAVAILABLE
**描述**: 服务暂时不可用  
**HTTP状态码**: 503  
**解决方案**: 稍后重试

### SYSTEM_003 - MAINTENANCE_MODE
**描述**: 系统维护中  
**HTTP状态码**: 503  
**解决方案**: 等待维护完成

```json
{
  "success": false,
  "message": "系统正在维护中",
  "error": {
    "code": "SYSTEM_003",
    "details": {
      "maintenance_start": "2024-01-01T02:00:00Z",
      "estimated_end": "2024-01-01T04:00:00Z"
    }
  }
}
```

## 🚦 限流错误 (RATE_LIMIT_*)

### RATE_LIMIT_001 - EXCEEDED
**描述**: 请求频率超出限制  
**HTTP状态码**: 429  
**解决方案**: 降低请求频率，等待限制重置

```json
{
  "success": false,
  "message": "请求频率超出限制",
  "error": {
    "code": "RATE_LIMIT_001",
    "details": {
      "limit": 60,
      "window": "1分钟",
      "reset_at": "2024-01-01T12:01:00Z",
      "retry_after": 30
    }
  }
}
```

## 📧 通知错误 (NOTIFICATION_*)

### NOTIFICATION_001 - EMAIL_SEND_FAILED
**描述**: 邮件发送失败  
**HTTP状态码**: 500  
**解决方案**: 检查邮件配置或稍后重试

```json
{
  "success": false,
  "message": "邮件发送失败",
  "error": {
    "code": "NOTIFICATION_001",
    "details": {
      "recipients": ["user@example.com"],
      "error_message": "SMTP服务器连接失败"
    }
  }
}
```

### NOTIFICATION_002 - INVALID_EMAIL_ADDRESS
**描述**: 邮箱地址无效  
**HTTP状态码**: 422  
**解决方案**: 提供有效的邮箱地址

## 🔧 故障排除指南

### 常见问题解决步骤

1. **认证问题**
   - 检查令牌是否过期
   - 确认请求头格式正确
   - 重新登录获取新令牌

2. **验证错误**
   - 检查必填字段
   - 验证数据格式
   - 确认值在允许范围内

3. **资源不存在**
   - 确认资源ID正确
   - 检查资源是否已被删除
   - 验证访问权限

4. **服务不可用**
   - 检查网络连接
   - 查看系统状态页面
   - 稍后重试请求

5. **性能问题**
   - 减少请求频率
   - 使用分页查询
   - 启用缓存

### 联系支持

如果遇到无法解决的问题：

- **技术支持邮箱**: tech@autoreportai.com
- **GitHub Issues**: https://github.com/autoreportai/issues
- **文档反馈**: docs@autoreportai.com

### 错误报告模板

```
错误代码: [ERROR_CODE]
HTTP状态码: [STATUS_CODE]
请求URL: [REQUEST_URL]
请求方法: [HTTP_METHOD]
时间戳: [TIMESTAMP]
用户ID: [USER_ID]
错误详情: [ERROR_DETAILS]
重现步骤: [REPRODUCTION_STEPS]
```

---

**最后更新**: 2024-01-01  
**文档版本**: v1.0.0