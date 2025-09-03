#!/bin/bash
set -e

# 配置时区 (如果存在配置脚本)
if [ -f "/app/scripts/configure-timezone.sh" ]; then
    /app/scripts/configure-timezone.sh
fi

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
    echo "Checking if database initialization is needed..."
    
    # Check if database is already initialized by checking for users table
    echo "🔍 Running simple user count check..."
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
    
    echo "Initializing database..."
    
    # Try to run the init_db.py script if it exists
    if [ -f "/app/scripts/init_db.py" ]; then
        echo "📝 Running database initialization script (fast mode)..."
        if SKIP_ARCHITECTURE_VALIDATION=true python /app/scripts/init_db.py; then
            echo "✅ Database initialization completed successfully"
            return 0
        else
            echo "⚠️  Database initialization script failed, trying inline initialization..."
        fi
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