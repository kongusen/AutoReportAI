#!/bin/bash
set -e

# AutoReportAI 统一启动脚本  
# 支持开发调试和生产部署两种模式

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 默认参数
MODE="dev"
DETACH=true
SERVICES=""
INIT_DB=false

# 帮助信息
show_help() {
    cat << EOF
AutoReportAI Docker 启动脚本

用法: $0 [选项] [服务名...]

选项:
  --mode=MODE        启动模式: dev(开发调试) | prod(生产部署) [默认: dev]
  --init-db         初始化数据库
  --attach          前台运行 (查看日志)
  -h, --help        显示此帮助信息

服务名 (可选，默认启动所有):
  db                数据库
  redis             缓存
  backend           后端API
  frontend          前端
  celery-worker     任务处理器
  celery-beat       任务调度器
  flower            监控面板

示例:
  $0                           # 开发模式启动所有服务
  $0 --mode=prod               # 生产模式启动
  $0 --mode=dev --attach       # 开发模式前台运行
  $0 --init-db                 # 启动并初始化数据库
  $0 backend frontend          # 只启动指定服务

模式说明:
  dev  - 开发调试: 热重载, 详细日志, 单Worker
  prod - 生产部署: 优化性能, 多Worker, 健康检查
EOF
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode=*)
            MODE="${1#*=}"
            shift
            ;;
        --init-db)
            INIT_DB=true
            shift
            ;;
        --attach)
            DETACH=false
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        -*)
            echo "❌ 未知选项: $1"
            show_help
            exit 1
            ;;
        *)
            SERVICES="$SERVICES $1"
            shift
            ;;
    esac
done

# 验证模式
if [[ "$MODE" != "dev" && "$MODE" != "prod" ]]; then
    echo "❌ 无效的启动模式: $MODE (只支持 dev 或 prod)"
    exit 1
fi

echo "🚀 AutoReportAI Docker 启动"
echo "=================================="
echo "启动模式: $MODE"
echo "初始化数据库: $INIT_DB"
echo "运行模式: $([ "$DETACH" == "true" ] && echo "后台" || echo "前台")"
[[ -n "$SERVICES" ]] && echo "指定服务:$SERVICES"
echo "=================================="

cd "$SCRIPT_DIR"

# 检查环境文件
if [[ ! -f ".env" ]]; then
    echo "⚠️  .env 文件不存在，使用默认配置"
    cp .env.example .env
    echo "✅ 已复制 .env.example 到 .env，请根据需要修改配置"
fi

# 确保数据目录存在
echo "📁 准备数据目录..."
mkdir -p data/{backend/{logs,reports,uploads,storage,cache},frontend/public,postgres,redis,celery-beat,minio}

# 根据模式设置环境变量
if [[ "$MODE" == "dev" ]]; then
    export ENVIRONMENT=development
    export DEBUG=true
    export LOG_LEVEL=DEBUG
    export API_WORKERS=1
    export CELERY_CONCURRENCY=2
    export FLOWER_BASIC_AUTH=""
    COMPOSE_FILES="-f docker-compose.yml"
    
    echo "🔧 开发模式配置："
    echo "  - 热重载启用"
    echo "  - 详细调试日志"
    echo "  - 单 Worker 便于调试"
    
elif [[ "$MODE" == "prod" ]]; then
    export ENVIRONMENT=production  
    export DEBUG=false
    export LOG_LEVEL=INFO
    export API_WORKERS=4
    export CELERY_CONCURRENCY=6
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
    
    echo "🚀 生产模式配置："
    echo "  - 性能优化"
    echo "  - 多 Worker"
    echo "  - 健康检查"
    echo "  - 监控面板"
fi

# 启动核心基础设施
echo "📦 启动基础设施 (数据库 + Redis)..."
docker-compose $COMPOSE_FILES up -d db redis

echo "⏳ 等待基础设施就绪..."
sleep 8

# 数据库初始化
if [[ "$INIT_DB" == "true" ]]; then
    echo "🗄️  初始化数据库..."
    docker-compose $COMPOSE_FILES run --rm backend python scripts/init_db.py
    echo "✅ 数据库初始化完成"
fi

# 启动应用服务
if [[ -n "$SERVICES" ]]; then
    echo "🎯 启动指定服务:$SERVICES"
    if [[ "$DETACH" == "true" ]]; then
        docker-compose $COMPOSE_FILES up -d $SERVICES
    else
        docker-compose $COMPOSE_FILES up $SERVICES
    fi
else
    echo "🎯 启动所有应用服务..."
    
    if [[ "$MODE" == "dev" ]]; then
        # 开发模式：分步启动便于调试
        echo "  🔧 启动后端..."
        docker-compose $COMPOSE_FILES up -d backend
        
        echo "  ⏳ 等待后端就绪..."
        sleep 10
        
        echo "  🎨 启动前端..."
        docker-compose $COMPOSE_FILES up -d frontend
        
        echo "  👷 启动任务处理器..."
        docker-compose $COMPOSE_FILES up -d celery-worker
        
    elif [[ "$MODE" == "prod" ]]; then
        # 生产模式：并行启动所有服务
        PROD_SERVICES="backend frontend celery-worker celery-beat"
        
        if [[ "$DETACH" == "true" ]]; then
            docker-compose $COMPOSE_FILES up -d $PROD_SERVICES
            
            # 启动监控服务
            echo "  📊 启动监控服务..."
            docker-compose $COMPOSE_FILES up -d flower || echo "⚠️  Flower 启动失败（可选服务）"
        else
            docker-compose $COMPOSE_FILES up $PROD_SERVICES
        fi
    fi
fi

# 等待服务启动
if [[ "$DETACH" == "true" ]]; then
    echo "⏳ 等待所有服务启动..."
    sleep 15
    
    echo ""
    echo "📊 服务状态检查:"
    docker-compose $COMPOSE_FILES ps
    
    echo ""
    echo "🏥 健康检查:"
    
    # 检查后端健康状态
    echo -n "  后端API: "
    if curl -sf --max-time 10 http://localhost:8000/api/v1/health >/dev/null 2>&1; then
        echo "✅ 健康"
    else
        echo "❌ 异常"
    fi
    
    # 检查前端
    echo -n "  前端服务: "
    if curl -sf --max-time 10 http://localhost:3000 >/dev/null 2>&1; then
        echo "✅ 健康"
    else
        echo "❌ 异常 (可能还在启动中)"
    fi
    
    # 检查数据库
    echo -n "  数据库: "
    if docker-compose $COMPOSE_FILES exec -T db pg_isready -U postgres >/dev/null 2>&1; then
        echo "✅ 健康"  
    else
        echo "❌ 异常"
    fi
    
    echo ""
    echo "🌐 访问地址:"
    echo "  🎨 前端界面: http://localhost:3000"
    echo "  🔧 后端API:  http://localhost:8000"
    echo "  📚 API文档:  http://localhost:8000/docs"
    
    if [[ "$MODE" == "prod" ]]; then
        echo "  📊 任务监控: http://localhost:5555"
    fi
    
    echo ""
    echo "🔧 常用命令:"
    echo "  查看日志: docker-compose logs -f [服务名]"
    echo "  停止服务: docker-compose down"
    echo "  重启服务: docker-compose restart [服务名]"
    
    if [[ "$MODE" == "dev" ]]; then
        echo "  进入后端: docker-compose exec backend bash"
        echo "  查看后端日志: docker-compose logs -f backend"
    fi
fi

echo ""
echo "✅ AutoReportAI 启动完成！"