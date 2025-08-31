# 生产环境部署指南

本文档详细说明如何将 AutoReportAI 部署到生产环境。

## 🏗️ 部署架构

### 推荐部署架构
```
Load Balancer (Nginx)
    ↓
┌─────────────────────────────────────┐
│         Application Layer           │
├─────────────────────────────────────┤
│ Frontend (Next.js)  │ Backend (FastAPI)│
│ Port: 3000         │ Port: 8000       │
└─────────────────────────────────────┘
    ↓                     ↓
┌─────────────────────────────────────┐
│         Infrastructure Layer        │
├─────────────────────────────────────┤
│ PostgreSQL  │ Redis  │ MinIO (Optional)│
│ Port: 5432  │ 6379   │ Port: 9000      │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│         External Services           │
├─────────────────────────────────────┤
│ Doris/MySQL  │ LLM APIs │ Monitoring │
└─────────────────────────────────────┘
```

## 🐳 Docker 部署 (推荐)

### 1. 准备部署文件

#### docker-compose.production.yml
```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx.conf:/etc/nginx/nginx.conf
      - ./docker/ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend
    restart: always

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: production
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_URL=https://your-domain.com/api
    restart: always

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    environment:
      - ENV=production
      - DATABASE_URL=postgresql://user:password@db:5432/autoreport
      - REDIS_URL=redis://redis:6379
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - db
      - redis
    restart: always

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=autoreport
      - POSTGRES_USER=autoreport
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    restart: always

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: always

  celery:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    command: celery -A app.core.celery_scheduler worker -l info
    environment:
      - ENV=production
      - DATABASE_URL=postgresql://user:password@db:5432/autoreport
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    restart: always

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    command: celery -A app.core.celery_scheduler beat -l info
    environment:
      - ENV=production
      - DATABASE_URL=postgresql://user:password@db:5432/autoreport
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    restart: always

volumes:
  postgres_data:
  redis_data:
```

### 2. 环境配置

#### .env.production
```bash
# 应用配置
ENV=production
DEBUG=false
SECRET_KEY=your-super-secret-key-here

# 数据库配置
DB_PASSWORD=your-db-password
POSTGRES_DB=autoreport
POSTGRES_USER=autoreport

# Redis 配置
REDIS_PASSWORD=your-redis-password

# API 配置
API_V1_STR=/api/v1
PROJECT_NAME="AutoReportAI"

# 安全配置
CORS_ORIGINS=["https://your-domain.com"]
ALLOWED_HOSTS=["your-domain.com"]

# LLM 配置
OPENAI_API_KEY=your-openai-api-key
```

### 3. SSL 证书配置

#### nginx.conf
```nginx
events {
    worker_connections 1024;
}

http {
    upstream frontend {
        server frontend:3000;
    }

    upstream backend {
        server backend:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Backend API
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### 4. 部署命令
```bash
# 创建环境配置
cp .env.example .env.production
# 编辑 .env.production 文件

# 构建并启动服务
docker-compose -f docker-compose.production.yml up -d

# 查看服务状态
docker-compose -f docker-compose.production.yml ps

# 查看日志
docker-compose -f docker-compose.production.yml logs -f
```

## 🖥️ 裸机部署

### 1. 系统要求
- **OS**: Ubuntu 20.04+ / CentOS 8+
- **Memory**: 8GB+ RAM
- **Storage**: 100GB+ SSD
- **Network**: 带宽 100Mbps+

### 2. 依赖安装
```bash
# Ubuntu
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip
sudo apt install -y nodejs npm
sudo apt install -y postgresql postgresql-contrib
sudo apt install -y redis-server
sudo apt install -y nginx

# 安装 PM2 (Node.js 进程管理)
npm install -g pm2
```

### 3. 数据库配置
```bash
# PostgreSQL 配置
sudo -u postgres createuser --createdb autoreport
sudo -u postgres createdb autoreport

# Redis 配置
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### 4. 应用部署
```bash
# 部署后端
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env.production
# 编辑配置文件

# 启动后端服务
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000" --name autoreport-backend

# 部署前端
cd ../frontend
npm install
npm run build
pm2 start "npm start" --name autoreport-frontend
```

### 5. Nginx 配置
```bash
# 创建配置文件
sudo nano /etc/nginx/sites-available/autoreport

# 启用站点
sudo ln -s /etc/nginx/sites-available/autoreport /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 🔒 安全配置

### 1. 防火墙配置
```bash
# UFW 配置
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### 2. SSL 证书 (Let's Encrypt)
```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com
```

### 3. 数据库安全
```bash
# PostgreSQL 安全配置
sudo nano /etc/postgresql/14/main/postgresql.conf
# 设置 listen_addresses = 'localhost'

sudo nano /etc/postgresql/14/main/pg_hba.conf
# 配置访问控制
```

## 📊 监控和日志

### 1. 应用监控
```bash
# 安装监控工具
pip install prometheus-client
npm install @prometheus/client

# PM2 监控
pm2 monit
```

### 2. 日志管理
```bash
# 配置日志轮转
sudo nano /etc/logrotate.d/autoreport

/var/log/autoreport/*.log {
    daily
    missingok
    rotate 30
    compress
    notifempty
    create 0644 www-data www-data
}
```

### 3. 健康检查
```bash
# 创建健康检查脚本
nano /opt/autoreport/healthcheck.sh

#!/bin/bash
curl -f http://localhost:8000/health || exit 1

# 添加到 crontab
crontab -e
*/5 * * * * /opt/autoreport/healthcheck.sh
```

## 🔄 CI/CD 配置

### GitHub Actions
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to server
        uses: appleboy/ssh-action@v0.1.5
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.PRIVATE_KEY }}
          script: |
            cd /opt/autoreport
            git pull origin main
            docker-compose -f docker-compose.production.yml up -d --build
```

## 🚀 性能优化

### 1. 数据库优化
```sql
-- PostgreSQL 配置优化
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '10MB';
SELECT pg_reload_conf();
```

### 2. Redis 优化
```bash
# Redis 配置优化
echo 'maxmemory 512mb' >> /etc/redis/redis.conf
echo 'maxmemory-policy allkeys-lru' >> /etc/redis/redis.conf
```

### 3. 应用优化
- 启用 gzip 压缩
- 配置静态文件缓存
- 使用 CDN 加速
- 数据库连接池优化

## 🔧 运维命令

### 常用运维命令
```bash
# 重启服务
pm2 restart all

# 查看日志
pm2 logs
docker-compose logs -f

# 备份数据库
pg_dump autoreport > backup_$(date +%Y%m%d).sql

# 更新应用
git pull origin main
docker-compose -f docker-compose.production.yml up -d --build
```

### 故障排除
```bash
# 检查服务状态
systemctl status nginx
systemctl status postgresql
systemctl status redis

# 检查端口占用
netstat -tlnp | grep :8000

# 检查资源使用
htop
df -h
```

---

*最后更新：2025-08-29*