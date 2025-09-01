#!/bin/bash
set -e

# AutoReportAI 统一构建脚本
# 支持开发调试和生产部署两种模式

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 默认参数
MODE="dev"
CLEAN=false
VERBOSE=false
NO_CACHE=false

# 帮助信息
show_help() {
    cat << EOF
AutoReportAI Docker 构建脚本

用法: $0 [选项]

选项:
  --mode=MODE        构建模式: dev(开发调试) | prod(生产部署) [默认: dev]
  --clean           清理现有镜像和容器
  --no-cache        不使用Docker构建缓存
  --verbose         详细输出
  -h, --help        显示此帮助信息

示例:
  $0                    # 开发模式构建
  $0 --mode=prod        # 生产模式构建
  $0 --clean --no-cache # 清理并重新构建

环境文件:
  .env                  # 主配置文件（需要手动创建）
  .env.example          # 配置模板
EOF
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode=*)
            MODE="${1#*=}"
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "❌ 未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 验证模式
if [[ "$MODE" != "dev" && "$MODE" != "prod" ]]; then
    echo "❌ 无效的构建模式: $MODE (只支持 dev 或 prod)"
    exit 1
fi

echo "🏗️  AutoReportAI Docker 构建"
echo "=================================="
echo "构建模式: $MODE"
echo "项目根目录: $PROJECT_ROOT"
echo "清理模式: $CLEAN"
echo "无缓存构建: $NO_CACHE"
echo "=================================="

cd "$SCRIPT_DIR"

# 检查环境文件
if [[ ! -f ".env" ]]; then
    echo "⚠️  .env 文件不存在，请复制 .env.example 并配置"
    echo "   cp .env.example .env"
    echo "   编辑 .env 文件中的配置"
    exit 1
fi

# 创建必要的数据目录
echo "📁 创建数据目录..."
mkdir -p data/{backend/{logs,reports,uploads,storage,cache},frontend/public,postgres,redis,celery-beat,minio}

# 清理操作
if [[ "$CLEAN" == "true" ]]; then
    echo "🧹 清理现有容器和镜像..."
    docker-compose down --remove-orphans --volumes || true
    
    # 删除项目相关镜像
    PROJECT_IMAGES=$(docker images --format "table {{.Repository}}" | grep "autoreporait-docker" || true)
    if [[ -n "$PROJECT_IMAGES" ]]; then
        echo "$PROJECT_IMAGES" | xargs -r docker rmi -f
    fi
    
    # 清理构建缓存
    docker builder prune -f
fi

# 构建选项
BUILD_ARGS=()
if [[ "$NO_CACHE" == "true" ]]; then
    BUILD_ARGS+=(--no-cache)
fi

if [[ "$VERBOSE" == "true" ]]; then
    BUILD_ARGS+=(--progress=plain)
fi

# 根据模式选择不同的构建策略
if [[ "$MODE" == "dev" ]]; then
    echo "🔧 开发模式构建..."
    
    # 开发模式：快速构建，启用热重载
    export DOCKERFILE_TARGET=runtime
    export WORKERS=1
    export CELERY_CONCURRENCY=2
    
    echo "  📦 构建后端服务 (开发模式)..."
    docker-compose build "${BUILD_ARGS[@]}" backend
    
    echo "  🎨 构建前端服务 (开发模式)..."
    docker-compose build "${BUILD_ARGS[@]}" frontend
    
    echo "  👷 构建 Celery Worker..."
    docker-compose build "${BUILD_ARGS[@]}" celery-worker

elif [[ "$MODE" == "prod" ]]; then
    echo "🚀 生产模式构建..."
    
    # 生产模式：优化构建，多阶段构建
    export DOCKERFILE_TARGET=production
    export WORKERS=4
    export CELERY_CONCURRENCY=6
    
    echo "  📦 构建后端服务 (生产优化)..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml build "${BUILD_ARGS[@]}" backend
    
    echo "  🎨 构建前端服务 (生产优化)..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml build "${BUILD_ARGS[@]}" frontend
    
    echo "  👷 构建 Celery 服务..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml build "${BUILD_ARGS[@]}" celery-worker celery-beat
    
    # 生产模式可选服务
    echo "  📊 构建监控服务..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml build "${BUILD_ARGS[@]}" flower || true
fi

echo ""
echo "✅ 构建完成！"
echo ""
echo "🎯 下一步操作:"
if [[ "$MODE" == "dev" ]]; then
    echo "  开发启动: ./start.sh --mode=dev"
    echo "  查看日志: docker-compose logs -f"
    echo "  热重载: 代码修改会自动重启服务"
else
    echo "  生产启动: ./start.sh --mode=prod"
    echo "  健康检查: docker-compose ps"
    echo "  监控面板: http://localhost:5555 (Flower)"
fi
echo ""
echo "🌐 服务地址:"
echo "  前端: http://localhost:3000"
echo "  后端API: http://localhost:8000"
echo "  API文档: http://localhost:8000/docs"