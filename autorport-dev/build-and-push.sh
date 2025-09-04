#!/bin/bash
# ==========================================
# AutoReportAI 多架构镜像构建和推送脚本
# 支持 amd64/arm64 架构，自动推送到 Docker Hub
# ==========================================

set -e  # 遇到错误立即退出

# ==========================================
# 颜色和格式定义
# ==========================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# ==========================================
# 配置变量
# ==========================================
DOCKER_HUB_USERNAME="${DOCKER_HUB_USERNAME:-}"
PROJECT_NAME="autoreportai"
VERSION="${VERSION:-latest}"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
PLATFORMS="linux/amd64,linux/arm64"
PUSH_TO_REGISTRY="${PUSH_TO_REGISTRY:-true}"

# 镜像配置 - 使用数组而非关联数组以兼容更多bash版本
SERVICES=(backend frontend)
BACKEND_PATH="../backend"
FRONTEND_PATH="../frontend"

# ==========================================
# 辅助函数
# ==========================================
print_header() {
    echo -e "${CYAN}${BOLD}"
    echo "========================================"
    echo "  🚀 AutoReportAI 多架构镜像构建工具"
    echo "========================================"
    echo -e "${NC}"
}

print_section() {
    echo -e "${BLUE}${BOLD}📦 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

print_info() {
    echo -e "${MAGENTA}ℹ️  $1${NC}"
}

# ==========================================
# 环境检查函数
# ==========================================
check_requirements() {
    print_section "检查构建环境"
    
    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装或不在 PATH 中"
    fi
    print_success "Docker 已安装: $(docker --version | cut -d' ' -f3)"
    
    # 检查 Docker Buildx
    if ! docker buildx version &> /dev/null; then
        print_error "Docker Buildx 不可用，请升级 Docker"
    fi
    print_success "Docker Buildx 可用: $(docker buildx version | head -1 | cut -d' ' -f2)"
    
    # 检查是否登录 Docker Hub
    if [ "$PUSH_TO_REGISTRY" = "true" ]; then
        if [ -z "$DOCKER_HUB_USERNAME" ]; then
            print_warning "未设置 DOCKER_HUB_USERNAME 环境变量"
            read -p "请输入 Docker Hub 用户名: " DOCKER_HUB_USERNAME
            if [ -z "$DOCKER_HUB_USERNAME" ]; then
                print_error "Docker Hub 用户名不能为空"
            fi
        fi
        
        # 验证 Docker Hub 登录状态
        if ! docker info | grep -q "Username: $DOCKER_HUB_USERNAME"; then
            print_warning "未登录到 Docker Hub，正在登录..."
            docker login
        fi
        print_success "Docker Hub 登录状态正常: $DOCKER_HUB_USERNAME"
    fi
    
    # 检查 Git 仓库
    if ! git status &> /dev/null; then
        print_warning "不在 Git 仓库中，某些标签信息可能不可用"
    else
        print_success "Git 仓库状态正常，提交: $GIT_COMMIT"
    fi
}

# ==========================================
# Buildx Builder 设置
# ==========================================
setup_builder() {
    print_section "设置多架构构建器"
    
    # 创建或使用现有的 builder
    BUILDER_NAME="autoreportai-builder"
    
    if ! docker buildx ls | grep -q "$BUILDER_NAME"; then
        print_info "创建新的多架构构建器: $BUILDER_NAME"
        docker buildx create \
            --name "$BUILDER_NAME" \
            --driver docker-container \
            --use \
            --bootstrap
    else
        print_info "使用现有构建器: $BUILDER_NAME"
        docker buildx use "$BUILDER_NAME"
    fi
    
    # 检查构建器支持的平台
    print_info "构建器支持的平台:"
    docker buildx inspect --bootstrap | grep "Platforms:" || true
    
    print_success "多架构构建器设置完成"
}

# ==========================================
# 构建单个镜像
# ==========================================
build_image() {
    local service_name=$1
    local context_path=$2
    local image_tag="$DOCKER_HUB_USERNAME/$PROJECT_NAME-$service_name:$VERSION"
    local latest_tag="$DOCKER_HUB_USERNAME/$PROJECT_NAME-$service_name:latest"
    
    print_section "构建 $service_name 镜像"
    print_info "镜像标签: $image_tag"
    print_info "上下文路径: $context_path"
    print_info "目标平台: $PLATFORMS"
    
    # 构建参数
    local build_args=(
        "--platform" "$PLATFORMS"
        "--tag" "$image_tag"
        "--tag" "$latest_tag"
        "--label" "org.opencontainers.image.created=$BUILD_DATE"
        "--label" "org.opencontainers.image.version=$VERSION"
        "--label" "org.opencontainers.image.revision=$GIT_COMMIT"
        "--label" "org.opencontainers.image.source=https://github.com/$DOCKER_HUB_USERNAME/$PROJECT_NAME"
        "--label" "org.opencontainers.image.title=AutoReportAI-$service_name"
        "--label" "org.opencontainers.image.description=AutoReportAI $service_name service with React Agent architecture"
        "--label" "autoreportai.service=$service_name"
        "--label" "autoreportai.architecture=react_agent"
        "--label" "autoreportai.build.date=$BUILD_DATE"
        "--label" "autoreportai.build.commit=$GIT_COMMIT"
    )
    
    # 根据服务类型设置构建目标
    case "$service_name" in
        "backend")
            build_args+=("--target" "production")
            ;;
        "frontend")
            build_args+=("--target" "production")
            build_args+=("--build-arg" "NEXT_PUBLIC_API_URL=\$NEXT_PUBLIC_API_URL")
            build_args+=("--build-arg" "NEXT_PUBLIC_WS_URL=\$NEXT_PUBLIC_WS_URL")
            ;;
    esac
    
    # 是否推送到注册表
    if [ "$PUSH_TO_REGISTRY" = "true" ]; then
        build_args+=("--push")
        print_info "构建完成后将推送到 Docker Hub"
    else
        # 多架构镜像无法加载到本地，只能推送或缓存
        if [[ "$PLATFORMS" == *","* ]]; then
            print_warning "多架构构建无法加载到本地，将使用缓存模式"
            # 不添加 --push 或 --load，这样会构建并缓存
        else
            build_args+=("--load")
            print_info "单架构构建，将加载到本地"
        fi
    fi
    
    # 执行构建
    print_info "开始构建 $service_name..."
    if docker buildx build "${build_args[@]}" "$context_path"; then
        print_success "$service_name 镜像构建完成"
        
        if [ "$PUSH_TO_REGISTRY" = "true" ]; then
            print_success "✅ $service_name 镜像已推送到: $image_tag"
        else
            print_success "✅ $service_name 镜像已加载到本地: $image_tag"
        fi
    else
        print_error "$service_name 镜像构建失败"
    fi
}

# ==========================================
# 获取服务路径
# ==========================================
get_service_path() {
    local service_name=$1
    case "$service_name" in
        "backend")
            echo "$BACKEND_PATH"
            ;;
        "frontend")
            echo "$FRONTEND_PATH"
            ;;
        *)
            print_error "未知服务: $service_name"
            ;;
    esac
}

# ==========================================
# 构建所有镜像
# ==========================================
build_all_images() {
    print_section "开始构建所有镜像"
    
    local start_time=$(date +%s)
    
    for service in "${SERVICES[@]}"; do
        local service_path=$(get_service_path "$service")
        build_image "$service" "$service_path"
        echo
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    print_success "所有镜像构建完成！总用时: ${minutes}分${seconds}秒"
}

# ==========================================
# 显示镜像信息
# ==========================================
show_image_info() {
    if [ "$PUSH_TO_REGISTRY" = "true" ]; then
        print_section "镜像信息 (Docker Hub)"
        for service in "${SERVICES[@]}"; do
            echo -e "${CYAN}$service:${NC}"
            echo "  📦 docker pull $DOCKER_HUB_USERNAME/$PROJECT_NAME-$service:$VERSION"
            echo "  📦 docker pull $DOCKER_HUB_USERNAME/$PROJECT_NAME-$service:latest"
        done
    else
        print_section "本地镜像信息"
        for service in "${SERVICES[@]}"; do
            echo -e "${CYAN}$service:${NC}"
            echo "  📦 $DOCKER_HUB_USERNAME/$PROJECT_NAME-$service:$VERSION"
            echo "  📦 $DOCKER_HUB_USERNAME/$PROJECT_NAME-$service:latest"
        done
    fi
    
    echo
    print_section "使用 Docker Compose 运行"
    cat << EOF
修改 docker-compose.yml 中的镜像引用:

services:
  backend:
    image: $DOCKER_HUB_USERNAME/$PROJECT_NAME-backend:$VERSION
    # ... 其他配置
    
  frontend:
    image: $DOCKER_HUB_USERNAME/$PROJECT_NAME-frontend:$VERSION
    # ... 其他配置
EOF
}

# ==========================================
# 清理函数
# ==========================================
cleanup() {
    print_section "清理构建环境"
    
    # 清理构建缓存
    if docker buildx ls | grep -q "autoreportai-builder"; then
        print_info "清理构建器缓存"
        docker buildx prune --builder autoreportai-builder --filter until=24h --force || true
    fi
    
    print_success "清理完成"
}

# ==========================================
# 显示帮助信息
# ==========================================
show_help() {
    cat << EOF
AutoReportAI 多架构镜像构建脚本

用法: $0 [选项] [服务名...]

选项:
  -u, --username USER     设置 Docker Hub 用户名
  -v, --version VERSION   设置镜像版本标签 (默认: latest)
  -p, --platforms PLAT    设置目标平台 (默认: linux/amd64,linux/arm64)
  --no-push              只构建本地镜像，不推送到注册表
  --cleanup              构建后清理缓存
  -h, --help             显示帮助信息

服务名:
  backend     构建后端 API 服务镜像
  frontend    构建前端 UI 服务镜像
  all         构建所有服务镜像 (默认)

环境变量:
  DOCKER_HUB_USERNAME     Docker Hub 用户名
  VERSION                 镜像版本标签
  PUSH_TO_REGISTRY        是否推送到注册表 (true/false)

示例:
  $0                                          # 构建所有镜像并推送
  $0 --username myuser --version v1.0.0      # 指定用户名和版本
  $0 backend frontend                         # 只构建指定服务
  $0 --no-push --cleanup                      # 本地构建并清理
  
  # 使用环境变量
  DOCKER_HUB_USERNAME=myuser VERSION=v1.0.0 $0
EOF
}

# ==========================================
# 主函数
# ==========================================
main() {
    # 解析命令行参数
    local services_to_build=()
    local cleanup_after=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -u|--username)
                DOCKER_HUB_USERNAME="$2"
                shift 2
                ;;
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -p|--platforms)
                PLATFORMS="$2"
                shift 2
                ;;
            --no-push)
                PUSH_TO_REGISTRY="false"
                shift
                ;;
            --cleanup)
                cleanup_after=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            backend|frontend)
                services_to_build+=("$1")
                shift
                ;;
            all)
                services_to_build=()  # 清空，构建所有
                shift
                ;;
            *)
                print_error "未知参数: $1"
                ;;
        esac
    done
    
    # 如果没有指定服务，构建所有服务
    if [ ${#services_to_build[@]} -eq 0 ]; then
        services_to_build=("${SERVICES[@]}")
    fi
    
    # 显示构建信息
    print_header
    print_info "项目: $PROJECT_NAME"
    print_info "版本: $VERSION"
    print_info "平台: $PLATFORMS"
    print_info "用户: ${DOCKER_HUB_USERNAME:-未设置}"
    print_info "推送: $([ "$PUSH_TO_REGISTRY" = "true" ] && echo "是" || echo "否")"
    print_info "服务: ${services_to_build[*]}"
    echo
    
    # 环境检查
    check_requirements
    echo
    
    # 设置构建器
    setup_builder
    echo
    
    # 构建镜像
    local start_time=$(date +%s)
    
    for service in "${services_to_build[@]}"; do
        # 检查服务是否在支持的服务列表中
        local service_found=false
        for supported_service in "${SERVICES[@]}"; do
            if [[ "$service" == "$supported_service" ]]; then
                service_found=true
                break
            fi
        done
        
        if [[ "$service_found" == true ]]; then
            local service_path=$(get_service_path "$service")
            build_image "$service" "$service_path"
            echo
        else
            print_error "未知服务: $service"
        fi
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    print_success "🎉 所有构建任务完成！总用时: ${minutes}分${seconds}秒"
    echo
    
    # 显示镜像信息
    show_image_info
    
    # 清理
    if [ "$cleanup_after" = true ]; then
        echo
        cleanup
    fi
    
    echo
    print_success "🚀 AutoReportAI 多架构镜像构建完成！"
}

# ==========================================
# 脚本入口
# ==========================================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi