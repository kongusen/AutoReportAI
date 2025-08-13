#!/bin/bash

echo "🚀 启动AutoReportAI核心服务..."

# 确保数据目录存在
mkdir -p data/{postgres,redis,logs,uploads,reports,storage}

# 启动核心服务（数据库、Redis、后端、前端）
echo "📦 启动数据库和Redis..."
docker-compose up -d db redis

echo "⏳ 等待数据库和Redis启动..."
sleep 10

echo "🔧 启动后端服务..."
docker-compose up -d backend

echo "⏳ 等待后端服务启动..."
sleep 15

echo "🎨 启动前端服务..."
docker-compose up -d frontend

echo "✅ 核心服务启动完成！"
echo ""
echo "📊 服务状态："
docker-compose ps
echo ""
echo "🌐 访问地址："
echo "   前端: http://localhost:3000"
echo "   后端API: http://localhost:8000"
echo "   数据库: localhost:5432"
echo "   Redis: localhost:6381" 