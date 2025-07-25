# 后端 API 接口及数据格式

## AI 服务
- GET /ai-providers
  - 参数：provider_type, is_active, skip, limit
  - 响应：List[AIProviderResponse]
  - 字段示例：id, name, provider_type, model_name, is_active, config, created_at
- POST /ai-providers
  - 请求体：AIProviderCreate
  - 响应：APIResponse[AIProvider]

## 模板管理
- GET /templates
  - 参数：skip, limit, include_public
  - 响应：APIResponse[List[Template]]
  - 字段示例：id, name, description, template_type, is_public, created_at, updated_at, user_id, file_size, placeholder_count
- POST /templates
  - 请求体：TemplateCreate
  - 响应：APIResponse[Template]

## 数据源管理
- GET /data-sources
  - 参数：skip, limit, type, status
  - 响应：List[DataSourceResponse]
  - 字段示例：id, name, type, status, config, created_at, updated_at
- POST /data-sources
  - 请求体：DataSourceCreate
  - 响应：APIResponse[DataSource]
- GET /data-sources/{source_id}
  - 响应：APIResponse[DataSource]

## 用户认证
- POST /auth/login
  - 请求体：{ username: string, password: string }
  - 响应：{ access_token: string, token_type: string, expires_in: number }
- POST /auth/register
  - 请求体：{ username: string, email: string, password: string, full_name?: string, terms_accepted: boolean }
  - 响应：{ id, username, email, full_name, is_active, is_superuser, created_at }

## 用户配置
- GET /user-profile/me
  - 响应：{ username, email, full_name, bio, ... }
- PATCH /user-profile/me
  - 请求体：{ username, email, full_name, bio, ... }
  - 响应：同上
- GET /user-profile/notifications
  - 响应：{ email_notifications, report_completion, error_alerts, weekly_summary }
- PATCH /user-profile/notifications
  - 请求体：{ email_notifications, report_completion, error_alerts, weekly_summary }
  - 响应：同上
- 其它如 /user-profile/preferences, /user-profile/email, /user-profile/ai-provider, /user-profile/security

## 任务详情
- GET /tasks/{id}
  - 响应：{ id, name, description, is_active, template: { id, name, description }, data_source: { id, name, type }, schedule_type, schedule_config, created_at, updated_at, last_run?, next_run?, userId }
- PATCH /tasks/{id}
  - 请求体：同上
  - 响应：同上
- DELETE /tasks/{id}
  - 响应：{ success: boolean, message: string }

## 任务管理
- GET /tasks
  - 参数：skip, limit
  - 响应：List[TaskRead]
  - 字段示例：id, name, ...

## 其它接口
- 可根据 endpoints/*.py 路由补充 