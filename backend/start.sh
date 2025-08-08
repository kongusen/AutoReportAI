#!/bin/bash

# AutoReportAI Backend 启动脚本
# 确保在虚拟环境中启动后端和Celery

set -e  # 遇到错误时退出

echo "🚀 AutoReportAI Backend 启动脚本"
echo "================================"

# 获取脚本所在目录（backend目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "📂 项目根目录: $PROJECT_ROOT"
echo "📂 后端目录: $SCRIPT_DIR"

# 切换到后端目录
cd "$SCRIPT_DIR"

# 检查虚拟环境（在backend目录中）
VENV_PATH="$SCRIPT_DIR/venv"
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ 虚拟环境不存在: $VENV_PATH"
    echo "💡 请先创建虚拟环境: cd backend && python3 -m venv venv"
    exit 1
fi

echo "🔄 激活虚拟环境..."
source "$VENV_PATH/bin/activate"

# 检查Python版本
echo "🐍 Python版本: $(python --version)"
echo "📍 Python路径: $(which python)"

# 检查依赖
echo "📦 检查关键依赖..."
python -c "import fastapi, uvicorn, celery, redis" || {
    echo "❌ 缺少关键依赖，正在安装..."
    pip install -r requirements.txt
    pip install "celery[redis]"
}

# 检查Redis连接
echo "🔍 检查Redis连接..."
python -c "import redis; r=redis.Redis(host='localhost', port=6380); r.ping()" || {
    echo "❌ Redis连接失败"
    echo "💡 请确保Redis服务正在运行："
    echo "   docker-compose up -d redis"
    exit 1
}

# 设置环境变量
export PYTHONPATH="$SCRIPT_DIR"

echo "🎯 启动AutoReportAI后端服务（包含Celery worker）..."
python run.py