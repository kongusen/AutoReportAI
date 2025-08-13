#!/bin/bash

# AutoReportAI Docker 启动脚本
# 使用方法: ./start.sh [mode]
# 模式选项: basic(默认), dev, prod, monitoring

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印彩色消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}[AutoReportAI]${NC} $message"
}

print_info() {
    print_message $BLUE "$1"
}

print_success() {
    print_message $GREEN "$1"
}

print_warning() {
    print_message $YELLOW "$1"
}

print_error() {
    print_message $RED "$1"
}

# 检查 Docker 和 Docker Compose
check_prerequisites() {
    print_info "检查系统依赖..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    print_success "Docker 环境检查通过"
}

# 检查环境变量文件
check_env_file() {
    if [ ! -f .env ]; then
        print_warning "未找到 .env 文件，正在从模板创建..."
        if [ -f .env.template ]; then
            cp .env.template .env
            print_success "已创建 .env 文件"
            print_warning "请编辑 .env 文件中的配置项，特别是密钥和密码！"
            print_info "必须配置的项目："
            echo "  - SECRET_KEY"
            echo "  - ENCRYPTION_KEY" 
            echo "  - POSTGRES_PASSWORD"
            echo "  - OPENAI_API_KEY"
            echo ""
            read -p "是否现在编辑 .env 文件？(y/n): " edit_env
            if [ "$edit_env" = "y" ] || [ "$edit_env" = "Y" ]; then
                ${EDITOR:-nano} .env
            fi
        else
            print_error "未找到 .env.template 文件"
            exit 1
        fi
    else
        print_success "找到 .env 文件"
    fi
}

# 检查端口占用
check_ports() {
    print_info "检查端口占用情况..."
    local ports=(3000 8000 5432 6379)
    local occupied_ports=()
    
    for port in "${ports[@]}"; do
        if lsof -i :$port &> /dev/null; then
            occupied_ports+=($port)
        fi
    done
    
    if [ ${#occupied_ports[@]} -gt 0 ]; then
        print_warning "以下端口已被占用: ${occupied_ports[*]}"
        print_info "你可以在 .env 文件中修改端口配置"
        read -p "是否继续启动？(y/n): " continue_start
        if [ "$continue_start" != "y" ] && [ "$continue_start" != "Y" ]; then
            print_info "启动已取消"
            exit 0
        fi
    fi
}

# 启动服务
start_services() {
    local mode=${1:-basic}
    
    print_info "启动模式: $mode"
    
    case $mode in
        basic)
            print_info "启动基础服务..."
            docker-compose up -d
            ;;
        dev)
            print_info "启动开发环境（包含监控）..."
            docker-compose --profile dev up -d
            ;;
        prod)
            print_info "启动生产环境（包含存储）..."
            docker-compose --profile prod up -d
            ;;
        monitoring)
            print_info "启动监控服务..."
            docker-compose --profile monitoring up -d
            ;;
        *)
            print_error "未知模式: $mode"
            print_info "可用模式: basic, dev, prod, monitoring"
            exit 1
            ;;
    esac
}

# 等待服务启动
wait_for_services() {
    print_info "等待服务启动..."
    
    # 等待后端服务
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:8000/api/v1/health &> /dev/null; then
            print_success "后端服务已启动"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_warning "后端服务启动超时，请检查日志"
        else
            echo -n "."
            sleep 2
        fi
        
        ((attempt++))
    done
    
    echo ""
}

# 显示服务信息
show_service_info() {
    print_success "服务启动完成！"
    echo ""
    print_info "访问地址:"
    echo "  前端应用: http://localhost:3000"
    echo "  后端API:  http://localhost:8000"
    echo "  API文档:  http://localhost:8000/docs"
    
    # 检查特定服务是否启动
    if docker-compose ps | grep -q "flower"; then
        echo "  Flower监控: http://localhost:5555"
    fi
    
    if docker-compose ps | grep -q "minio"; then
        echo "  MinIO控制台: http://localhost:9001"
    fi
    
    echo ""
    print_info "常用命令:"
    echo "  查看日志: docker-compose logs -f"
    echo "  查看状态: docker-compose ps"
    echo "  停止服务: docker-compose down"
    echo ""
}

# 主函数
main() {
    local mode=${1:-basic}
    
    print_info "AutoReportAI Docker 启动脚本"
    echo ""
    
    check_prerequisites
    check_env_file
    check_ports
    start_services $mode
    wait_for_services
    show_service_info
}

# 脚本入口
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi