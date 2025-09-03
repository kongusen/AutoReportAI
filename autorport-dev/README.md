# AutoReportAI 开发环境指南

## 🚀 快速开始

### 1. 基础启动 (默认包含Minio)

启动全部核心服务，包括Minio对象存储：

```bash
# 使用开发环境配置启动
docker-compose --env-file ../.env.dev up -d

# 或者指定配置文件启动
docker-compose -f docker-compose.yml up -d
```

包含的服务：
- PostgreSQL 数据库 (端口: 5432)
- Redis 缓存 (端口: 6379) 
- 后端API服务 (端口: 8000)
- 前端UI (端口: 3000)
- Celery Worker & Beat
- **Minio对象存储** (API端口: 9000, 控制台: 9001)

### 2. 开发模式启动 (dev-suffix模式)

启动包含开发工具的完整环境：

```bash
# 启动开发模式 (包含额外的Minio开发实例)
docker-compose --profile dev-mode up -d

# 查看开发模式服务状态
docker-compose --profile dev-mode ps
```

额外的开发模式服务：
- **Minio开发实例** (API端口: 9002, 控制台: 9003)
- 独立的开发存储空间
- 不同的认证凭据

### 3. 开发工具模式

启动管理工具：

```bash
# 启动数据库和Redis管理工具
docker-compose --profile tools up -d pgadmin redis-insight
```

管理工具：
- pgAdmin (端口: 5050)
- Redis Insight (端口: 8001)

## 📦 Minio对象存储配置

### 默认Minio服务

**访问信息：**
- API地址: http://localhost:9000
- Web控制台: http://localhost:9001
- 用户名: `minioadmin` 
- 密码: `minioadmin123`

**后端集成：**
```yaml
环境变量:
  MINIO_ENDPOINT: minio:9000
  MINIO_ACCESS_KEY: minioadmin
  MINIO_SECRET_KEY: minioadmin123
  MINIO_BUCKET_NAME: autoreport
  FILE_STORAGE_BACKEND: minio
```

### 开发模式Minio服务

**访问信息：**
- API地址: http://localhost:9002
- Web控制台: http://localhost:9003  
- 用户名: `devuser`
- 密码: `devpassword123`

## 🛠 常用操作命令

### 服务管理

```bash
# 查看所有服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
docker-compose logs -f minio

# 重启特定服务
docker-compose restart backend
docker-compose restart minio

# 停止所有服务
docker-compose down

# 清理数据卷 (谨慎使用)
docker-compose down -v
```

### Minio管理

```bash
# 进入Minio容器
docker exec -it autoreport-minio-dev sh

# 检查存储桶
docker exec -it autoreport-minio-dev mc ls minio/

# 创建存储桶
docker exec -it autoreport-minio-dev mc mb minio/autoreport
```

### 开发调试

```bash
# 进入后端容器
docker exec -it autoreport-backend-dev bash

# 查看后端日志
docker-compose logs -f backend

# 监控Minio连接
docker-compose logs -f backend | grep -i minio

# 测试Minio连接
curl -v http://localhost:9000/minio/health/live
```

## 🔧 配置文件

### 环境变量文件

- `.env.dev` - 开发环境配置
- `docker-compose.yml` - 服务编排配置

### 关键配置项

```bash
# Minio配置
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
MINIO_BUCKET_NAME=autoreport

# 开发模式Minio
MINIO_DEV_ROOT_USER=devuser  
MINIO_DEV_ROOT_PASSWORD=devpassword123

# 后端存储配置
FILE_STORAGE_BACKEND=minio
FILE_UPLOAD_MAX_SIZE=50MB
```

## 🚨 故障排除

### Minio连接问题

```bash
# 检查Minio服务状态
docker-compose ps minio

# 检查Minio健康状态
curl http://localhost:9000/minio/health/live

# 重启Minio服务
docker-compose restart minio
```

### 权限问题

```bash
# 检查数据卷权限
docker exec -it autoreport-minio-dev ls -la /data

# 修复权限 (如果需要)
docker exec -it autoreport-minio-dev chown -R minio:minio /data
```

### 端口冲突

检查端口占用：
```bash
lsof -i :9000  # Minio API
lsof -i :9001  # Minio Console
lsof -i :9002  # Minio Dev API
lsof -i :9003  # Minio Dev Console
```

## 📊 服务依赖关系

```
PostgreSQL (db) ←─── Backend ←─── Frontend
     ↑                ↓
   Redis ←──────── Celery Worker/Beat
     ↑                ↓  
   Minio ←─────── File Storage
```

## 🔍 监控和日志

### 健康检查

```bash
# 检查所有服务健康状态
docker-compose ps

# API健康检查
curl http://localhost:8000/api/v1/health

# Minio健康检查  
curl http://localhost:9000/minio/health/live
```

### 日志监控

```bash
# 实时查看后端日志
docker-compose logs -f backend

# 查看Minio访问日志
docker-compose logs -f minio

# 搜索特定日志
docker-compose logs backend | grep -i error
```

## 🎯 开发工作流

1. **启动开发环境**:
   ```bash
   docker-compose --env-file ../.env.dev up -d
   ```

2. **检查服务状态**:
   ```bash
   docker-compose ps
   ```

3. **访问服务**:
   - 前端: http://localhost:3000
   - 后端API: http://localhost:8000/docs
   - Minio控制台: http://localhost:9001

4. **开发调试**:
   - 修改代码会自动重载
   - 查看日志进行调试
   - 使用Minio控制台管理文件

5. **停止服务**:
   ```bash
   docker-compose down
   ```

---

**注意**: 所有配置都针对开发环境优化，生产环境请使用不同的配置和凭据。