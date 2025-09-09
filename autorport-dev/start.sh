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
    
    if ! command -v docker-compose &> /dev/null && ! command -v docker compose &> /dev/null; then
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

# 获取本机IP地址
get_local_ip() {
    # 优先使用连接到默认网关的网络接口IP
    local ip=$(ip route get 8.8.8.8 2>/dev/null | grep -oE 'src [0-9]{1,3}(\.[0-9]{1,3}){3}' | awk '{print $2}')
    if [ -z "$ip" ]; then
        # macOS系统或其他系统的fallback
        ip=$(ifconfig 2>/dev/null | grep -E 'inet [0-9]' | grep -v 'inet 127.0.0.1' | head -1 | awk '{print $2}')
    fi
    if [ -z "$ip" ]; then
        # 最后的fallback
        ip="localhost"
    fi
    echo "$ip"
}

# 自动配置环境文件
setup_env() {
    local env_mode=$1
    local compose_file=""
    local env_example=""
    local local_ip=$(get_local_ip)
    
    echo -e "${YELLOW}${GEAR} 配置环境 ($env_mode)${NC}"
    echo -e "检测到本机IP: ${GREEN}$local_ip${NC}"
    
    case $env_mode in
        "deployment")
            env_example=".env.example"
            compose_file="docker-compose.yml"
            ;;
        "proxy")
            env_example=".env.proxy.example"
            compose_file="docker-compose.proxy.yml"
            ;;
        *)
            echo -e "${RED}无效的环境模式: $env_mode${NC}"
            return 1
            ;;
    esac
    
    # 检查example文件是否存在
    if [ ! -f "$env_example" ]; then
        echo -e "${RED}${CROSS} 环境模板文件不存在: $env_example${NC}"
        return 1
    fi
    
    # 创建.env文件
    echo -e "${YELLOW}基于 $env_example 创建 .env 文件...${NC}"
    cp "$env_example" .env
    
    # 自动替换IP地址相关配置
    if [ "$local_ip" != "localhost" ]; then
        echo -e "${YELLOW}更新环境配置中的IP地址...${NC}"
        
        # 替换SERVER_IP
        sed -i.bak "s|SERVER_IP=.*|SERVER_IP=$local_ip|g" .env
        
        # 处理不同的前端API地址格式
        if grep -q "NEXT_PUBLIC_API_URL=http://\${SERVER_IP}" .env; then
            # 如果使用变量格式，直接进行变量替换
            sed -i.bak "s|\${SERVER_IP}|$local_ip|g" .env
        else
            # 如果使用固定格式，替换为实际IP
            sed -i.bak "s|NEXT_PUBLIC_API_URL=http://.*:8000/api/v1|NEXT_PUBLIC_API_URL=http://$local_ip:8000/api/v1|g" .env
            sed -i.bak "s|NEXT_PUBLIC_WS_URL=ws://.*:8000/ws|NEXT_PUBLIC_WS_URL=ws://$local_ip:8000/ws|g" .env
        fi
        
        # 更新CORS配置，支持局域网访问
        local cors_origins="http://localhost:3000,http://127.0.0.1:3000,http://$local_ip:3000,http://0.0.0.0:3000"
        sed -i.bak "s|ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=$cors_origins|g" .env
        
        # 删除备份文件
        rm -f .env.bak
    fi
    
    # 生成安全密钥
    echo -e "${YELLOW}生成安全密钥...${NC}"
    local secret_key=$(openssl rand -base64 32 2>/dev/null || echo "auto-generated-secret-$(date +%s)")
    local encryption_key=$(openssl rand -base64 32 2>/dev/null || echo "auto-generated-encrypt-$(date +%s)")
    
    sed -i.bak "s|SECRET_KEY=.*|SECRET_KEY=$secret_key|g" .env
    sed -i.bak "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$encryption_key|g" .env
    rm -f .env.bak
    
    # 配置代理模式特定设置
    if [ "$env_mode" = "proxy" ]; then
        echo -e "${YELLOW}检测代理设置...${NC}"
        if [ -n "$http_proxy" ] || [ -n "$HTTP_PROXY" ]; then
            proxy_url="${http_proxy:-$HTTP_PROXY}"
            echo -e "${GREEN}检测到代理: $proxy_url${NC}"
            sed -i.bak "s|BUILD_HTTP_PROXY=.*|BUILD_HTTP_PROXY=$proxy_url|g" .env
            sed -i.bak "s|BUILD_HTTPS_PROXY=.*|BUILD_HTTPS_PROXY=$proxy_url|g" .env
            rm -f .env.bak
        fi
    fi
    
    echo -e "${GREEN}${CHECKMARK} 环境配置完成${NC}"
    echo -e "  • 配置文件: ${CYAN}.env${NC}"
    echo -e "  • Docker Compose: ${CYAN}$compose_file${NC}"
    echo -e "  • 本机IP: ${CYAN}$local_ip${NC}"
    echo ""
    
    # 设置全局compose文件变量
    export COMPOSE_FILE="$compose_file"
}

# 显示菜单
show_menu() {
    echo -e "${PACKAGE} 核心服务:"
    echo -e "  ${GREEN}1)${NC} ${ROCKET} 启动完整开发环境 (推荐)"
    echo -e "  ${GREEN}2)${NC} ${DATABASE} 仅启动基础服务 (数据库 + Redis + Minio)"
    echo -e "  ${GREEN}3)${NC} ${GEAR} 启动后端服务 (API + Worker + Beat)"
    echo -e "  ${GREEN}4)${NC} ${PAINT} 启动前端服务 (Next.js + React Agent UI)"
    echo -e "  ${GREEN}5)${NC} ${GEAR} 启动开发工具 (PgAdmin + Redis Insight)"
    echo ""
    echo -e "${PACKAGE} 部署环境:"
    echo -e "  ${GREEN}11)${NC} ${ROCKET} 部署环境启动 (自动配置IP)"
    echo -e "  ${GREEN}12)${NC} ${ROCKET} 代理环境启动 (企业网络)"
    echo ""
    echo -e "${PACKAGE} 管理操作:"
    echo -e "  ${GREEN}6)${NC} ${PACKAGE} 查看服务状态"
    echo -e "  ${GREEN}7)${NC} ${PACKAGE} 停止所有服务"
    echo -e "  ${GREEN}8)${NC} ${PACKAGE} 查看服务日志"
    echo -e "  ${GREEN}9)${NC} ${PACKAGE} 重启服务"
    echo -e "  ${GREEN}10)${NC} ${PACKAGE} 重建并重启 (代码更新后)"
    echo -e "  ${GREEN}13)${NC} ${PACKAGE} 清理环境数据"
    echo -e "  ${RED}0)${NC} 退出"
    echo ""
}

# 启动完整环境
start_full() {
    echo -e "${GREEN}${ROCKET} 启动完整开发环境...${NC}"
    local compose_cmd="docker-compose"
    if [ -n "$COMPOSE_FILE" ] && [ "$COMPOSE_FILE" != "docker-compose.yml" ]; then
        compose_cmd="docker-compose -f $COMPOSE_FILE"
    fi
    eval "$compose_cmd up -d"
    show_services_status
}

# 部署环境启动 (自动配置)
start_deployment() {
    echo -e "${GREEN}${ROCKET} 部署环境启动 (自动配置IP)...${NC}"
    
    # 自动配置环境
    setup_env "deployment"
    if [ $? -ne 0 ]; then
        echo -e "${RED}${CROSS} 环境配置失败${NC}"
        return 1
    fi
    
    # 确保目录存在
    ensure_directories
    
    # 启动服务
    echo -e "${GREEN}启动所有服务...${NC}"
    docker-compose up -d
    
    # 显示状态
    show_services_status
    
    # 显示访问信息
    local local_ip=$(get_local_ip)
    echo -e "${CYAN}部署完成！访问地址:${NC}"
    echo -e "  • 前端: ${GREEN}http://$local_ip:3000${NC}"
    echo -e "  • 后端API: ${GREEN}http://$local_ip:8000${NC}"
    echo -e "  • API文档: ${GREEN}http://$local_ip:8000/docs${NC}"
    echo -e "  • Minio控制台: ${GREEN}http://$local_ip:9001${NC}"
    echo ""
}

# 代理环境启动 (企业网络)
start_proxy() {
    echo -e "${GREEN}${ROCKET} 代理环境启动 (企业网络)...${NC}"
    
    # 检查代理环境
    if [ -z "$http_proxy" ] && [ -z "$HTTP_PROXY" ]; then
        echo -e "${YELLOW}⚠️  未检测到代理设置${NC}"
        echo -e "${CYAN}如果需要代理，请先设置环境变量：${NC}"
        echo -e "  export http_proxy=http://your-proxy:port"
        echo -e "  export https_proxy=http://your-proxy:port"
        echo ""
        read -p "继续启动吗？(y/N): " continue_without_proxy
        if [[ ! "$continue_without_proxy" =~ ^[Yy]$ ]]; then
            return 0
        fi
    fi
    
    # 自动配置环境
    setup_env "proxy"
    if [ $? -ne 0 ]; then
        echo -e "${RED}${CROSS} 环境配置失败${NC}"
        return 1
    fi
    
    # 确保目录存在
    ensure_directories
    
    # 启动服务
    echo -e "${GREEN}启动所有服务 (使用代理配置)...${NC}"
    docker-compose -f docker-compose.proxy.yml up -d
    
    # 显示状态
    show_services_status
    
    # 显示访问信息
    local local_ip=$(get_local_ip)
    echo -e "${CYAN}代理环境部署完成！访问地址:${NC}"
    echo -e "  • 前端: ${GREEN}http://$local_ip:3000${NC}"
    echo -e "  • 后端API: ${GREEN}http://$local_ip:8000${NC}"
    echo -e "  • API文档: ${GREEN}http://$local_ip:8000/docs${NC}"
    if [ -n "$http_proxy" ] || [ -n "$HTTP_PROXY" ]; then
        echo -e "  • 代理: ${GREEN}${http_proxy:-$HTTP_PROXY}${NC}"
    fi
    echo ""
}

# 启动基础服务
start_basic() {
    echo -e "${GREEN}${DATABASE} 启动基础服务...${NC}"
    local compose_cmd="docker-compose"
    if [ -n "$COMPOSE_FILE" ] && [ "$COMPOSE_FILE" != "docker-compose.yml" ]; then
        compose_cmd="docker-compose -f $COMPOSE_FILE"
    fi
    eval "$compose_cmd up -d db redis minio"
    show_services_status
}

# 启动后端服务
start_backend() {
    echo -e "${GREEN}${GEAR} 启动后端服务...${NC}"
    local compose_cmd="docker-compose"
    if [ -n "$COMPOSE_FILE" ] && [ "$COMPOSE_FILE" != "docker-compose.yml" ]; then
        compose_cmd="docker-compose -f $COMPOSE_FILE"
    fi
    eval "$compose_cmd up -d db redis minio backend celery-worker celery-beat"
    show_services_status
}

# 启动前端服务
start_frontend() {
    echo -e "${GREEN}${PAINT} 启动前端服务...${NC}"
    local compose_cmd="docker-compose"
    if [ -n "$COMPOSE_FILE" ] && [ "$COMPOSE_FILE" != "docker-compose.yml" ]; then
        compose_cmd="docker-compose -f $COMPOSE_FILE"
    fi
    eval "$compose_cmd up -d frontend"
    show_services_status
}

# 启动开发工具
start_tools() {
    echo -e "${GREEN}${GEAR} 启动开发工具...${NC}"
    local compose_cmd="docker-compose"
    if [ -n "$COMPOSE_FILE" ] && [ "$COMPOSE_FILE" != "docker-compose.yml" ]; then
        compose_cmd="docker-compose -f $COMPOSE_FILE"
    fi
    eval "$compose_cmd --profile tools up -d"
    show_services_status
}

# 清理环境数据
clean_environment() {
    echo -e "${RED}${PACKAGE} 清理环境数据${NC}"
    echo -e "${YELLOW}⚠️  此操作将删除所有数据，包括数据库、缓存和存储文件！${NC}"
    echo ""
    echo -e "将要清理的内容："
    echo -e "  • 停止所有容器"
    echo -e "  • 删除所有容器和网络"
    echo -e "  • 删除数据目录 (./data/)"
    echo -e "  • 删除环境配置文件 (.env)"
    echo -e "  • 清理Docker镜像"
    echo ""
    
    read -p "确认清理环境？请输入 'CLEAN' 确认: " confirm
    if [ "$confirm" != "CLEAN" ]; then
        echo -e "${GREEN}操作已取消${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}开始清理环境...${NC}"
    
    # 停止所有服务
    echo -e "${YELLOW}停止所有服务...${NC}"
    docker-compose down 2>/dev/null || true
    docker-compose -f docker-compose.proxy.yml down 2>/dev/null || true
    docker-compose --profile tools down 2>/dev/null || true
    
    # 删除数据目录
    if [ -d "./data" ]; then
        echo -e "${YELLOW}删除数据目录...${NC}"
        sudo rm -rf ./data/ || rm -rf ./data/
    fi
    
    # 删除环境文件
    if [ -f ".env" ]; then
        echo -e "${YELLOW}删除环境配置...${NC}"
        rm -f .env
    fi
    
    # 清理Docker资源
    echo -e "${YELLOW}清理Docker资源...${NC}"
    docker system prune -f 2>/dev/null || true
    docker volume prune -f 2>/dev/null || true
    
    echo -e "${GREEN}${CHECKMARK} 环境清理完成${NC}"
    echo -e "${CYAN}重新开始使用前，请重新运行启动脚本${NC}"
    echo ""
}

# 查看服务状态
show_services_status() {
    echo -e "${YELLOW}服务状态:${NC}"
    local compose_cmd="docker-compose"
    if [ -n "$COMPOSE_FILE" ] && [ "$COMPOSE_FILE" != "docker-compose.yml" ]; then
        compose_cmd="docker-compose -f $COMPOSE_FILE"
    fi
    eval "$compose_cmd ps"
    echo ""
    
    # 获取当前IP
    local current_ip=$(get_local_ip)
    
    echo -e "${CYAN}访问地址:${NC}"
    echo -e "  • 前端: ${GREEN}http://$current_ip:3000${NC}"
    echo -e "  • 后端API: ${GREEN}http://$current_ip:8000${NC}"
    echo -e "  • API文档: ${GREEN}http://$current_ip:8000/docs${NC}"
    echo -e "  • Minio控制台: ${GREEN}http://$current_ip:9001${NC}"
    echo -e "  • PgAdmin: ${GREEN}http://$current_ip:5050${NC} (需启用tools)"
    echo -e "  • Redis Insight: ${GREEN}http://$current_ip:8001${NC} (需启用tools)"
    
    # 显示当前配置信息
    if [ -f ".env" ]; then
        echo ""
        echo -e "${CYAN}当前配置:${NC}"
        if [ -n "$COMPOSE_FILE" ]; then
            echo -e "  • Docker Compose: ${GREEN}$COMPOSE_FILE${NC}"
        else
            echo -e "  • Docker Compose: ${GREEN}docker-compose.yml${NC}"
        fi
        echo -e "  • 本机IP: ${GREEN}$current_ip${NC}"
    fi
    echo ""
}

# 停止所有服务
stop_all() {
    echo -e "${RED}停止所有服务...${NC}"
    
    # 停止标准配置
    docker-compose down 2>/dev/null || true
    docker-compose --profile tools down 2>/dev/null || true
    
    # 停止代理配置
    docker-compose -f docker-compose.proxy.yml down 2>/dev/null || true
    
    # 清理网络
    docker network prune -f 2>/dev/null || true
    
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

# 重建并重启服务
rebuild_services() {
    echo -e "${YELLOW}${PACKAGE} 重建并重启服务 (代码更新后)${NC}"
    echo -e "${CYAN}选择要重建的服务:${NC}"
    echo "1) 重建所有服务 (完整重建)"
    echo "2) 重建后端服务 (API + Worker + Beat)"
    echo "3) 重建前端服务 (Next.js)"
    echo "4) 重建并重启所有服务"
    echo ""
    read -p "请选择 (1-4): " rebuild_choice
    
    case $rebuild_choice in
        1)
            echo -e "${YELLOW}停止所有服务...${NC}"
            docker-compose down
            echo -e "${YELLOW}重建所有镜像...${NC}"
            docker-compose build --no-cache
            echo -e "${GREEN}启动所有服务...${NC}"
            docker-compose up -d
            ;;
        2)
            echo -e "${YELLOW}停止后端服务...${NC}"
            docker-compose stop backend celery-worker celery-beat
            echo -e "${YELLOW}重建后端镜像...${NC}"
            docker-compose build --no-cache backend
            echo -e "${GREEN}启动后端服务...${NC}"
            docker-compose up -d backend celery-worker celery-beat
            ;;
        3)
            echo -e "${YELLOW}停止前端服务...${NC}"
            docker-compose stop frontend
            echo -e "${YELLOW}重建前端镜像...${NC}"
            docker-compose build --no-cache frontend
            echo -e "${GREEN}启动前端服务...${NC}"
            docker-compose up -d frontend
            ;;
        4)
            echo -e "${YELLOW}停止所有服务...${NC}"
            docker-compose down
            echo -e "${YELLOW}清理旧镜像...${NC}"
            docker-compose build --no-cache
            echo -e "${YELLOW}清理未使用的镜像...${NC}"
            docker image prune -f
            echo -e "${GREEN}启动所有服务...${NC}"
            docker-compose up -d
            ;;
        *)
            echo -e "${RED}无效选择${NC}"
            return
            ;;
    esac
    
    echo -e "${GREEN}${CHECKMARK} 重建完成${NC}"
    echo ""
    show_services_status
}

# 主程序
main() {
    check_requirements
    
    # 如果没有参数，显示交互式菜单
    if [ $# -eq 0 ]; then
        while true; do
            show_menu
            read -p "请选择 (0-13): " choice
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
                10)
                    rebuild_services
                    ;;
                11)
                    start_deployment
                    ;;
                12)
                    start_proxy
                    ;;
                13)
                    clean_environment
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
            "deployment"|"deploy")
                start_deployment
                ;;
            "proxy")
                start_proxy
                ;;
            "status")
                show_services_status
                ;;
            "stop")
                stop_all
                ;;
            "clean")
                clean_environment
                ;;
            "logs")
                local compose_cmd="docker-compose"
                if [ -n "$COMPOSE_FILE" ] && [ "$COMPOSE_FILE" != "docker-compose.yml" ]; then
                    compose_cmd="docker-compose -f $COMPOSE_FILE"
                fi
                eval "$compose_cmd logs -f"
                ;;
            "restart")
                local compose_cmd="docker-compose"
                if [ -n "$COMPOSE_FILE" ] && [ "$COMPOSE_FILE" != "docker-compose.yml" ]; then
                    compose_cmd="docker-compose -f $COMPOSE_FILE"
                fi
                eval "$compose_cmd restart"
                show_services_status
                ;;
            "rebuild")
                rebuild_services
                ;;
            *)
                echo "用法: $0 [选项]"
                echo ""
                echo "基础选项:"
                echo "  full, all       - 启动完整开发环境"
                echo "  basic, base     - 启动基础服务"
                echo "  backend, api    - 启动后端服务"
                echo "  frontend, ui    - 启动前端服务"
                echo "  tools          - 启动开发工具"
                echo ""
                echo "部署选项:"
                echo "  deployment, deploy - 部署环境启动 (自动配置IP)"
                echo "  proxy             - 代理环境启动 (企业网络)"
                echo ""
                echo "管理选项:"
                echo "  status         - 查看服务状态"
                echo "  stop           - 停止所有服务"
                echo "  logs           - 查看服务日志"
                echo "  restart        - 重启服务"
                echo "  rebuild        - 重建并重启"
                echo "  clean          - 清理环境数据"
                echo ""
                echo "或运行不带参数进入交互模式"
                ;;
        esac
    fi
}

# 捕获Ctrl+C
trap 'echo -e "\n${YELLOW}操作已取消${NC}"; exit 0' INT

# 启动主程序
main "$@"