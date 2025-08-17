#!/bin/bash
set -e

# Silent health check for Celery Worker
SERVICE_TYPE=${SERVICE_TYPE:-worker}

case "$SERVICE_TYPE" in
    "api")
        curl -f -s --max-time 10 http://localhost:8000/api/v1/health > /dev/null 2>&1 || exit 1
        ;;
    "worker")
        # Check if celery process is running
        pgrep -f "celery.*worker" > /dev/null 2>&1 || exit 1
        
        # Check Redis connection with all output suppressed
        PYTHONPATH=/app python3 -c "
import redis
import os
import sys
import warnings
import logging

# Suppress all warnings and logs
warnings.filterwarnings('ignore')
logging.disable(logging.CRITICAL)

# Redirect stdout/stderr to suppress initialization messages
import io
import contextlib

@contextlib.contextmanager
def suppress_output():
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        yield

with suppress_output():
    try:
        # Import celery app to initialize it
        from app.services.task.core.worker.config.celery_app import celery_app
        
        # Test Redis connection
        redis_url = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
        r = redis.from_url(redis_url)
        r.ping()
        
        # Test celery connection
        inspect = celery_app.control.inspect()
        stats = inspect.ping(timeout=3)
        
        if not stats or not any('pong' in str(v) for v in stats.values()):
            sys.exit(1)
            
    except Exception:
        sys.exit(1)
" > /dev/null 2>&1 || exit 1
        ;;
    "beat")
        pgrep -f "celery.*beat" > /dev/null 2>&1 || exit 1
        ;;
    "flower")
        curl -f -s --max-time 10 http://localhost:5555/api/workers > /dev/null 2>&1 || exit 1
        ;;
    *)
        exit 1
        ;;
esac