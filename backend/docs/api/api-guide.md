# AutoReportAI API API使用指南

## 📋 目录

- [概述](#概述)
- [基础信息](#基础信息)
- [快速开始](#快速开始)
- [认证与安全](#认证与安全)
- [API端点详情](#api端点详情)
- [错误处理](#错误处理)
- [最佳实践](#最佳实践)
- [SDK和工具](#sdk和工具)
- [支持与帮助](#支持与帮助)

## 概述


        ## AutoReportAI 智能报告生成系统API

        这是一个基于AI的智能报告生成系统，提供以下核心功能：
        
        ### 🔐 认证与授权
        * 用户注册、登录、密码重置
        * JWT token认证
        * 角色权限管理
        
        ### 📊 数据源管理
        * 多种数据源连接（数据库、API、文件）
        * 数据源配置与验证
        * 数据预处理和清洗
        
        ### 🤖 AI服务集成
        * 多AI提供商支持（OpenAI、Claude、本地模型）
        * 智能数据分析
        * 自动图表生成
        
        ### 📝 报告生成
        * 模板化报告生成
        * 智能占位符匹配
        * 多格式输出支持
        
        ### 🔄 ETL任务管理
        * 数据提取、转换、加载
        * 任务调度与监控
        * 数据质量检查
        
        ## 🚀 快速开始
        
        1. 获取API访问令牌
        2. 配置数据源
        3. 创建报告模板
        4. 生成报告
        
        ## 📋 API版本
        
        当前版本：v1.0.0
        
        ## 🔗 相关链接
        
        * [GitHub仓库](https://github.com/your-org/AutoReportAI)
        * [用户指南](https://docs.autoreportai.com)
        * [API最佳实践](https://docs.autoreportai.com/api/best-practices)
        

## 基础信息

- **API版本**: 1.0.0
- **基础URL**: `http://localhost:8000`
- **文档URL**: `http://localhost:8000/api/v1/docs` (Swagger UI)
- **ReDoc URL**: `http://localhost:8000/api/v1/redoc` (ReDoc)
- **OpenAPI规范**: `http://localhost:8000/api/v1/openapi.json`
- **认证方式**: Bearer Token (JWT)
- **数据格式**: JSON
- **字符编码**: UTF-8

## 快速开始

### 1. 获取访问令牌

所有API请求都需要有效的JWT令牌进行认证。

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

**响应示例：**
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
      "email": "john@example.com"
    }
  }
}
```

### 2. 使用访问令牌

在后续请求中包含Authorization头：

```bash
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

### 3. 基本API调用示例

**获取模板列表：**
```bash
curl -X GET "http://localhost:8000/api/v1/templates?skip=0&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**创建新模板：**
```bash
curl -X POST "http://localhost:8000/api/v1/templates" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "月度报告模板",
    "description": "月度数据分析报告",
    "content": "本月共收到{{统计:投诉总数}}件投诉",
    "template_type": "docx",
    "is_public": false
  }'
```

## 认证与安全

### JWT令牌管理

- **令牌有效期**: 30分钟（1800秒）
- **刷新机制**: 令牌过期前需要重新登录
- **存储建议**: 安全存储在内存中，避免持久化到本地存储

### 安全最佳实践

1. **HTTPS传输**: 生产环境必须使用HTTPS
2. **令牌保护**: 不要在URL参数或日志中暴露令牌
3. **权限验证**: 每个请求都会验证用户权限
4. **请求限流**: API实施了速率限制保护

### 权限模型

- **用户权限**: 只能访问自己创建的资源
- **公共资源**: 部分资源（如公共模板）所有用户可访问
- **管理员权限**: 管理员可访问所有资源

## API端点详情


## 错误处理

### HTTP状态码

API使用标准的HTTP状态码：

| 状态码 | 含义 | 说明 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未授权访问 |
| 403 | Forbidden | 权限不足 |
| 404 | Not Found | 资源未找到 |
| 422 | Unprocessable Entity | 数据验证失败 |
| 429 | Too Many Requests | 请求频率超限 |
| 500 | Internal Server Error | 服务器内部错误 |

### 统一错误响应格式

```json
{
  "success": false,
  "message": "错误描述信息",
  "error": {
    "code": "ERROR_CODE",
    "details": {
      "field": "具体错误信息"
    }
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 常见错误代码

| 错误代码 | 说明 | 解决方案 |
|----------|------|----------|
| `INVALID_CREDENTIALS` | 用户名或密码错误 | 检查登录凭据 |
| `TOKEN_EXPIRED` | 访问令牌已过期 | 重新登录获取新令牌 |
| `INSUFFICIENT_PERMISSIONS` | 权限不足 | 联系管理员获取权限 |
| `RESOURCE_NOT_FOUND` | 资源不存在 | 检查资源ID是否正确 |
| `VALIDATION_ERROR` | 数据验证失败 | 检查请求数据格式 |
| `RATE_LIMIT_EXCEEDED` | 请求频率超限 | 降低请求频率 |

## 最佳实践

### 1. 认证管理

```python
# Python示例：令牌管理
class APIClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.token = None
        self.token_expires = None
    
    def get_token(self):
        if self.token and self.token_expires > datetime.now():
            return self.token
        # 重新获取令牌
        self.login()
        return self.token
```

### 2. 错误处理

```python
# Python示例：错误处理
try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        # 令牌过期，重新登录
        self.login()
        return self.retry_request(url, headers)
    else:
        raise APIError(f"API请求失败: {e}")
```

### 3. 分页处理

```python
# Python示例：分页处理
def get_all_templates():
    all_templates = []
    skip = 0
    limit = 100
    
    while True:
        response = api_client.get(f"/templates?skip={skip}&limit={limit}")
        templates = response.get("data", [])
        
        if not templates:
            break
            
        all_templates.extend(templates)
        skip += limit
    
    return all_templates
```

### 4. 请求限流

- 每分钟最多60个请求
- 使用指数退避重试策略
- 监控响应头中的限流信息

### 5. 数据验证

```python
# Python示例：请求数据验证
from pydantic import BaseModel, ValidationError

class TemplateCreate(BaseModel):
    name: str
    description: str
    content: str
    template_type: str = "docx"
    is_public: bool = False

try:
    template_data = TemplateCreate(**request_data)
    response = api_client.post("/templates", json=template_data.dict())
except ValidationError as e:
    print(f"数据验证失败: {e}")
```

## SDK和工具

### 官方SDK

**Python SDK:**
```bash
pip install autoreportai-sdk
```

```python
from autoreportai import AutoReportClient

client = AutoReportClient(
    base_url="http://localhost:8000",
    username="your_username",
    password="your_password"
)

# 获取模板列表
templates = client.templates.list()

# 创建新模板
template = client.templates.create({
    "name": "新模板",
    "content": "模板内容"
})
```

**JavaScript/TypeScript SDK:**
```bash
npm install autoreportai-js
```

```typescript
import { AutoReportClient } from 'autoreportai-js';

const client = new AutoReportClient({
  baseUrl: 'http://localhost:8000',
  username: 'your_username',
  password: 'your_password'
});

// 获取模板列表
const templates = await client.templates.list();

// 创建新模板
const template = await client.templates.create({
  name: '新模板',
  content: '模板内容'
});
```

### 开发工具

**Postman集合:**
- 导入生成的Postman集合文件
- 包含所有API端点的示例请求
- 预配置的环境变量和认证

**OpenAPI工具:**
- Swagger UI: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`
- OpenAPI规范: `http://localhost:8000/api/v1/openapi.json`

### 测试工具

**API测试:**
```bash
# 使用httpie进行API测试
http POST localhost:8000/api/v1/auth/login username=test password=test

# 使用curl进行批量测试
curl -X GET "localhost:8000/api/v1/health" | jq .
```

## 性能优化

### 1. 缓存策略

- 使用HTTP缓存头
- 客户端缓存不变的数据
- 避免重复请求相同资源

### 2. 批量操作

```python
# 批量创建模板
templates_data = [
    {"name": "模板1", "content": "内容1"},
    {"name": "模板2", "content": "内容2"}
]

# 使用并发请求
import asyncio
import aiohttp

async def create_templates_batch(templates_data):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for template_data in templates_data:
            task = create_template(session, template_data)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results
```

### 3. 连接池管理

```python
# 使用连接池提高性能
import requests
from requests.adapters import HTTPAdapter

session = requests.Session()
adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20)
session.mount('http://', adapter)
session.mount('https://', adapter)
```

## 监控与调试

### 1. 健康检查

```bash
# 基础健康检查
curl -X GET "http://localhost:8000/api/v1/health"

# 详细健康检查
curl -X GET "http://localhost:8000/api/v1/health/detailed" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. 日志记录

```python
import logging

# 配置API客户端日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('autoreportai.client')

# 记录API请求
logger.info(f"发送API请求: {method} {url}")
logger.info(f"请求完成: {response.status_code} - {response.elapsed.total_seconds()}s")
```

### 3. 性能监控

- 监控API响应时间
- 跟踪错误率和成功率
- 设置告警阈值

## 支持与帮助

### 文档资源

- 📚 **API参考文档**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- 📖 **开发者指南**: [docs/development/](../development/)
- ❓ **常见问题**: [docs/api/faq.md](./faq.md)
- 🔧 **最佳实践**: [docs/api/best-practices.md](./best-practices.md)

### 技术支持

- 📧 **技术支持**: support@autoreportai.com
- 💬 **开发者社区**: https://community.autoreportai.com
- 🐛 **问题反馈**: https://github.com/your-org/AutoReportAI/issues
- 📞 **紧急支持**: +86-400-xxx-xxxx

### 更新通知

- 🔔 **API变更通知**: 订阅邮件列表获取API更新通知
- 📋 **变更日志**: [CHANGELOG.md](./CHANGELOG.md)
- 🚀 **新功能预览**: https://roadmap.autoreportai.com

---

**文档版本**: v1.0.0  
**最后更新**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**生成方式**: 自动生成
