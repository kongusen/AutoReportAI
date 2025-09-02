#!/bin/bash
# 生产环境部署脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查部署依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    log_success "依赖检查完成"
}

# 检查环境变量文件
check_env_file() {
    log_info "检查环境变量文件..."
    
    if [ ! -f ".env.production" ]; then
        log_error "未找到 .env.production 文件"
        log_info "请复制 .env.production.template 为 .env.production 并配置相应的值"
        exit 1
    fi
    
    # 检查必需的环境变量
    required_vars=(
        "DB_PASSWORD"
        "REDIS_PASSWORD" 
        "JWT_SECRET_KEY"
        "GRAFANA_PASSWORD"
        "ACME_EMAIL"
    )
    
    source .env.production
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ] || [ "${!var}" = "your_secure_${var,,}_here" ] || [ "${!var}" = "your_${var,,}_here" ]; then
            log_error "环境变量 $var 未正确设置"
            exit 1
        fi
    done
    
    log_success "环境变量检查完成"
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    
    mkdir -p logs
    mkdir -p uploads
    mkdir -p config
    mkdir -p docker/postgres
    mkdir -p docker/monitoring
    
    # 设置目录权限
    chmod 755 logs uploads
    
    log_success "目录创建完成"
}

# 生成数据库初始化脚本
generate_db_init() {
    log_info "生成数据库初始化脚本..."
    
    cat > docker/postgres/init.sql << EOF
-- 数据库初始化脚本
-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- 创建数据库用户权限
GRANT ALL PRIVILEGES ON DATABASE autoreport TO postgres;

-- 设置默认权限
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO postgres;
EOF
    
    log_success "数据库初始化脚本生成完成"
}

# 生成Prometheus配置
generate_prometheus_config() {
    log_info "生成Prometheus配置..."
    
    mkdir -p docker/monitoring
    
    cat > docker/monitoring/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'autoreport-app'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'react-agent-services'
    static_configs:
      - targets: 
          - 'app:8000'
          - 'worker:8001'
          - 'beat:8002'
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis:6379']
EOF
    
    log_success "Prometheus配置生成完成"
}

# 构建镜像
build_images() {
    log_info "构建Docker镜像..."
    
    # 构建主应用镜像
    docker build -f docker/Dockerfile.production -t autoreport/app:latest .
    
    log_success "镜像构建完成"
}

# 运行数据库迁移
run_migrations() {
    log_info "运行数据库迁移..."
    
    # 等待数据库启动
    log_info "等待数据库服务启动..."
    sleep 10
    
    # 运行迁移
    docker-compose -f docker/docker-compose.production.yml exec -T app alembic upgrade head
    
    log_success "数据库迁移完成"
}

# 部署服务
deploy_services() {
    log_info "部署服务..."
    
    # 使用生产环境配置
    export COMPOSE_FILE=docker/docker-compose.production.yml
    export COMPOSE_PROJECT_NAME=autoreport
    
    # 停止现有服务
    log_info "停止现有服务..."
    docker-compose down
    
    # 拉取最新镜像
    log_info "拉取最新镜像..."
    docker-compose pull
    
    # 启动服务
    log_info "启动服务..."
    docker-compose up -d
    
    log_success "服务部署完成"
}

# 健康检查
health_check() {
    log_info "进行健康检查..."
    
    # 等待服务启动
    sleep 30
    
    # 检查主应用
    if curl -f http://localhost/health > /dev/null 2>&1; then
        log_success "主应用健康检查通过"
    else
        log_error "主应用健康检查失败"
        return 1
    fi
    
    # 检查React Agent系统
    if curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        log_success "React Agent系统健康检查通过"
        
        # 检查React Agent具体服务
        agent_endpoints=("/api/v1/templates" "/api/v1/reports" "/api/v1/tasks")
        for endpoint in "${agent_endpoints[@]}"; do
            if curl -f http://localhost:8000$endpoint > /dev/null 2>&1; then
                log_success "React Agent端点 $endpoint 可访问"
            else
                log_warning "React Agent端点 $endpoint 不可访问"
            fi
        done
    else
        log_warning "React Agent系统健康检查失败"
    fi
    
    log_success "健康检查完成"
}

# 显示部署信息
show_deployment_info() {
    log_info "部署信息："
    echo "=================================="
    echo "应用地址: https://yourdomain.com"
    echo "API地址: https://api.yourdomain.com"
    echo "Grafana监控: http://localhost:3000"
    echo "Prometheus: http://localhost:9090"
    echo "Traefik仪表板: http://localhost:8080"
    echo "=================================="
    
    log_info "查看服务状态："
    docker-compose -f docker/docker-compose.production.yml ps
    
    log_info "查看应用日志："
    echo "docker-compose -f docker/docker-compose.production.yml logs -f app"
}

# 主函数
main() {
    log_info "开始生产环境部署..."
    
    # 检查参数
    ENVIRONMENT=${1:-production}
    
    if [ "$ENVIRONMENT" != "production" ] && [ "$ENVIRONMENT" != "staging" ]; then
        log_error "无效的环境: $ENVIRONMENT。支持的环境: production, staging"
        exit 1
    fi
    
    log_info "部署环境: $ENVIRONMENT"
    
    # 执行部署步骤
    check_dependencies
    check_env_file
    create_directories
    generate_db_init
    generate_prometheus_config
    build_images
    deploy_services
    run_migrations
    health_check
    show_deployment_info
    
    log_success "🎉 部署完成！"
}

# 错误处理
trap 'log_error "部署过程中发生错误，请检查日志"; exit 1' ERR

# 执行主函数
main "$@"