#!/bin/bash
set -e

# Health check based on service type
SERVICE_TYPE=${SERVICE_TYPE:-api}

case "$SERVICE_TYPE" in
    "api")
        curl -f -s --max-time 10 http://localhost:8000/api/v1/health || exit 1
        ;;
    "worker")
        # Optimized worker health check with reduced noise
        
        # Check if celery process is running
        if ! pgrep -f "celery.*worker" > /dev/null 2>&1; then
            exit 1
        fi
        
        # Check Redis connection quietly
        python3 -c "
import redis
import os
import sys
import warnings
warnings.filterwarnings('ignore')

try:
    redis_url = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
    r = redis.from_url(redis_url)
    r.ping()
except Exception:
    sys.exit(1)
" 2>/dev/null || exit 1
        
        # Check worker ping with suppressed output
        if ! celery -A app.services.application.task_management.core.worker.celery_app inspect ping --timeout=3 2>/dev/null | grep -q "pong"; then
            exit 1
        fi
        ;;
    "beat")
        # For beat, just check if process is running
        pgrep -f "celery.*beat" > /dev/null || exit 1
        ;;
    "flower")
        curl -f -s --max-time 10 http://localhost:5555/api/workers || exit 1
        ;;
    *)
        echo "Unknown service type: $SERVICE_TYPE"
        exit 1
        ;;
esac 