# AutoReportAI 开发环境指南

## 🚀 快速开始

### 多架构镜像构建

AutoReportAI 支持多架构 Docker 镜像构建，可以同时构建 `amd64` 和 `arm64` 架构的镜像并推送到 Docker Hub。

#### 构建脚本使用

```bash
# 设置 Docker Hub 用户名
export DOCKER_HUB_USERNAME=你的dockerhub用户名

# 构建并推送所有服务的多架构镜像
./build-and-push.sh

# 构建特定服务
./build-and-push.sh backend frontend

# 本地构建（不推送）
./build-and-push.sh --no-push --platforms linux/amd64

# 查看帮助
./build-and-push.sh --help
```

详细使用说明请参考 [多架构镜像构建](#-多架构镜像构建) 章节。

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

## 🐳 多架构镜像构建

AutoReportAI 提供了完整的多架构 Docker 镜像构建解决方案，支持 `linux/amd64` 和 `linux/arm64` 平台。

### 构建脚本特性

- ✅ 支持多架构构建 (amd64/arm64)
- ✅ 自动推送到 Docker Hub
- ✅ 多阶段构建优化
- ✅ 智能缓存管理
- ✅ 健康检查配置
- ✅ 安全标签管理

### 快速开始

1. **设置 Docker Hub 用户名**
   ```bash
   export DOCKER_HUB_USERNAME=你的dockerhub用户名
   ```

2. **构建并推送所有镜像**
   ```bash
   ./build-and-push.sh
   ```

### 命令选项

```bash
./build-and-push.sh [选项] [服务名...]
```

**选项:**
- `-u, --username USER`: 设置 Docker Hub 用户名
- `-v, --version VERSION`: 设置镜像版本标签 (默认: latest)
- `-p, --platforms PLAT`: 设置目标平台 (默认: linux/amd64,linux/arm64)
- `--no-push`: 只构建本地镜像，不推送到注册表
- `--cleanup`: 构建后清理缓存
- `-h, --help`: 显示帮助信息

**支持的服务:**
- `backend`: 后端 API 服务镜像
- `frontend`: 前端 UI 服务镜像  
- `all`: 构建所有服务镜像 (默认)

### 使用示例

#### 基础用法
```bash
# 构建所有服务并推送到 Docker Hub
DOCKER_HUB_USERNAME=myuser ./build-and-push.sh

# 指定版本标签
./build-and-push.sh --username myuser --version v1.0.0

# 构建特定服务
./build-and-push.sh --username myuser backend
```

#### 本地构建
```bash
# 多架构构建（缓存模式，不推送）
./build-and-push.sh --username myuser --no-push

# 单架构本地构建并加载
./build-and-push.sh --username myuser --no-push --platforms linux/amd64
```

#### 维护操作
```bash
# 构建后清理缓存
./build-and-push.sh --username myuser --cleanup

# 只清理构建器缓存
docker buildx prune --builder autoreportai-builder --force
```

### 环境变量

可以通过环境变量设置构建参数：

```bash
export DOCKER_HUB_USERNAME=myuser
export VERSION=v1.0.0
export PUSH_TO_REGISTRY=true
./build-and-push.sh
```

### 镜像标签

构建的镜像会被标记为：
- `用户名/autoreportai-服务名:版本号`
- `用户名/autoreportai-服务名:latest`

示例：
```
myuser/autoreportai-backend:v1.0.0
myuser/autoreportai-backend:latest
myuser/autoreportai-frontend:v1.0.0
myuser/autoreportai-frontend:latest
```

### 在生产环境中使用

构建并推送镜像后，可以在生产环境的 `docker-compose.yml` 中使用：

```yaml
version: '3.8'

services:
  backend:
    image: myuser/autoreportai-backend:v1.0.0
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/autoreport
      - REDIS_URL=redis://redis:6379/0
    # ... 其他配置

  frontend:
    image: myuser/autoreportai-frontend:v1.0.0
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
      - NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
    # ... 其他配置
```

### 架构支持

脚本默认构建以下架构：
- `linux/amd64` - Intel/AMD 64位处理器
- `linux/arm64` - ARM 64位处理器 (Apple Silicon, ARM服务器)

可以通过 `--platforms` 参数自定义：
```bash
# 只构建 ARM64
./build-and-push.sh --platforms linux/arm64

# 添加更多架构
./build-and-push.sh --platforms linux/amd64,linux/arm64,linux/arm/v7
```

### 故障排除

#### Docker Buildx 问题
```bash
# 重新创建构建器
docker buildx rm autoreportai-builder
docker buildx create --name autoreportai-builder --use
```

#### 多架构构建无法加载到本地
多架构镜像无法直接加载到本地 Docker，有以下选择：

1. **推送到注册表**（推荐）
   ```bash
   ./build-and-push.sh --username myuser
   ```

2. **单架构本地构建**
   ```bash
   ./build-and-push.sh --username myuser --no-push --platforms linux/amd64
   ```

#### 内存不足
```bash
# 单独构建服务
./build-and-push.sh --username myuser backend
./build-and-push.sh --username myuser frontend

# 增加 Docker Desktop 内存限制
# 在 Docker Desktop 设置中调整内存分配
```

#### 网络问题
```bash
# 检查网络连接
docker buildx build --help

# 清理网络缓存
docker system prune -a
```

### 镜像优化特性

#### 后端镜像
- 基于 `python:3.11-slim`
- 多阶段构建减少镜像大小
- 包含中文字体支持
- 非 root 用户运行
- 支持生产、开发、Worker、Beat 多种模式

#### 前端镜像
- 基于 `node:18-alpine` 
- Next.js 14 + TypeScript 优化
- 支持 React Agent UI
- 开发/生产环境分离
- 静态文件优化

### 监控和维护

#### 查看构建历史
```bash
# 查看构建器状态
docker buildx ls

# 查看缓存使用情况
docker system df

# 清理构建缓存
docker buildx prune --all
```

#### 镜像大小优化
脚本自动应用以下优化：
- 多阶段构建
- 依赖缓存层
- 非必要文件清理
- 压缩层合并

---

**注意**: 所有配置都针对开发环境优化，生产环境请使用不同的配置和凭据。