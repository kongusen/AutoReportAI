#!/bin/bash
set -e

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

# Legacy function to initialize database (kept for compatibility)
init_database() {
    echo "Initializing database..."
    if python scripts/init_db.py; then
        echo "✅ Database initialization completed successfully"
        return 0
    else
        echo "⚠️  Database initialization failed, but continuing startup..."
        return 0  # Don't fail startup even if init fails
    fi
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
        # Use comprehensive startup check instead of individual checks
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
            exec celery -A app.services.task.core.worker.celery_app worker \
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
            exec celery -A app.services.task.core.worker.celery_app beat --loglevel=info
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