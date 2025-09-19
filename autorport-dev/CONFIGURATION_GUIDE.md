# AutoReportAI 配置指南
## DDD v2.0 架构版本

### 📋 配置文件更新说明

本目录中的配置文件已更新以匹配新的**DDD v2.0架构**。主要更新包括：

### 🔄 主要变更

#### 1. 架构标签更新
- **原**: `architecture=react_agent` 
- **新**: `architecture=ddd_v2`

#### 2. Agent系统重新定位
Agent系统现在正确位于**基础设施层**，作为技术服务：

```yaml
# 新的Agent配置
- AGENT_ENGINE=new
- NEW_AGENT_MODE=local_stub
- NEW_AGENT_TIMEOUT=60
- NEW_AGENT_MAX_CONCURRENCY=10
- NEW_AGENT_MAX_RETRIES=3
- AGENT_SYSTEM_ENABLED=true
```

#### 3. DDD架构服务配置
添加了DDD架构层级配置：

```yaml
# DDD架构服务配置
- DDD_ARCHITECTURE_ENABLED=true
- APPLICATION_SERVICE_LAYER=enabled
- DOMAIN_SERVICE_LAYER=enabled
- INFRASTRUCTURE_SERVICE_LAYER=enabled
- UNIFIED_API_RESPONSE=enabled
- TRANSACTIONAL_APPLICATION_SERVICE=enabled
```

#### 4. 前端配置更新
```yaml
# DDD架构 UI 特定配置
- NEXT_PUBLIC_DDD_ARCHITECTURE=enabled
- NEXT_PUBLIC_UNIFIED_API=enabled
- NEXT_PUBLIC_TYPE_SAFE_API=enabled
```

### 📁 配置文件说明

#### `docker-compose.yml`
主要的Docker Compose配置文件，包含：
- PostgreSQL数据库服务
- Redis缓存服务
- 后端API服务 (DDD v2.0架构)
- Celery Worker和Beat服务
- 前端服务
- MinIO对象存储服务

#### `.env.example`
环境变量模板文件，包含：
- 基础环境配置
- DDD架构配置
- Agent系统配置
- LLM服务配置
- 数据库和缓存配置

#### `.env.template`
简化的环境变量模板，用于快速部署

### 🚀 使用方法

#### 1. 初始化环境变量
```bash
# 复制环境变量模板
cp .env.example .env

# 或使用简化模板
cp .env.template .env
```

#### 2. 配置必要的环境变量
编辑 `.env` 文件，至少配置：
- `OPENAI_API_KEY` (如果使用OpenAI服务)
- `SERVER_IP` (如果需要局域网访问)
- 数据库密码等安全配置

#### 3. 启动服务
```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
```

### 🔧 DDD架构特性

#### 应用层 (Application Layer)
- 事务性应用服务
- 工作流编排
- 跨领域协调

#### 领域层 (Domain Layer)
- 纯业务逻辑
- 领域服务
- 业务规则验证

#### 基础设施层 (Infrastructure Layer)
- Agent系统 (技术服务)
- LLM集成
- 缓存系统
- 存储服务

#### API层
- 统一响应格式
- 类型安全的API
- 异常处理

### 📊 监控和调试

#### 健康检查端点
- 后端API: `http://localhost:8000/api/v1/health`
- 前端: `http://localhost:3000/api/health`
- MinIO: `http://localhost:9000/minio/health/live`

#### 日志查看
```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs backend
docker-compose logs celery-worker
```

#### 性能监控
启用了以下监控功能：
- `ENABLE_PERFORMANCE_MONITORING=true`
- `ENABLE_MONITORING=true`
- `DDD_METRICS_ENABLED=true`

### 🛡️ 安全配置

#### 生产环境部署前必须更改：
1. **SECRET_KEY**: 更改默认密钥
2. **数据库密码**: 使用强密码
3. **MinIO密钥**: 更改默认访问密钥
4. **ENCRYPTION_KEY**: 生成新的加密密钥
5. **CORS设置**: 配置合适的跨域设置

#### 推荐的生产环境配置：
```bash
# 生成新的密钥
SECRET_KEY=$(openssl rand -base64 32)
ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# 强密码
POSTGRES_PASSWORD=$(openssl rand -base64 16)
MINIO_ROOT_PASSWORD=$(openssl rand -base64 16)
```

### 🔗 相关文档

- [项目README](../README.md)
- [服务架构Wiki](../docs/SERVICE_ARCHITECTURE_WIKI.md)
- [数据流程图](../docs/data_flow_diagram.md)

### 🆘 故障排除

#### 常见问题：

1. **端口冲突**
   ```bash
   # 检查端口占用
   lsof -i :8000
   lsof -i :3000
   lsof -i :5432
   ```

2. **权限问题**
   ```bash
   # 确保数据目录权限
   sudo chown -R $USER:$USER ./data
   ```

3. **Agent系统问题**
   - 检查 `AGENT_ENGINE=new` 配置
   - 验证 `NEW_AGENT_MODE=local_stub` 设置
   - 查看Agent相关日志

4. **DDD架构验证**
   ```bash
   # 验证DDD组件
   docker-compose exec backend python -c "
   from app.services.application.base_application_service import BaseApplicationService
   from app.services.domain.placeholder.services.placeholder_analysis_domain_service import PlaceholderAnalysisDomainService
   print('DDD架构组件正常')
   "
   ```

### 📝 版本信息

- **配置版本**: DDD v2.0
- **Docker Compose版本**: 3.8+
- **架构**: 领域驱动设计 (Domain-Driven Design)
- **更新日期**: 2024年9月

---

如有问题，请查看项目文档或创建Issue反馈。