#!/bin/bash
set -e

# Health check based on service type
SERVICE_TYPE=${SERVICE_TYPE:-api}

case "$SERVICE_TYPE" in
    "api")
        curl -f -s --max-time 10 http://localhost:8000/api/v1/health || exit 1
        ;;
    "worker")
        celery -A app.services.task.core.worker.celery_app inspect ping --timeout=10 || exit 1
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