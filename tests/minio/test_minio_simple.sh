#!/bin/bash

# AutoReportAI Minio集成测试脚本
# 使用curl测试Minio服务功能

echo "🚀 AutoReportAI Minio集成测试"
echo "=" * 50

echo ""
echo "📡 测试默认Minio服务 (端口9000/9001):"
echo "-" * 40

# 测试默认Minio API健康状态
echo "🔍 测试API健康状态..."
if curl -s -f http://localhost:9000/minio/health/live > /dev/null; then
    echo "✅ 默认Minio API (端口9000) 运行正常"
else
    echo "❌ 默认Minio API (端口9000) 连接失败"
fi

# 测试默认Minio控制台
echo "🔍 测试Web控制台..."
if curl -s -f http://localhost:9001/minio/health/live > /dev/null; then
    echo "✅ 默认Minio控制台 (端口9001) 可访问"
else
    echo "⚠️  默认Minio控制台 (端口9001) 可能在不同路径"
    # 测试根路径
    if curl -s -I http://localhost:9001/ | grep -q "200 OK"; then
        echo "✅ 默认Minio控制台根路径可访问"
    fi
fi

echo ""
echo "🛠️ 测试开发模式Minio服务 (端口9002/9003):"
echo "-" * 40

# 测试开发模式Minio API
echo "🔍 测试开发模式API..."
if curl -s -f http://localhost:9002/minio/health/live > /dev/null; then
    echo "✅ 开发模式Minio API (端口9002) 运行正常"
else
    echo "❌ 开发模式Minio API (端口9002) 连接失败"
fi

# 测试开发模式控制台
echo "🔍 测试开发模式控制台..."
if curl -s -f http://localhost:9003/minio/health/live > /dev/null; then
    echo "✅ 开发模式Minio控制台 (端口9003) 可访问"
else
    echo "⚠️  开发模式Minio控制台 (端口9003) 可能在不同路径"
    # 测试根路径
    if curl -s -I http://localhost:9003/ | grep -q "200 OK"; then
        echo "✅ 开发模式Minio控制台根路径可访问"
    fi
fi

echo ""
echo "🐳 检查Docker容器状态:"
echo "-" * 30

echo "📊 运行中的Minio容器:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep minio

echo ""
echo "🔍 容器健康状态:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep minio | while read line; do
    container_name=$(echo $line | awk '{print $1}')
    status=$(echo $line | awk '{print $2}')
    if [[ $status == *"healthy"* ]]; then
        echo "✅ $container_name: 健康"
    elif [[ $status == *"unhealthy"* ]]; then
        echo "❌ $container_name: 不健康"
    else
        echo "⚠️  $container_name: $status"
    fi
done

echo ""
echo "📊 测试总结:"
echo "-" * 20

# 检查默认Minio
default_status="❌"
if curl -s -f http://localhost:9000/minio/health/live > /dev/null; then
    default_status="✅"
fi

# 检查开发Minio
dev_status="❌"
if curl -s -f http://localhost:9002/minio/health/live > /dev/null; then
    dev_status="✅"
fi

echo "默认Minio服务: $default_status"
echo "开发模式Minio: $dev_status"

echo ""
echo "💡 访问地址:"
echo "   - 默认Minio控制台: http://localhost:9001"
echo "     用户名: minioadmin"
echo "     密码: minioadmin123"
echo ""
echo "   - 开发Minio控制台: http://localhost:9003" 
echo "     用户名: devuser"
echo "     密码: devpassword123"

if [[ $default_status == "✅" ]] && [[ $dev_status == "✅" ]]; then
    echo ""
    echo "🎉 所有Minio服务运行正常!"
    echo "✅ AutoReportAI Docker环境Minio集成成功"
    exit 0
else
    echo ""
    echo "⚠️  部分Minio服务可能未正常运行"
    echo "💡 请检查Docker Compose配置和服务状态"
    exit 1
fi