#!/bin/bash
set -e

# Enhanced health check for Celery Worker
echo "🔍 Starting Celery Worker health check..."

# Check if celery process is running
if ! pgrep -f "celery.*worker" > /dev/null; then
    echo "❌ Celery worker process not found"
    exit 1
fi

# Check if worker can respond to ping
echo "📡 Checking worker ping response..."
PING_OUTPUT=$(celery -A app.services.task.core.worker.celery_app inspect ping --timeout=5 2>/dev/null || echo "PING_FAILED")

if echo "$PING_OUTPUT" | grep -q "pong"; then
    echo "✅ Worker ping successful"
else
    echo "❌ Worker ping failed"
    exit 1
fi

# Check Redis connection
echo "🔗 Checking Redis connection..."
if ! python3 -c "
import redis
import os
redis_url = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
try:
    r = redis.from_url(redis_url)
    r.ping()
    print('✅ Redis connection successful')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    exit(1)
" 2>/dev/null; then
    echo "❌ Redis connection check failed"
    exit 1
fi

# Check worker stats (optional, non-blocking)
echo "📊 Checking worker stats..."
STATS_OUTPUT=$(celery -A app.services.task.core.worker.celery_app inspect stats --timeout=3 2>/dev/null || echo "STATS_UNAVAILABLE")

if echo "$STATS_OUTPUT" | grep -q "total"; then
    echo "✅ Worker stats available"
    # Extract worker name if available
    WORKER_NAME=$(echo "$STATS_OUTPUT" | grep -o "celery@[^:]*" | head -1)
    if [ -n "$WORKER_NAME" ]; then
        echo "🏷️  Worker name: $WORKER_NAME"
    fi
else
    echo "⚠️  Worker stats unavailable (non-critical)"
fi

# Check if worker can process tasks (optional quick test)
echo "🔄 Testing task processing capability..."
TASK_TEST=$(python3 -c "
from app.services.task.core.worker.tasks.basic_tasks import test_celery_task
import asyncio
import time

try:
    # Send a quick test task
    result = test_celery_task.delay('health_check')
    print(f'📤 Test task sent: {result.id}')
    
    # Wait for result with short timeout
    task_result = result.get(timeout=3)
    print('✅ Task processing test successful')
except Exception as e:
    print(f'⚠️  Task processing test failed: {e}')
    # Don't fail health check for this
" 2>/dev/null || echo "⚠️ Task processing test unavailable")

echo "🎉 Celery Worker health check completed successfully"
exit 0