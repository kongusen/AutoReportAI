#!/bin/bash

# 调试期间快速重建脚本 - 只重新构建代码变更，跳过环境变量重建

echo "🚀 快速重建模式 - 调试期间使用"
echo "📝 注意：此脚本跳过环境变量重建，仅重新构建代码变更"

# 停止现有容器
echo "⏹️  停止现有容器..."
docker-compose down

# 只清理构建缓存，保留镜像层
echo "🧹 清理构建缓存..."
docker builder prune -f

# 使用 --no-cache 但保留基础镜像层
echo "🔨 快速重新构建服务（保留基础层）..."
docker-compose build --no-cache --parallel

# 可选：如果只想重建特定服务，取消注释下面的行
# echo "🔨 只重建后端服务..."
# docker-compose build --no-cache backend

# echo "🔨 只重建前端服务..."
# docker-compose build --no-cache frontend

echo "✅ 快速构建完成！"
echo "🚀 启动服务: docker-compose up -d"
echo "📊 查看日志: docker-compose logs -f [service_name]"
echo ""
echo "💡 提示："
echo "   - 如果遇到环境变量问题，请使用 rebuild.sh"
echo "   - 如果只想重建单个服务，可以注释掉上面的并行构建，使用下面的单服务构建"
