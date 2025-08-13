#!/bin/bash

# AutoReportAI Docker 停止脚本
# 使用方法: ./stop.sh [--clean]
# --clean 选项会删除所有数据卷（谨慎使用）

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

# 停止服务
stop_services() {
    print_info "正在停止 AutoReportAI 服务..."
    
    if docker-compose ps -q | grep -q .; then
        docker-compose down
        print_success "服务已停止"
    else
        print_info "没有运行中的服务"
    fi
}

# 清理数据
clean_data() {
    print_warning "⚠️  警告：即将删除所有数据卷！"
    print_warning "这将删除数据库、上传文件、报告等所有数据！"
    echo ""
    read -p "确定要继续吗？请输入 'yes' 确认: " confirmation
    
    if [ "$confirmation" = "yes" ]; then
        print_info "正在清理数据卷..."
        docker-compose down -v
        
        # 清理孤立的卷
        print_info "清理孤立的卷..."
        docker volume prune -f
        
        print_success "数据清理完成"
    else
        print_info "数据清理已取消"
    fi
}

# 显示状态
show_status() {
    print_info "Docker 容器状态:"
    docker-compose ps
    
    echo ""
    print_info "Docker 卷状态:"
    docker volume ls | grep autoreport || echo "没有找到相关数据卷"
}

# 主函数
main() {
    print_info "AutoReportAI Docker 停止脚本"
    echo ""
    
    # 解析参数
    local clean_data=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --clean)
                clean_data=true
                shift
                ;;
            -h|--help)
                echo "使用方法: $0 [选项]"
                echo ""
                echo "选项:"
                echo "  --clean    停止服务并删除所有数据卷（谨慎使用）"
                echo "  -h, --help 显示帮助信息"
                exit 0
                ;;
            *)
                print_error "未知选项: $1"
                echo "使用 $0 --help 查看帮助信息"
                exit 1
                ;;
        esac
    done
    
    if [ "$clean_data" = true ]; then
        clean_data
    else
        stop_services
    fi
    
    echo ""
    show_status
    
    echo ""
    print_info "其他有用的命令:"
    echo "  重新启动: ./start.sh"
    echo "  查看日志: docker-compose logs"
    echo "  清理系统: docker system prune"
}

# 脚本入口
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi