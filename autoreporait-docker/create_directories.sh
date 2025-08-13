#!/bin/bash

# 创建数据目录脚本
# 用于创建Docker Compose所需的本地目录

echo "开始创建数据目录..."

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "脚本目录: $SCRIPT_DIR"

# 创建数据目录
echo "创建数据目录..."
mkdir -p "$SCRIPT_DIR/data/postgres"
mkdir -p "$SCRIPT_DIR/data/redis"
mkdir -p "$SCRIPT_DIR/data/logs"
mkdir -p "$SCRIPT_DIR/data/uploads"
mkdir -p "$SCRIPT_DIR/data/reports"
mkdir -p "$SCRIPT_DIR/data/storage"
mkdir -p "$SCRIPT_DIR/data/celery-beat"
mkdir -p "$SCRIPT_DIR/data/minio"
mkdir -p "$SCRIPT_DIR/data/frontend-public"

# 设置目录权限为777
echo "设置目录权限为777..."
chmod -R 777 "$SCRIPT_DIR/data"

# 显示创建的目录
echo ""
echo "已创建的目录:"
ls -la "$SCRIPT_DIR/data/"

echo ""
echo "目录权限:"
ls -la "$SCRIPT_DIR/data/" | grep "^d"

echo ""
echo "所有数据目录创建完成！"
echo "现在可以运行: docker compose --profile storage up -d"
