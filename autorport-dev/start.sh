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

# 获取Docker Compose命令
get_docker_compose_cmd() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
        echo "docker compose"
    else
        echo ""
    fi
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

# 交互式环境配置
configure_env_interactive() {
    local detected_ip=$1
    echo -e "${CYAN}${GEAR} 交互式环境配置${NC}"
    echo ""
    
    # IP地址配置
    echo -e "${YELLOW}1. 服务器IP配置${NC}"
    echo -e "自动检测到的IP: ${GREEN}$detected_ip${NC}"
    read -p "是否使用此IP？(Y/n): " use_detected_ip
    
    local server_ip="$detected_ip"
    if [[ "$use_detected_ip" =~ ^[Nn]$ ]]; then
        read -p "请输入服务器IP地址: " server_ip
        if [ -z "$server_ip" ]; then
            server_ip="$detected_ip"
        fi
    fi
    
    # 数据库配置
    echo ""
    echo -e "${YELLOW}2. 数据库配置${NC}"
    read -p "数据库密码 (默认: postgres123): " db_password
    db_password=${db_password:-postgres123}
    
    # 管理员配置
    echo ""
    echo -e "${YELLOW}3. 管理员账户配置${NC}"
    read -p "管理员用户名 (默认: admin): " admin_user
    admin_user=${admin_user:-admin}
    
    read -p "管理员邮箱 (默认: admin@autoreportai.com): " admin_email
    admin_email=${admin_email:-admin@autoreportai.com}
    
    read -p "管理员密码 (默认: password): " admin_password
    admin_password=${admin_password:-password}
    
    # 应用配置到.env文件
    echo ""
    echo -e "${YELLOW}应用配置...${NC}"
    
    # 更新IP配置
    if [ "$server_ip" != "localhost" ]; then
        sed -i.bak "s|SERVER_IP=.*|SERVER_IP=$server_ip|g" .env
        rm -f .env.bak
    fi
    
    # 更新数据库密码
    sed -i.bak "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$db_password|g" .env
    sed -i.bak "s|postgres123|$db_password|g" .env
    rm -f .env.bak
    
    # 更新管理员配置
    sed -i.bak "s|FIRST_SUPERUSER=.*|FIRST_SUPERUSER=$admin_user|g" .env
    sed -i.bak "s|FIRST_SUPERUSER_EMAIL=.*|FIRST_SUPERUSER_EMAIL=$admin_email|g" .env
    sed -i.bak "s|FIRST_SUPERUSER_PASSWORD=.*|FIRST_SUPERUSER_PASSWORD=$admin_password|g" .env
    rm -f .env.bak
    
    echo -e "${GREEN}${CHECKMARK} 配置已应用${NC}"
    echo ""
}

# 自动配置环境文件
setup_env() {
    local env_mode=$1
    local interactive=${2:-false}
    local compose_file=""
    local env_example=""
    local local_ip=$(get_local_ip)
    
    echo -e "${YELLOW}${GEAR} 配置环境 ($env_mode)${NC}"
    echo -e "检测到本机IP: ${GREEN}$local_ip${NC}"
    echo ""
    
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
    
    # 检查是否已存在.env文件
    if [ -f ".env" ]; then
        echo -e "${YELLOW}发现现有的 .env 文件${NC}"
        if [ "$interactive" = "true" ]; then
            read -p "是否覆盖现有的 .env 文件？(y/N): " overwrite_env
            if [[ ! "$overwrite_env" =~ ^[Yy]$ ]]; then
                echo -e "${CYAN}使用现有的 .env 文件${NC}"
                export COMPOSE_FILE="$compose_file"
                return 0
            fi
        else
            echo -e "${YELLOW}覆盖现有的 .env 文件...${NC}"
        fi
    fi
    
    # 创建.env文件
    echo -e "${YELLOW}基于 $env_example 创建 .env 文件...${NC}"
    cp "$env_example" .env
    
    # 交互式配置（如果启用）
    if [ "$interactive" = "true" ]; then
        configure_env_interactive "$local_ip"
    fi
    
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
        local http_proxy_url="${http_proxy:-$HTTP_PROXY}"
        local https_proxy_url="${https_proxy:-$HTTPS_PROXY:-$http_proxy_url}"
        
        if [ -n "$http_proxy_url" ]; then
            echo -e "${GREEN}检测到HTTP代理: $http_proxy_url${NC}"
            sed -i.bak "s|BUILD_HTTP_PROXY=.*|BUILD_HTTP_PROXY=$http_proxy_url|g" .env
            rm -f .env.bak
        fi
        
        if [ -n "$https_proxy_url" ]; then
            echo -e "${GREEN}检测到HTTPS代理: $https_proxy_url${NC}"
            sed -i.bak "s|BUILD_HTTPS_PROXY=.*|BUILD_HTTPS_PROXY=$https_proxy_url|g" .env
            rm -f .env.bak
        fi
        
        if [ -z "$http_proxy_url" ] && [ -z "$https_proxy_url" ]; then
            echo -e "${YELLOW}未检测到代理设置，将使用配置文件中的默认值${NC}"
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
    echo -e "  ${GREEN}14)${NC} ${GEAR} 交互式配置启动 (自定义配置)"
    echo ""
    echo -e "${PACKAGE} 配置管理:"
    echo -e "  ${GREEN}15)${NC} ${GEAR} 配置环境文件 (.env)"
    echo -e "  ${GREEN}16)${NC} ${GEAR} 查看当前配置"
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
    local compose_cmd=$(get_docker_compose_cmd)
    if [ -z "$compose_cmd" ]; then
        echo -e "${RED}${CROSS} Docker Compose 未找到${NC}"
        return 1
    fi
    
    if [ -n "$COMPOSE_FILE" ] && [ "$COMPOSE_FILE" != "docker-compose.yml" ]; then
        eval "$compose_cmd -f $COMPOSE_FILE up -d"
    else
        eval "$compose_cmd up -d"
    fi
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
    local compose_cmd=$(get_docker_compose_cmd)
    if [ -z "$compose_cmd" ]; then
        echo -e "${RED}${CROSS} Docker Compose 未找到${NC}"
        return 1
    fi
    eval "$compose_cmd up -d"
    
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

# 交互式配置启动
start_interactive() {
    echo -e "${GREEN}${GEAR} 交互式配置启动${NC}"
    echo ""
    
    # 选择环境模式
    echo -e "${CYAN}选择环境模式:${NC}"
    echo "1) 标准部署环境"
    echo "2) 代理环境 (企业网络)"
    echo ""
    read -p "请选择 (1-2): " env_mode_choice
    
    local env_mode=""
    case $env_mode_choice in
        1) env_mode="deployment" ;;
        2) env_mode="proxy" ;;
        *) 
            echo -e "${RED}无效选择${NC}"
            return 1
            ;;
    esac
    
    # 检查代理环境（如果选择了代理模式）
    if [ "$env_mode" = "proxy" ]; then
        if [ -z "$http_proxy" ] && [ -z "$HTTP_PROXY" ]; then
            echo -e "${YELLOW}⚠️  未检测到代理设置${NC}"
            echo -e "${CYAN}如果需要代理，请先设置环境变量：${NC}"
            echo -e "  export http_proxy=http://your-proxy:port"
            echo -e "  export https_proxy=http://your-proxy:port"
            echo ""
        fi
    fi
    
    # 交互式环境配置
    setup_env "$env_mode" "true"
    if [ $? -ne 0 ]; then
        echo -e "${RED}${CROSS} 环境配置失败${NC}"
        return 1
    fi
    
    # 确保目录存在
    ensure_directories
    
    # 启动服务
    echo -e "${GREEN}启动所有服务...${NC}"
    local compose_cmd=$(get_docker_compose_cmd)
    if [ -z "$compose_cmd" ]; then
        echo -e "${RED}${CROSS} Docker Compose 未找到${NC}"
        return 1
    fi
    
    if [ "$env_mode" = "proxy" ]; then
        eval "$compose_cmd -f docker-compose.proxy.yml up -d"
    else
        eval "$compose_cmd up -d"
    fi
    
    # 显示状态
    show_services_status
    
    echo -e "${CYAN}交互式配置启动完成！${NC}"
}

# 配置环境文件
configure_env_only() {
    echo -e "${GREEN}${GEAR} 配置环境文件${NC}"
    echo ""
    
    # 选择环境模式
    echo -e "${CYAN}选择环境模式:${NC}"
    echo "1) 标准部署环境 (.env.example)"
    echo "2) 代理环境 (.env.proxy.example)"
    echo ""
    read -p "请选择 (1-2): " env_mode_choice
    
    local env_mode=""
    case $env_mode_choice in
        1) env_mode="deployment" ;;
        2) env_mode="proxy" ;;
        *) 
            echo -e "${RED}无效选择${NC}"
            return 1
            ;;
    esac
    
    # 只进行环境配置，不启动服务
    setup_env "$env_mode" "true"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}${CHECKMARK} 环境配置完成，可以运行启动命令启动服务${NC}"
    fi
}

# 查看当前配置
show_current_config() {
    echo -e "${CYAN}${GEAR} 当前环境配置${NC}"
    echo ""
    
    if [ ! -f ".env" ]; then
        echo -e "${RED}未找到 .env 文件${NC}"
        echo -e "${YELLOW}请先运行配置选项创建环境文件${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}基础配置:${NC}"
    echo -e "  • 项目名: $(grep "PROJECT_NAME=" .env 2>/dev/null | cut -d'=' -f2 || echo "N/A")"
    echo -e "  • 环境模式: $(grep "NODE_ENV=" .env 2>/dev/null | cut -d'=' -f2 || echo "N/A")"
    echo -e "  • 服务器IP: $(grep "SERVER_IP=" .env 2>/dev/null | cut -d'=' -f2 || echo "N/A")"
    echo -e "  • 前端端口: $(grep "FRONTEND_PORT=" .env 2>/dev/null | cut -d'=' -f2 || echo "N/A")"
    echo -e "  • 后端端口: $(grep "PORT=" .env 2>/dev/null | cut -d'=' -f2 || echo "N/A")"
    echo ""
    
    echo -e "${YELLOW}数据库配置:${NC}"
    echo -e "  • 数据库名: $(grep "POSTGRES_DB=" .env 2>/dev/null | cut -d'=' -f2 || echo "N/A")"
    echo -e "  • 数据库用户: $(grep "POSTGRES_USER=" .env 2>/dev/null | cut -d'=' -f2 || echo "N/A")"
    echo ""
    
    echo -e "${YELLOW}管理员配置:${NC}"
    echo -e "  • 用户名: $(grep "FIRST_SUPERUSER=" .env 2>/dev/null | cut -d'=' -f2 || echo "N/A")"
    echo -e "  • 邮箱: $(grep "FIRST_SUPERUSER_EMAIL=" .env 2>/dev/null | cut -d'=' -f2 || echo "N/A")"
    echo ""
}

# 代理环境启动 (企业网络)
start_proxy() {
    echo -e "${GREEN}${ROCKET} 代理环境启动 (企业网络)...${NC}"
    
    # 检查代理环境
    local has_proxy=false
    if [ -n "$http_proxy" ] || [ -n "$HTTP_PROXY" ] || [ -n "$https_proxy" ] || [ -n "$HTTPS_PROXY" ]; then
        has_proxy=true
        echo -e "${GREEN}检测到代理配置:${NC}"
        [ -n "$http_proxy" ] && echo -e "  • http_proxy: $http_proxy"
        [ -n "$HTTP_PROXY" ] && echo -e "  • HTTP_PROXY: $HTTP_PROXY"
        [ -n "$https_proxy" ] && echo -e "  • https_proxy: $https_proxy"
        [ -n "$HTTPS_PROXY" ] && echo -e "  • HTTPS_PROXY: $HTTPS_PROXY"
    else
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
    local compose_cmd=$(get_docker_compose_cmd)
    if [ -z "$compose_cmd" ]; then
        echo -e "${RED}${CROSS} Docker Compose 未找到${NC}"
        return 1
    fi
    eval "$compose_cmd -f docker-compose.proxy.yml up -d"
    
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
    local compose_cmd=$(get_docker_compose_cmd)
    if [ -z "$compose_cmd" ]; then
        echo -e "${RED}${CROSS} Docker Compose 未找到${NC}"
        return 1
    fi
    
    if [ -n "$COMPOSE_FILE" ] && [ "$COMPOSE_FILE" != "docker-compose.yml" ]; then
        eval "$compose_cmd -f $COMPOSE_FILE up -d db redis minio"
    else
        eval "$compose_cmd up -d db redis minio"
    fi
    show_services_status
}

# 启动后端服务
start_backend() {
    echo -e "${GREEN}${GEAR} 启动后端服务...${NC}"
    local compose_cmd=$(get_docker_compose_cmd)
    if [ -z "$compose_cmd" ]; then
        echo -e "${RED}${CROSS} Docker Compose 未找到${NC}"
        return 1
    fi
    
    if [ -n "$COMPOSE_FILE" ] && [ "$COMPOSE_FILE" != "docker-compose.yml" ]; then
        eval "$compose_cmd -f $COMPOSE_FILE up -d db redis minio backend celery-worker celery-beat"
    else
        eval "$compose_cmd up -d db redis minio backend celery-worker celery-beat"
    fi
    show_services_status
}

# 启动前端服务
start_frontend() {
    echo -e "${GREEN}${PAINT} 启动前端服务...${NC}"
    local compose_cmd=$(get_docker_compose_cmd)
    if [ -z "$compose_cmd" ]; then
        echo -e "${RED}${CROSS} Docker Compose 未找到${NC}"
        return 1
    fi
    
    if [ -n "$COMPOSE_FILE" ] && [ "$COMPOSE_FILE" != "docker-compose.yml" ]; then
        eval "$compose_cmd -f $COMPOSE_FILE up -d frontend"
    else
        eval "$compose_cmd up -d frontend"
    fi
    show_services_status
}

# 启动开发工具
start_tools() {
    echo -e "${GREEN}${GEAR} 启动开发工具...${NC}"
    local compose_cmd=$(get_docker_compose_cmd)
    if [ -z "$compose_cmd" ]; then
        echo -e "${RED}${CROSS} Docker Compose 未找到${NC}"
        return 1
    fi
    
    if [ -n "$COMPOSE_FILE" ] && [ "$COMPOSE_FILE" != "docker-compose.yml" ]; then
        eval "$compose_cmd -f $COMPOSE_FILE --profile tools up -d"
    else
        eval "$compose_cmd --profile tools up -d"
    fi
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
    local compose_cmd=$(get_docker_compose_cmd)
    if [ -n "$compose_cmd" ]; then
        eval "$compose_cmd down 2>/dev/null || true"
        eval "$compose_cmd -f docker-compose.proxy.yml down 2>/dev/null || true"
        eval "$compose_cmd --profile tools down 2>/dev/null || true"
    fi
    
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
    local compose_cmd=$(get_docker_compose_cmd)
    if [ -z "$compose_cmd" ]; then
        echo -e "${RED}${CROSS} Docker Compose 未找到${NC}"
        return 1
    fi
    
    if [ -n "$COMPOSE_FILE" ] && [ "$COMPOSE_FILE" != "docker-compose.yml" ]; then
        eval "$compose_cmd -f $COMPOSE_FILE ps"
    else
        eval "$compose_cmd ps"
    fi
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
    
    local compose_cmd=$(get_docker_compose_cmd)
    if [ -z "$compose_cmd" ]; then
        echo -e "${RED}${CROSS} Docker Compose 未找到${NC}"
        return 1
    fi
    
    # 停止标准配置
    eval "$compose_cmd down 2>/dev/null || true"
    eval "$compose_cmd --profile tools down 2>/dev/null || true"
    
    # 停止代理配置
    eval "$compose_cmd -f docker-compose.proxy.yml down 2>/dev/null || true"
    
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
    
    local compose_cmd=$(get_docker_compose_cmd)
    if [ -z "$compose_cmd" ]; then
        echo -e "${RED}${CROSS} Docker Compose 未找到${NC}"
        return 1
    fi
    
    # 确定使用的compose文件
    local compose_file_arg=""
    if [ -n "$COMPOSE_FILE" ] && [ "$COMPOSE_FILE" != "docker-compose.yml" ]; then
        compose_file_arg="-f $COMPOSE_FILE"
    fi
    
    case $log_choice in
        1) eval "$compose_cmd $compose_file_arg logs -f" ;;
        2) eval "$compose_cmd $compose_file_arg logs -f backend" ;;
        3) eval "$compose_cmd $compose_file_arg logs -f frontend" ;;
        4) eval "$compose_cmd $compose_file_arg logs -f db" ;;
        5) eval "$compose_cmd $compose_file_arg logs -f redis" ;;
        6) eval "$compose_cmd $compose_file_arg logs -f celery-worker" ;;
        7) eval "$compose_cmd $compose_file_arg logs -f celery-beat" ;;
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
    
    local compose_cmd=$(get_docker_compose_cmd)
    if [ -z "$compose_cmd" ]; then
        echo -e "${RED}${CROSS} Docker Compose 未找到${NC}"
        return 1
    fi
    
    # 确定使用的compose文件
    local compose_file_arg=""
    if [ -n "$COMPOSE_FILE" ] && [ "$COMPOSE_FILE" != "docker-compose.yml" ]; then
        compose_file_arg="-f $COMPOSE_FILE"
    fi
    
    case $restart_choice in
        1) eval "$compose_cmd $compose_file_arg restart" ;;
        2) eval "$compose_cmd $compose_file_arg restart backend celery-worker celery-beat" ;;
        3) eval "$compose_cmd $compose_file_arg restart frontend" ;;
        4) eval "$compose_cmd $compose_file_arg restart db redis minio" ;;
        *) echo "无效选择" ;;
    esac
    show_services_status
}

# 重建并重启服务
rebuild_services() {
    echo -e "${YELLOW}${PACKAGE} 重建并重启服务 (代码更新后)${NC}"
    echo -e "${CYAN}选择要重建的服务:${NC}"
    echo "1) 重建所有服务 (完整重建)"
    echo "2) 重建后端服务 (Backend + Worker)"
    echo "3) 重建前端服务 (Next.js)"
    echo "4) 快速重建后端 (推荐，使用缓存)"
    echo ""
    read -p "请选择 (1-4): " rebuild_choice

    local compose_cmd=$(get_docker_compose_cmd)
    if [ -z "$compose_cmd" ]; then
        echo -e "${RED}${CROSS} Docker Compose 未找到${NC}"
        return 1
    fi

    # 确定使用的compose文件
    local compose_file_arg=""
    if [ -n "$COMPOSE_FILE" ] && [ "$COMPOSE_FILE" != "docker-compose.yml" ]; then
        compose_file_arg="-f $COMPOSE_FILE"
    fi

    case $rebuild_choice in
        1)
            echo -e "${YELLOW}重建所有服务 (使用 --build --force-recreate)...${NC}"
            eval "$compose_cmd $compose_file_arg up -d --build --force-recreate"
            ;;
        2)
            echo -e "${YELLOW}重建后端服务 (无缓存)...${NC}"
            echo -e "${CYAN}步骤 1/4: 停止服务${NC}"
            eval "$compose_cmd $compose_file_arg stop backend celery-worker"
            echo -e "${CYAN}步骤 2/4: 删除容器${NC}"
            eval "$compose_cmd $compose_file_arg rm -f backend celery-worker"
            echo -e "${CYAN}步骤 3/4: 重建镜像 (--no-cache)${NC}"
            eval "$compose_cmd $compose_file_arg build --no-cache backend celery-worker"
            echo -e "${CYAN}步骤 4/4: 启动服务${NC}"
            eval "$compose_cmd $compose_file_arg up -d backend celery-worker"
            ;;
        3)
            echo -e "${YELLOW}重建前端服务 (使用 --build --force-recreate)...${NC}"
            eval "$compose_cmd $compose_file_arg up -d --build --force-recreate frontend"
            ;;
        4)
            echo -e "${YELLOW}快速重建后端服务 (使用 --build --force-recreate)...${NC}"
            echo -e "${CYAN}这将使用Docker缓存加速构建，适合代码小改动${NC}"
            eval "$compose_cmd $compose_file_arg up -d --build --force-recreate backend celery-worker"
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
            read -p "请选择 (0-16): " choice
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
                14)
                    start_interactive
                    ;;
                15)
                    configure_env_only
                    ;;
                16)
                    show_current_config
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
            "interactive"|"config")
                start_interactive
                ;;
            "configure"|"setup")
                configure_env_only
                ;;
            "show-config"|"info")
                show_current_config
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
                local compose_cmd=$(get_docker_compose_cmd)
                if [ -z "$compose_cmd" ]; then
                    echo -e "${RED}${CROSS} Docker Compose 未找到${NC}"
                    exit 1
                fi
                
                if [ -n "$COMPOSE_FILE" ] && [ "$COMPOSE_FILE" != "docker-compose.yml" ]; then
                    eval "$compose_cmd -f $COMPOSE_FILE logs -f"
                else
                    eval "$compose_cmd logs -f"
                fi
                ;;
            "restart")
                local compose_cmd=$(get_docker_compose_cmd)
                if [ -z "$compose_cmd" ]; then
                    echo -e "${RED}${CROSS} Docker Compose 未找到${NC}"
                    exit 1
                fi
                
                if [ -n "$COMPOSE_FILE" ] && [ "$COMPOSE_FILE" != "docker-compose.yml" ]; then
                    eval "$compose_cmd -f $COMPOSE_FILE restart"
                else
                    eval "$compose_cmd restart"
                fi
                show_services_status
                ;;
            "rebuild")
                rebuild_services
                ;;
            *)
                echo "用法: $0 [选项]"
                echo ""
                echo "基础选项:"
                echo "  full, all         - 启动完整开发环境"
                echo "  basic, base       - 启动基础服务"
                echo "  backend, api      - 启动后端服务"
                echo "  frontend, ui      - 启动前端服务"
                echo "  tools            - 启动开发工具"
                echo ""
                echo "部署选项:"
                echo "  deployment, deploy - 部署环境启动 (自动配置IP)"
                echo "  proxy             - 代理环境启动 (企业网络)"
                echo "  interactive, config - 交互式配置启动"
                echo ""
                echo "配置选项:"
                echo "  configure, setup  - 仅配置环境文件 (.env)"
                echo "  show-config, info - 查看当前配置"
                echo ""
                echo "管理选项:"
                echo "  status           - 查看服务状态"
                echo "  stop             - 停止所有服务"
                echo "  logs             - 查看服务日志"
                echo "  restart          - 重启服务"
                echo "  rebuild          - 重建并重启"
                echo "  clean            - 清理环境数据"
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