#!/bin/bash

# AutoReportAI 开发环境启动脚本
# 支持多种启动模式

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 图标定义
ROCKET="🚀"
DATABASE="🗄️"
GEAR="🔧"
PAINT="🎨"
PACKAGE="📦"
CHECKMARK="✅"
CROSS="❌"

echo -e "${BLUE}${PACKAGE} AutoReportAI 开发环境启动器${NC}"
echo -e "${CYAN}基于 React Agent 架构 - 现代化微服务设计${NC}"
echo ""

# 检查Docker和docker-compose
check_requirements() {
    echo -e "${YELLOW}检查系统要求...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}${CROSS} Docker 未安装${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}${CROSS} Docker Compose 未安装${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}${CHECKMARK} 系统要求检查通过${NC}"
    echo ""
}

# 检查并创建必要的目录（如果需要）
ensure_directories() {
    echo -e "${YELLOW}检查数据目录...${NC}"
    echo -e "${GREEN}${CHECKMARK} Docker将自动创建所需的数据目录${NC}"
    echo ""
}

# 显示菜单
show_menu() {
    echo -e "${PACKAGE} 核心服务:"
    echo -e "  ${GREEN}1)${NC} ${ROCKET} 启动完整开发环境 (推荐)"
    echo -e "  ${GREEN}2)${NC} ${DATABASE} 仅启动基础服务 (数据库 + Redis + Minio)"
    echo -e "  ${GREEN}3)${NC} ${GEAR} 启动后端服务 (API + Worker + Beat)"
    echo -e "  ${GREEN}4)${NC} ${PAINT} 启动前端服务 (Next.js + React Agent UI)"
    echo -e "  ${GREEN}5)${NC} ${GEAR} 启动开发工具 (PgAdmin + Redis Insight)"
    echo -e "  ${GREEN}6)${NC} ${PACKAGE} 查看服务状态"
    echo -e "  ${GREEN}7)${NC} ${PACKAGE} 停止所有服务"
    echo -e "  ${GREEN}8)${NC} ${PACKAGE} 查看服务日志"
    echo -e "  ${GREEN}9)${NC} ${PACKAGE} 重启服务"
    echo -e "  ${RED}0)${NC} 退出"
    echo ""
}

# 启动完整环境
start_full() {
    echo -e "${GREEN}${ROCKET} 启动完整开发环境...${NC}"
    docker-compose up -d
    show_services_status
}

# 启动基础服务
start_basic() {
    echo -e "${GREEN}${DATABASE} 启动基础服务...${NC}"
    docker-compose up -d db redis minio
    show_services_status
}

# 启动后端服务
start_backend() {
    echo -e "${GREEN}${GEAR} 启动后端服务...${NC}"
    docker-compose up -d db redis minio backend celery-worker celery-beat
    show_services_status
}

# 启动前端服务
start_frontend() {
    echo -e "${GREEN}${PAINT} 启动前端服务...${NC}"
    docker-compose up -d frontend
    show_services_status
}

# 启动开发工具
start_tools() {
    echo -e "${GREEN}${GEAR} 启动开发工具...${NC}"
    docker-compose --profile tools up -d
    show_services_status
}

# 查看服务状态
show_services_status() {
    echo -e "${YELLOW}服务状态:${NC}"
    docker-compose ps
    echo ""
    echo -e "${CYAN}访问地址:${NC}"
    echo -e "  • 前端: ${GREEN}http://localhost:3000${NC}"
    echo -e "  • 后端API: ${GREEN}http://localhost:8000${NC}"
    echo -e "  • API文档: ${GREEN}http://localhost:8000/docs${NC}"
    echo -e "  • Minio控制台: ${GREEN}http://localhost:9001${NC}"
    echo -e "  • PgAdmin: ${GREEN}http://localhost:5050${NC} (需启用tools)"
    echo -e "  • Redis Insight: ${GREEN}http://localhost:8001${NC} (需启用tools)"
    echo ""
}

# 停止所有服务
stop_all() {
    echo -e "${RED}停止所有服务...${NC}"
    docker-compose down
    docker-compose --profile tools down
    echo -e "${GREEN}${CHECKMARK} 所有服务已停止${NC}"
}

# 查看日志
show_logs() {
    echo -e "${CYAN}选择要查看日志的服务:${NC}"
    echo "1) 所有服务"
    echo "2) 后端 API"
    echo "3) 前端"
    echo "4) 数据库"
    echo "5) Redis"
    echo "6) Celery Worker"
    echo "7) Celery Beat"
    echo ""
    read -p "请选择 (1-7): " log_choice
    
    case $log_choice in
        1) docker-compose logs -f ;;
        2) docker-compose logs -f backend ;;
        3) docker-compose logs -f frontend ;;
        4) docker-compose logs -f db ;;
        5) docker-compose logs -f redis ;;
        6) docker-compose logs -f celery-worker ;;
        7) docker-compose logs -f celery-beat ;;
        *) echo "无效选择" ;;
    esac
}

# 重启服务
restart_services() {
    echo -e "${CYAN}选择要重启的服务:${NC}"
    echo "1) 所有服务"
    echo "2) 后端服务"
    echo "3) 前端服务"
    echo "4) 基础服务"
    echo ""
    read -p "请选择 (1-4): " restart_choice
    
    case $restart_choice in
        1) docker-compose restart ;;
        2) docker-compose restart backend celery-worker celery-beat ;;
        3) docker-compose restart frontend ;;
        4) docker-compose restart db redis minio ;;
        *) echo "无效选择" ;;
    esac
    show_services_status
}

# 主程序
main() {
    check_requirements
    
    # 如果没有参数，显示交互式菜单
    if [ $# -eq 0 ]; then
        while true; do
            show_menu
            read -p "请选择 (0-9): " choice
            echo ""
            
            case $choice in
                1)
                    ensure_directories
                    start_full
                    ;;
                2)
                    ensure_directories
                    start_basic
                    ;;
                3)
                    ensure_directories
                    start_backend
                    ;;
                4)
                    start_frontend
                    ;;
                5)
                    start_tools
                    ;;
                6)
                    show_services_status
                    ;;
                7)
                    stop_all
                    ;;
                8)
                    show_logs
                    ;;
                9)
                    restart_services
                    ;;
                0)
                    echo -e "${GREEN}再见！${NC}"
                    exit 0
                    ;;
                *)
                    echo -e "${RED}无效选择，请重试${NC}"
                    ;;
            esac
            
            echo ""
            read -p "按回车键继续..."
            clear
        done
    else
        # 支持命令行参数
        case $1 in
            "full"|"all")
                ensure_directories
                start_full
                ;;
            "basic"|"base")
                ensure_directories
                start_basic
                ;;
            "backend"|"api")
                ensure_directories
                start_backend
                ;;
            "frontend"|"ui")
                start_frontend
                ;;
            "tools")
                start_tools
                ;;
            "status")
                show_services_status
                ;;
            "stop")
                stop_all
                ;;
            "logs")
                docker-compose logs -f
                ;;
            "restart")
                docker-compose restart
                show_services_status
                ;;
            *)
                echo "用法: $0 [full|basic|backend|frontend|tools|status|stop|logs|restart]"
                echo "或运行不带参数进入交互模式"
                ;;
        esac
    fi
}

# 捕获Ctrl+C
trap 'echo -e "\n${YELLOW}操作已取消${NC}"; exit 0' INT

# 启动主程序
main "$@"