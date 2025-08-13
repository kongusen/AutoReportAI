# AutoReportAI 部署指南

本文档提供了 AutoReportAI 在不同环境中的部署指南，包括开发环境和生产环境。

## 目录

- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [环境配置](#环境配置)
- [部署模式](#部署模式)
- [生产环境部署](#生产环境部署)
- [监控和维护](#监控和维护)
- [故障排除](#故障排除)

## 系统要求

### 硬件要求
- **最小配置**: 2 CPU 核心, 4GB RAM, 20GB 磁盘空间
- **推荐配置**: 4 CPU 核心, 8GB RAM, 50GB 磁盘空间
- **生产环境**: 8+ CPU 核心, 16GB+ RAM, 100GB+ 磁盘空间

### 软件要求
- Docker Engine 20.10+
- Docker Compose 2.0+
- Git (用于代码拉取)

### 网络要求
- 如果使用 AI 功能，需要访问 OpenAI API
- 如果需要邮件通知，需要 SMTP 服务器访问权限

## 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd AutoReportAI
```

### 2. 配置环境变量
```bash
# 复制环境变量模板
cp .env.template .env

# 编辑环境变量
nano .env
```

### 3. 启动服务
```bash
# 启动所有核心服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 4. 初始化数据库
```bash
# 等待数据库启动后，运行数据库初始化
docker-compose exec backend python scripts/init_db.py
```

### 5. 访问应用
- **前端应用**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

## 环境配置

### 必需配置项

在 `.env` 文件中，以下配置项必须设置：

```bash
# 安全密钥（生产环境必须更改）
SECRET_KEY=your_secure_secret_key_minimum_32_characters
ENCRYPTION_KEY=your_base64_encryption_key_here

# 数据库密码
POSTGRES_PASSWORD=your_secure_database_password

# AI API 密钥
OPENAI_API_KEY=your_openai_api_key_here
```

### 生成安全密钥

```bash
# 生成 SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 生成 ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 网络配置

根据你的网络环境，可能需要调整以下配置：

```bash
# CORS 配置 - 添加你的域名
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# 前端 API 地址配置
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

## 部署模式

### 开发模式

适用于开发和测试：

```bash
# 启动包括监控服务的完整开发环境
docker-compose --profile dev up -d

# 这将启动：
# - 核心服务 (db, redis, backend, frontend, celery-worker, celery-beat)
# - 监控服务 (flower)
```

访问地址：
- Flower 监控: http://localhost:5555

### 最小化部署

仅启动核心服务：

```bash
# 仅启动核心服务
docker-compose up -d db redis backend frontend celery-worker celery-beat
```

### 生产模式

包含存储服务的完整生产环境：

```bash
# 启动生产环境
docker-compose --profile prod up -d

# 这将启动：
# - 所有核心服务
# - MinIO 对象存储服务
```

访问地址：
- MinIO 控制台: http://localhost:9001

## 生产环境部署

### 1. 安全配置

更新 `.env` 文件中的安全相关配置：

```bash
# 环境标识
ENVIRONMENT=production

# 安全配置
DEBUG=false
LOG_LEVEL=INFO

# 使用强密码
POSTGRES_PASSWORD=your_very_secure_database_password
SECRET_KEY=your_very_secure_secret_key
ENCRYPTION_KEY=your_secure_encryption_key

# 限制 CORS 来源
CORS_ORIGINS=https://yourdomain.com

# 生产 API 地址
NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api/v1
NEXT_PUBLIC_WS_URL=wss://api.yourdomain.com/ws
```

### 2. 反向代理配置

推荐使用 Nginx 作为反向代理：

```nginx
# nginx.conf 示例
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}

server {
    listen 80;
    server_name api.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### 3. SSL 证书配置

使用 Let's Encrypt 获取免费 SSL 证书：

```bash
# 安装 certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d yourdomain.com -d api.yourdomain.com
```

### 4. 数据备份配置

设置定期数据备份：

```bash
# 创建备份脚本
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# 备份数据库
docker-compose exec -T db pg_dump -U postgres autoreport > $BACKUP_DIR/database.sql

# 备份文件
cp -r ./data/uploads $BACKUP_DIR/
cp -r ./data/reports $BACKUP_DIR/

# 压缩备份
tar -czf $BACKUP_DIR.tar.gz -C /backup $(basename $BACKUP_DIR)
rm -rf $BACKUP_DIR

# 删除 7 天前的备份
find /backup -name "*.tar.gz" -mtime +7 -delete
EOF

chmod +x backup.sh

# 设置定时任务
crontab -e
# 添加：0 2 * * * /path/to/backup.sh
```

## 监控和维护

### 健康检查

```bash
# 检查服务状态
docker-compose ps

# 检查容器健康状态
docker-compose exec backend /app/healthcheck.sh
docker-compose exec frontend wget --spider http://localhost:3000/api/health
```

### 日志管理

```bash
# 查看实时日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f celery-worker

# 查看最近的错误日志
docker-compose logs --tail 100 backend | grep ERROR
```

### 性能监控

启用监控服务：

```bash
# 启动 Flower 监控 Celery 任务
docker-compose --profile monitoring up -d flower

# 访问监控面板
# Flower: http://localhost:5555
```

### 资源使用情况

```bash
# 查看容器资源使用情况
docker stats

# 查看磁盘使用情况
df -h
du -sh ./data/*
```

## 故障排除

### 常见问题

#### 1. 服务无法启动

```bash
# 检查端口占用
netstat -tlnp | grep :8000
netstat -tlnp | grep :3000

# 检查 Docker 状态
docker version
docker-compose version

# 重新构建镜像
docker-compose build --no-cache
```

#### 2. 数据库连接失败

```bash
# 检查数据库容器状态
docker-compose logs db

# 测试数据库连接
docker-compose exec db pg_isready -U postgres

# 重启数据库服务
docker-compose restart db
```

#### 3. 前端无法连接后端

检查环境变量配置：

```bash
# 确认 API 地址配置
echo $NEXT_PUBLIC_API_URL
echo $CORS_ORIGINS

# 检查网络连通性
docker-compose exec frontend ping backend
```

#### 4. AI 功能不工作

```bash
# 检查 AI 配置
echo $OPENAI_API_KEY
echo $AI_PROVIDER

# 测试 API 连接
docker-compose exec backend python scripts/test_ai_integration.py
```

### 日志分析

重要日志文件位置：

```bash
# 应用日志
./data/logs/app.log
./data/logs/performance.log

# Docker 日志
docker-compose logs backend
docker-compose logs celery-worker
```

### 数据恢复

如果需要从备份恢复：

```bash
# 停止服务
docker-compose down

# 恢复数据库
gunzip -c backup_20240101.tar.gz | docker-compose exec -T db psql -U postgres -d autoreport

# 恢复文件
tar -xzf backup_20240101.tar.gz
cp -r backup_20240101/uploads ./data/
cp -r backup_20240101/reports ./data/

# 重启服务
docker-compose up -d
```

## 更新和维护

### 应用程序更新

```bash
# 拉取最新代码
git pull origin main

# 重新构建并部署
docker-compose build --no-cache
docker-compose up -d

# 运行数据库迁移（如有需要）
docker-compose exec backend alembic upgrade head
```

### 系统清理

```bash
# 清理未使用的 Docker 资源
docker system prune -a

# 清理旧的容器镜像
docker image prune -a
```

## 支持和帮助

如果遇到问题：

1. 查看本文档的故障排除部分
2. 检查项目的 GitHub Issues
3. 查看日志文件获取详细错误信息
4. 确保环境配置符合要求

---

**注意**: 生产环境部署前，请仔细阅读并测试所有配置，确保安全性和稳定性。