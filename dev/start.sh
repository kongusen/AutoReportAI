#!/bin/bash

# AutoReportAI 开发环境启动脚本
# 用于快速启动开发环境

set -e

echo "🚀 AutoReportAI 开发环境启动脚本"
echo "=================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查Docker和Docker Compose
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ 错误: Docker未安装，请先安装Docker${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ 错误: Docker Compose未安装，请先安装Docker Compose${NC}"
    exit 1
fi

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}📁 项目根目录: $PROJECT_ROOT${NC}"
echo -e "${BLUE}📁 开发环境目录: $SCRIPT_DIR${NC}"

# 切换到开发环境目录
cd "$SCRIPT_DIR"

# 检查.env文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  未找到 .env 文件，从 .env.example 复制...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ 已创建 .env 文件，请根据需要修改配置${NC}"
    else
        echo -e "${RED}❌ 错误: .env.example 文件不存在${NC}"
        exit 1
    fi
fi

# 功能选择菜单
echo ""
echo -e "${BLUE}🛠️  请选择操作:${NC}"
echo "1) 启动完整开发环境 (前端 + 后端 + 数据库)"
echo "2) 仅启动基础服务 (数据库 + Redis)"
echo "3) 启动后端服务"
echo "4) 启动前端服务"
echo "5) 启动管理工具 (pgAdmin + RedisInsight)"
echo "6) 查看服务状态"
echo "7) 查看服务日志"
echo "8) 停止所有服务"
echo "9) 清理数据 (谨慎使用!)"
echo "0) 退出"

read -p "请输入选择 (0-9): " choice

case $choice in
    1)
        echo -e "${GREEN}🚀 启动完整开发环境...${NC}"
        docker-compose up -d
        ;;
    2)
        echo -e "${GREEN}🗄️  启动基础服务...${NC}"
        docker-compose up -d db redis
        ;;
    3)
        echo -e "${GREEN}🔧 启动后端服务...${NC}"
        docker-compose up -d db redis backend celery-worker celery-beat
        ;;
    4)
        echo -e "${GREEN}🎨 启动前端服务...${NC}"
        docker-compose up -d db redis backend frontend
        ;;
    5)
        echo -e "${GREEN}🛠️  启动管理工具...${NC}"
        docker-compose --profile tools up -d pgadmin redis-insight
        ;;
    6)
        echo -e "${BLUE}📊 服务状态:${NC}"
        docker-compose ps
        ;;
    7)
        echo -e "${BLUE}📋 请选择要查看日志的服务:${NC}"
        echo "1) 后端服务"
        echo "2) 前端服务"
        echo "3) 数据库服务"
        echo "4) Redis服务"
        echo "5) Celery Worker"
        echo "6) 所有服务"
        read -p "请选择 (1-6): " log_choice
        
        case $log_choice in
            1) docker-compose logs -f backend ;;
            2) docker-compose logs -f frontend ;;
            3) docker-compose logs -f db ;;
            4) docker-compose logs -f redis ;;
            5) docker-compose logs -f celery-worker ;;
            6) docker-compose logs -f ;;
            *) echo -e "${RED}❌ 无效选择${NC}" ;;
        esac
        ;;
    8)
        echo -e "${YELLOW}🛑 停止所有服务...${NC}"
        docker-compose down
        echo -e "${GREEN}✅ 所有服务已停止${NC}"
        ;;
    9)
        echo -e "${RED}⚠️  警告: 这将删除所有数据，包括数据库数据！${NC}"
        read -p "确认删除所有数据? (输入 'YES' 确认): " confirm
        if [ "$confirm" = "YES" ]; then
            echo -e "${RED}🗑️  清理所有数据...${NC}"
            docker-compose down -v
            docker-compose down --remove-orphans
            docker system prune -f
            echo -e "${GREEN}✅ 数据清理完成${NC}"
        else
            echo -e "${GREEN}✅ 操作已取消${NC}"
        fi
        ;;
    0)
        echo -e "${GREEN}👋 再见！${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ 无效选择${NC}"
        exit 1
        ;;
esac

# 显示服务信息
if [ "$choice" = "1" ] || [ "$choice" = "3" ] || [ "$choice" = "4" ]; then
    echo ""
    echo -e "${GREEN}✅ 服务启动完成！${NC}"
    echo ""
    echo -e "${BLUE}🌐 服务访问地址:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "• 前端应用:     http://localhost:3000"
    echo "• 后端API:      http://localhost:8000"
    echo "• API文档:      http://localhost:8000/docs"
    echo "• ReDoc文档:    http://localhost:8000/redoc"
    
    if docker-compose ps | grep -q "pgadmin.*Up"; then
        echo "• pgAdmin:      http://localhost:5050"
        echo "  - 邮箱: admin@autoreportai.com"
        echo "  - 密码: admin123"
    fi
    
    if docker-compose ps | grep -q "redis-insight.*Up"; then
        echo "• RedisInsight:  http://localhost:8001"
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo -e "${YELLOW}📝 使用提示:${NC}"
    echo "• 查看服务状态: ./start.sh 然后选择 6"
    echo "• 查看服务日志: ./start.sh 然后选择 7" 
    echo "• 停止所有服务: ./start.sh 然后选择 8"
    echo "• 管理工具启动: ./start.sh 然后选择 5"
    echo ""
    echo -e "${GREEN}🎉 开发环境准备就绪，开始愉快的开发吧！${NC}"
fi