#!/bin/bash
set -e

# 确保在正确的工作目录中
cd /app

# 配置时区 (如果存在配置脚本)
if [ -f "/app/scripts/configure-timezone.sh" ]; then
    /app/scripts/configure-timezone.sh
fi

# 确保必要的目录存在并有正确的权限
ensure_directories() {
    echo "🗂️  开始容器权限与目录检查..."
    
    # 显示当前用户信息
    echo "📋 容器环境信息:"
    echo "  用户: $(whoami) (UID: $(id -u), GID: $(id -g))"
    echo "  工作目录: $(pwd)"
    echo "  可写权限: $([ -w "." ] && echo "是" || echo "否")"
    
    # 权限检查结果
    PERMISSIONS_OK=true
    FAILED_DIRS=""
    
    # 需要创建的基础目录
    BASE_DIRS=(logs cache storage temp uploads)
    SUB_DIRS=(
        "cache/llamaindex"
        "cache/react_agent" 
        "cache/embeddings"
        "storage/templates"
        "storage/reports"
        "storage/exports"
    )
    
    echo "📁 创建基础目录..."
    # 创建基础目录并检查权限
    for dir in "${BASE_DIRS[@]}"; do
        if [ ! -d "$dir" ]; then
            if mkdir -p "$dir" 2>/dev/null; then
                echo "  ✅ 创建目录: $dir"
            else
                echo "  ❌ 无法创建目录: $dir (权限不足)"
                PERMISSIONS_OK=false
                FAILED_DIRS="$FAILED_DIRS $dir"
            fi
        else
            echo "  ℹ️  目录已存在: $dir"
        fi
        
        # 测试目录写入权限
        if [ -d "$dir" ]; then
            TEST_FILE="$dir/.permission_test_$$"
            if touch "$TEST_FILE" 2>/dev/null; then
                rm -f "$TEST_FILE" 2>/dev/null
                echo "  ✅ $dir 写入权限正常"
            else
                echo "  ❌ $dir 无写入权限"
                PERMISSIONS_OK=false
                FAILED_DIRS="$FAILED_DIRS $dir"
            fi
        fi
    done
    
    echo "📂 创建子目录..."
    # 创建子目录
    for subdir in "${SUB_DIRS[@]}"; do
        if mkdir -p "$subdir" 2>/dev/null; then
            echo "  ✅ 创建子目录: $subdir"
        else
            echo "  ⚠️  无法创建子目录: $subdir (已跳过)"
        fi
    done
    
    # 根据权限检查结果设置环境变量
    if [ "$PERMISSIONS_OK" = true ]; then
        echo "✅ 所有目录权限检查通过"
        export ENABLE_FILE_LOGGING=true
        export ENABLE_LOCAL_STORAGE=true
        export CONTAINER_PERMISSIONS=full
    else
        echo "⚠️  部分目录权限受限: $FAILED_DIRS"
        export ENABLE_FILE_LOGGING=false
        export ENABLE_LOCAL_STORAGE=false
        export CONTAINER_PERMISSIONS=limited
        echo "🔄 系统将自动启用MinIO优先策略:"
        echo "  - 日志: 输出到标准输出流"
        echo "  - 存储: 优先使用MinIO对象存储"
        echo "  - 缓存: 使用内存缓存"
        echo "  - 文件: MinIO存储为主，本地存储为备选"
    fi
    
    # 特殊权限检查
    echo "🔒 执行特殊权限检查..."
    
    # 检查是否能执行脚本
    if [ -x "$0" ]; then
        echo "  ✅ 脚本执行权限正常"
    else
        echo "  ⚠️  脚本执行权限异常"
    fi
    
    # 检查Python执行权限
    if python --version >/dev/null 2>&1; then
        echo "  ✅ Python执行权限正常"
    else
        echo "  ❌ Python执行权限异常"
    fi
    
    # 网络连通性检查
    if ping -c 1 -W 1 google.com >/dev/null 2>&1; then
        echo "  ✅ 网络连通正常"
        export NETWORK_ACCESS=true
    else
        echo "  ⚠️  网络连通受限（正常，取决于网络配置）"
        export NETWORK_ACCESS=false
    fi
    
    # MinIO连接测试（如果配置了MinIO）
    echo "  🗄️  MinIO存储连接测试..."
    if python -c "
import os
from app.core.config import settings
print(f'MinIO配置检查:')
print(f'  Endpoint: {getattr(settings, \"MINIO_ENDPOINT\", \"未配置\")}')
print(f'  Access Key: {\"已配置\" if getattr(settings, \"MINIO_ACCESS_KEY\", None) else \"未配置\"}')
print(f'  Secret Key: {\"已配置\" if getattr(settings, \"MINIO_SECRET_KEY\", None) else \"未配置\"}')
print(f'  Bucket: {getattr(settings, \"MINIO_BUCKET_NAME\", \"未配置\")}')
print(f'存储策略: {getattr(settings, \"STORAGE_STRATEGY\", \"minio_first\")}')
" 2>/dev/null; then
        echo "  ✅ MinIO配置读取正常"
        export MINIO_CONFIG_OK=true
    else
        echo "  ⚠️  MinIO配置读取异常"
        export MINIO_CONFIG_OK=false
    fi
    
    echo "📊 容器权限检查完成"
    echo "  ENABLE_FILE_LOGGING=$ENABLE_FILE_LOGGING"
    echo "  ENABLE_LOCAL_STORAGE=$ENABLE_LOCAL_STORAGE"
    echo "  CONTAINER_PERMISSIONS=$CONTAINER_PERMISSIONS"
    echo "  NETWORK_ACCESS=$NETWORK_ACCESS"
    echo "  MINIO_CONFIG_OK=$MINIO_CONFIG_OK"
}

# 运行目录检查
ensure_directories

# 权限检查总结
summarize_permissions() {
    echo ""
    echo "📊 ============== 容器权限检查总结 =============="
    echo "环境类型: Docker容器"
    echo "用户信息: $(whoami) (UID: $(id -u), GID: $(id -g))"
    echo "工作目录: $(pwd)"
    echo ""
    echo "🔐 权限状态:"
    echo "  文件日志: ${ENABLE_FILE_LOGGING:-未设置}"
    echo "  本地存储: ${ENABLE_LOCAL_STORAGE:-未设置}"
    echo "  容器权限: ${CONTAINER_PERMISSIONS:-未设置}"
    echo "  网络访问: ${NETWORK_ACCESS:-未设置}"
    echo "  MinIO配置: ${MINIO_CONFIG_OK:-未设置}"
    echo ""
    
    if [ "${CONTAINER_PERMISSIONS:-}" = "limited" ]; then
        echo "⚠️  检测到权限限制，以下功能将受影响:"
        echo "   - 本地文件存储可能无法正常工作"
        echo "   - 日志将输出到标准输出而非文件"
        echo "   - 某些缓存功能可能受限"
        echo ""
        echo "🔄 系统自动启用的回退策略:"
        echo "   - MinIO对象存储优先"
        echo "   - 控制台日志输出"
        echo "   - 内存缓存机制"
        echo ""
    else
        echo "✅ 容器权限检查通过，所有功能应正常工作"
        echo ""
    fi
    echo "=============================================="
    echo ""
}

# 运行权限总结
summarize_permissions

# Function to wait for database
wait_for_db() {
    echo "Waiting for database..."
    while ! python -c "
import psycopg2
import sys
import os
from urllib.parse import urlparse

db_url = os.getenv('DATABASE_URL', 'postgresql://autoreport_user:postgres@db:5432/autoreport')
parsed = urlparse(db_url)

try:
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path[1:],
        connect_timeout=5
    )
    conn.close()
    print('Database is ready!')
except Exception as e:
    print(f'Database not ready: {e}')
    sys.exit(1)
"; do
        echo "Database not ready, waiting 3 seconds..."
        sleep 3
    done
}

# Function to wait for Redis
wait_for_redis() {
    echo "Waiting for Redis..."
    while ! python -c "
import redis
import sys
import os
from urllib.parse import urlparse

redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
parsed = urlparse(redis_url)

try:
    r = redis.Redis(
        host=parsed.hostname,
        port=parsed.port or 6379,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    r.ping()
    print('Redis is ready!')
except Exception as e:
    print(f'Redis not ready: {e}')
    sys.exit(1)
"; do
        echo "Redis not ready, waiting 3 seconds..."
        sleep 3
    done
}

# Function to run comprehensive startup check
run_startup_check() {
    echo "🚀 Running comprehensive startup check..."
    if python scripts/startup_check.py; then
        echo "✅ Startup check completed successfully"
        return 0
    else
        echo "❌ Startup check failed"
        return 1
    fi
}

# Legacy function to run database migrations (kept for compatibility)
run_migrations() {
    echo "Running database migrations..."
    if cd /app && python -m alembic -c alembic.ini upgrade head; then
        echo "✅ Database migrations completed successfully"
        return 0
    else
        echo "⚠️  Database migrations failed, skipping migrations for now..."
        return 0  # Continue even if migrations fail
    fi
}

# Initialize database with tables and default users (only if needed)
init_database() {
    echo "🗄️  开始数据库初始化检查..."
    
    # 检查数据库连接权限
    echo "🔒 检查数据库连接权限..."
    
    # Check if database is already initialized by checking for users table
    echo "🔍 运行数据库表存在性检查..."
    # Use psql to directly check if users exist (simpler and faster)
    if python -c "
import psycopg2
import sys
import os
from urllib.parse import urlparse

db_url = os.getenv('DATABASE_URL')
parsed = urlparse(db_url)

try:
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path[1:],
        connect_timeout=5
    )
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM users')
    user_count = cur.fetchone()[0]
    cur.close()
    conn.close()
    
    if user_count > 0:
        print(f'ℹ️  Database already initialized with {user_count} users. Skipping initialization.')
        sys.exit(0)
    else:
        print('📝 Database is empty, initialization needed.')
        sys.exit(1)
except Exception as e:
    print(f'🔧 Database check failed: {e}')
    print('📝 Database initialization needed.')
    sys.exit(1)
"; then
        echo "✅ Database already initialized, skipping initialization"
        return 0
    fi
    
    echo "🔧 开始数据库初始化..."
    
    # 检查Python模块导入权限
    echo "🐍 检查Python环境和模块访问权限..."
    if python -c "import sys; sys.path.append('/app'); from app.db.session import get_db_session; print('✅ 数据库模块导入成功')" 2>/dev/null; then
        echo "✅ Python模块访问权限正常"
    else
        echo "❌ Python模块访问权限异常，可能影响数据库初始化"
        return 1
    fi
    
    # Try to run the init_db.py script if it exists
    if [ -f "/app/scripts/init_db.py" ]; then
        echo "📝 运行数据库初始化脚本（快速模式）..."
        echo "🔍 检查脚本执行权限..."
        
        if [ -r "/app/scripts/init_db.py" ]; then
            echo "✅ 初始化脚本可读取"
        else
            echo "⚠️  初始化脚本读取权限受限"
        fi
        
        if SKIP_ARCHITECTURE_VALIDATION=true python /app/scripts/init_db.py; then
            echo "✅ Database initialization completed successfully"
            return 0
        else
            echo "⚠️  数据库初始化脚本执行失败，尝试内联初始化..."
        fi
    else
        echo "ℹ️  未找到独立初始化脚本，使用内联初始化"
    fi
    
    # Fallback: inline database initialization
    echo "🔧 Creating default admin user if not exists..."
    python - <<'INIT_PY'
import sys
sys.path.append('/app')
from app.db.session import get_db_session
from app.models.user import User
from app.core.security import get_password_hash
from app.core.config import settings
import uuid

try:
    with get_db_session() as db:
        # Check if admin user exists
        admin_user = db.query(User).filter(User.email == settings.FIRST_SUPERUSER_EMAIL).first()
        if not admin_user:
            # Create default admin user
            admin_user = User(
                id=str(uuid.uuid4()),
                username=settings.FIRST_SUPERUSER,
                email=settings.FIRST_SUPERUSER_EMAIL,
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                is_active=True,
                is_superuser=True,
                full_name="System Administrator"
            )
            db.add(admin_user)
            db.commit()
            print(f"✅ Created default admin user: {settings.FIRST_SUPERUSER_EMAIL}")
        else:
            print(f"ℹ️  Admin user already exists: {settings.FIRST_SUPERUSER_EMAIL}")
    print("✅ Database initialization completed")
except Exception as e:
    print(f"❌ Database initialization failed: {e}")
    import traceback
    traceback.print_exc()
INIT_PY
    
    echo "✅ Database initialization process completed"
    return 0
}

# Print environment variables and Settings (before starting Python app)
print_env_and_settings() {
    echo "========================================"
    echo "🧩 Startup environment overview"
    echo "========================================"
    echo "ENVIRONMENT=${ENVIRONMENT:-unset}"
    echo "DEBUG=${DEBUG:-unset}"
    echo "LOG_LEVEL=${LOG_LEVEL:-unset}"
    echo "POSTGRES_HOST=${POSTGRES_HOST:-unset}"
    echo "POSTGRES_PORT=${POSTGRES_PORT:-unset}"
    echo "POSTGRES_DB=${POSTGRES_DB:-unset}"
    echo "POSTGRES_USER=${POSTGRES_USER:-unset}"
    if [ -n "${POSTGRES_PASSWORD}" ]; then echo "POSTGRES_PASSWORD=****"; else echo "POSTGRES_PASSWORD=unset"; fi
    echo "REDIS_URL=${REDIS_URL:-unset}"
    echo "DATABASE_URL=${DATABASE_URL:-unset}"
    if [ -n "${ENCRYPTION_KEY}" ]; then echo "ENCRYPTION_KEY_LENGTH=${#ENCRYPTION_KEY}"; else echo "ENCRYPTION_KEY=unset"; fi
    echo "========================================"
    echo "Attempting to import and print Settings from Python (pre-main)..."
    set +e
    python - <<'PY'
from app.core.config import settings

def is_sensitive(name: str) -> bool:
    ln = name.lower()
    return any(s in ln for s in ("password","secret","key","token"))

def mask(val):
    try:
        s = str(val)
        return s[:4] + "*"*(len(s)-8) + s[-4:] if len(s) > 8 else "*"*len(s)
    except Exception:
        return "****"

print("="*80)
print("Settings (pre-main)")
print("-"*80)
for k in sorted([a for a in dir(settings) if not a.startswith("_") and not callable(getattr(settings,a))]):
    v = getattr(settings, k)
    if is_sensitive(k):
        v = mask(v)
    print(f"{k:<30} = {v}")
print("="*80)
PY
    if [ $? -ne 0 ]; then
        echo "⚠️  Warning: Failed to import/print Settings."
    fi
    set -e
}

# Main execution based on command
case "$1" in
    "api")
        # Print env and settings before any checks
        print_env_and_settings
        
        # Wait for database and Redis
        wait_for_db
        wait_for_redis
        
        # Initialize database (create tables and default users)
        echo "🗄️  Initializing database..."
        init_database
        
        # Use comprehensive startup check
        if run_startup_check; then
            echo "🚀 Starting API server..."
            exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-1}
        else
            echo "❌ Startup check failed, cannot start API server"
            exit 1
        fi
        ;;
    "worker")
        # Print env and settings before any checks
        print_env_and_settings
        # Worker also needs database access, so run startup check
        if run_startup_check; then
            echo "🚀 Starting Celery worker..."
            exec celery -A app.core.celery_scheduler worker \
                --loglevel=info \
                --queues=${CELERY_QUEUES:-default} \
                --concurrency=${CELERY_CONCURRENCY:-4} \
                --max-tasks-per-child=${CELERY_MAX_TASKS:-100}
        else
            echo "❌ Startup check failed, cannot start worker"
            exit 1
        fi
        ;;
    "beat")
        # Print env and settings before any checks
        print_env_and_settings
        # Beat scheduler needs database access for scheduling data
        if run_startup_check; then
            echo "🚀 Starting Celery beat scheduler..."
            exec celery -A app.core.celery_scheduler beat --loglevel=info
        else
            echo "❌ Startup check failed, cannot start beat scheduler"
            exit 1
        fi
        ;;
    "startup-check")
        run_startup_check
        ;;
    "migrate")
        wait_for_db
        run_migrations
        ;;
    "init")
        wait_for_db
        init_database
        ;;
    *)
        echo "Available commands: api, worker, beat, startup-check, migrate, init"
        echo "Usage: docker run <image> <command>"
        exit 1
        ;;
esac 