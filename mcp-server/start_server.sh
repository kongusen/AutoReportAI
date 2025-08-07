#!/bin/bash

# AutoReportAI MCP Server 服务器启动脚本

set -e

echo "🚀 准备启动 AutoReportAI MCP Server (统一SSE版本)..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📥 安装依赖..."
pip install -r requirements.txt
pip install uvicorn[standard]

# 加载环境变量
if [ -f ".env.server" ]; then
    echo "⚙️  加载服务器配置..."
    export $(cat .env.server | grep -v '^#' | xargs)
fi

# 清除代理设置
unset ALL_PROXY
unset HTTP_PROXY  
unset HTTPS_PROXY

# 启动服务器
echo "🌐 启动 MCP 服务器 (统一SSE版本)..."
echo "📡 服务地址: http://${MCP_SERVER_HOST:-0.0.0.0}:${MCP_SERVER_PORT:-8001}"
echo "🔗 SSE端点: http://${MCP_SERVER_HOST:-0.0.0.0}:${MCP_SERVER_PORT:-8001}/sse"

python mcp_sse_server.py