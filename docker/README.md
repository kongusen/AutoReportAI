# AutoReportAI Docker 部署

本文件夹包含 AutoReportAI 的 Docker 部署配置文件。

## 文件说明

- `docker-compose.yml` - 主要的 Docker Compose 配置文件
- `.env.template` - 环境变量配置模板
- `DEPLOYMENT.md` - 详细的部署指南文档

## 快速开始

### 1. 准备环境变量

```bash
# 复制环境变量模板
cp .env.template .env

# 编辑环境变量文件
nano .env
```

**重要**: 请务必修改以下配置项：
- `SECRET_KEY` - 应用密钥
- `ENCRYPTION_KEY` - 加密密钥  
- `POSTGRES_PASSWORD` - 数据库密码
- `OPENAI_API_KEY` - OpenAI API 密钥

### 2. 启动服务

```bash
# 从项目根目录启动
docker-compose -f docker/docker-compose.yml up -d

# 或者在 docker 目录中启动
cd docker
docker-compose up -d
```

### 3. 访问应用

- **前端应用**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

## 部署模式

### 基础模式（默认）
启动核心服务：数据库、Redis、后端API、前端、Celery Worker 和 Beat

```bash
docker-compose up -d
```

### 开发模式
包含监控服务（Flower）

```bash
docker-compose --profile dev up -d
```

### 生产模式
包含对象存储服务（MinIO）

```bash
docker-compose --profile prod up -d
```

### 监控模式
仅启动监控相关服务

```bash
docker-compose --profile monitoring up -d
```

## 常用命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 清理数据（谨慎使用）
docker-compose down -v
```

## 数据持久化

默认使用 Docker 命名卷存储数据：
- `postgres_data` - 数据库数据
- `redis_data` - Redis 数据
- `backend_logs` - 应用日志
- `backend_uploads` - 上传文件
- `backend_reports` - 报告文件
- `backend_storage` - 存储文件

## 故障排除

如果遇到问题，请查看：
1. 环境变量配置是否正确
2. 端口是否被占用
3. Docker 和 Docker Compose 版本是否兼容
4. 查看服务日志获取详细错误信息

更多详细信息请参考 `DEPLOYMENT.md` 文件。

## 安全提醒

⚠️ **生产环境部署前请务必**：
- 更改默认密码和密钥
- 配置防火墙规则
- 启用 HTTPS
- 定期备份数据
- 监控系统资源使用情况