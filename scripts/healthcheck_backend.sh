#!/bin/sh
# Backend health check script
# Check if the backend API is responding correctly

set -e

# Configuration
HOST="localhost"
PORT="8000"
HEALTH_ENDPOINT="/health"
TIMEOUT=10

# Function to check API health
check_api_health() {
    echo "Checking backend health at http://${HOST}:${PORT}${HEALTH_ENDPOINT}"
    
    # Use curl with timeout and proper error handling
    response=$(curl -f -s -m ${TIMEOUT} \
        -H "Accept: application/json" \
        "http://${HOST}:${PORT}${HEALTH_ENDPOINT}" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo "Backend health check passed"
        echo "Response: $response"
        return 0
    else
        echo "Backend health check failed"
        return 1
    fi
}

# Function to check database connectivity (if health endpoint includes DB check)
check_database_connection() {
    echo "Checking database connectivity through API..."
    
    # Try to access an endpoint that requires database
    response=$(curl -f -s -m ${TIMEOUT} \
        -H "Accept: application/json" \
        "http://${HOST}:${PORT}/api/v1/health/db" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo "Database connectivity check passed"
        return 0
    else
        echo "Database connectivity check failed (this may be expected if endpoint doesn't exist)"
        return 0  # Don't fail the health check for this
    fi
}

# Main health check
main() {
    echo "Starting backend health check..."
    
    # Check if the service is listening on the port
    if ! nc -z ${HOST} ${PORT} 2>/dev/null; then
        echo "Backend service is not listening on port ${PORT}"
        exit 1
    fi
    
    # Check API health
    if ! check_api_health; then
        echo "API health check failed"
        exit 1
    fi
    
    # Optional: Check database connectivity
    check_database_connection
    
    echo "All health checks passed"
    exit 0
}

# Install netcat if not available (for Alpine)
if ! command -v nc >/dev/null 2>&1; then
    echo "Installing netcat for port checking..."
    apk add --no-cache netcat-openbsd 2>/dev/null || true
fi

# Run main function
main 