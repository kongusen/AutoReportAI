#!/bin/bash

# 清理Docker缓存和重新构建脚本

echo "🧹 清理Docker缓存..."
docker system prune -f
docker builder prune -f

echo "🗑️ 删除现有容器和镜像..."
docker-compose down --remove-orphans
docker rmi $(docker images -q autoreporait-docker_backend) 2>/dev/null || true
docker rmi $(docker images -q autoreporait-docker_frontend) 2>/dev/null || true
docker rmi $(docker images -q autoreporait-docker_celery-worker) 2>/dev/null || true
docker rmi $(docker images -q autoreporait-docker_celery-beat) 2>/dev/null || true
docker rmi $(docker images -q autoreporait-docker_flower) 2>/dev/null || true

echo "🔨 重新构建服务..."
docker-compose build --no-cache

echo "✅ 构建完成！"
echo "🚀 启动服务: docker-compose up -d" 