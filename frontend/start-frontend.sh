#!/bin/bash

# AutoReportAI Frontend 启动脚本 - 局域网访问优化
# 自动检测并配置局域网访问

set -e

echo "🎨 AutoReportAI Frontend 启动中..."

# 获取服务器IP
SERVER_IP=${SERVER_IP:-localhost}
FRONTEND_PORT=${PORT:-3000}

# 显示启动信息
echo "📱 Frontend 启动配置:"
echo "  • 服务器IP: $SERVER_IP"
echo "  • 端口: $FRONTEND_PORT"
echo "  • 主机绑定: ${HOSTNAME:-0.0.0.0}"

# 检测局域网访问配置
if [ "$SERVER_IP" != "localhost" ] && [ "$SERVER_IP" != "127.0.0.1" ]; then
    echo "🌐 局域网访问模式已启用"
    echo "  • 局域网访问: http://$SERVER_IP:$FRONTEND_PORT"
    echo "  • API地址: ${NEXT_PUBLIC_API_URL:-http://$SERVER_IP:8000/api/v1}"
    echo "  • WebSocket: ${NEXT_PUBLIC_WS_URL:-ws://$SERVER_IP:8000/ws}"
else
    echo "💻 本地访问模式"
    echo "  • 本地访问: http://localhost:$FRONTEND_PORT"
fi

echo "  • Node.js版本: $(node --version)"
echo "  • 环境: ${NODE_ENV:-development}"

# 健康检查函数
health_check() {
    local retries=0
    local max_retries=30
    
    while [ $retries -lt $max_retries ]; do
        if curl -f -s http://localhost:$FRONTEND_PORT/api/health > /dev/null 2>&1; then
            echo "✅ Frontend 健康检查通过"
            return 0
        fi
        
        echo "⏳ 等待 Frontend 启动... ($((retries + 1))/$max_retries)"
        sleep 2
        retries=$((retries + 1))
    done
    
    echo "❌ Frontend 启动超时"
    return 1
}

# 启动前检查
echo "🔍 启动前检查..."

# 检查端口是否被占用
if lsof -Pi :$FRONTEND_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  端口 $FRONTEND_PORT 已被占用"
    echo "尝试终止占用进程..."
    lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# 检查node_modules
if [ ! -d "node_modules" ]; then
    echo "📦 安装依赖..."
    npm ci
fi

# 启动应用
echo "🚀 启动 Next.js 开发服务器..."

# 根据环境选择启动方式
if [ "${NODE_ENV:-development}" = "production" ]; then
    echo "🏭 生产环境模式"
    npm run start &
else
    echo "🛠️  开发环境模式"
    npm run dev &
fi

# 获取进程ID
APP_PID=$!

# 等待启动完成
sleep 5

# 执行健康检查
if health_check; then
    echo "✅ Frontend 启动成功！"
    echo ""
    echo "🌐 访问地址:"
    if [ "$SERVER_IP" != "localhost" ] && [ "$SERVER_IP" != "127.0.0.1" ]; then
        echo "  • 局域网访问: http://$SERVER_IP:$FRONTEND_PORT"
    fi
    echo "  • 本地访问: http://localhost:$FRONTEND_PORT"
    echo ""
    
    # 保持前台运行
    wait $APP_PID
else
    echo "❌ Frontend 启动失败"
    kill $APP_PID 2>/dev/null || true
    exit 1
fi