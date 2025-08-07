#!/bin/bash

# 激活 Python 虚拟环境
echo "正在激活 Python 虚拟环境..."
source venv/bin/activate

# 显示当前 Python 版本和路径
echo "Python 版本: $(python --version)"
echo "Python 路径: $(which python)"
echo "虚拟环境已激活！"
echo ""
echo "使用方法:"
echo "  source activate_env.sh  # 激活环境"
echo "  deactivate              # 退出环境"
echo ""
echo "常用命令:"
echo "  python -m uvicorn app.main:app --reload  # 运行开发服务器"
echo "  python -m pytest tests/                  # 运行测试"
echo "  alembic upgrade head                     # 数据库迁移" 