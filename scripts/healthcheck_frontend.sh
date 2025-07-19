#!/bin/sh
# Frontend health check script
# Check if the frontend application is responding correctly

set -e

# Configuration
HOST="localhost"
PORT="3000"
TIMEOUT=10

# Function to check if Next.js app is responding
check_app_health() {
    echo "Checking frontend health at http://${HOST}:${PORT}"
    
    # Check the main page first
    response=$(curl -f -s -m ${TIMEOUT} \
        -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
        "http://${HOST}:${PORT}/" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo "Frontend main page check passed"
        return 0
    else
        echo "Frontend main page check failed"
        return 1
    fi
}

# Function to check API health endpoint (if available)
check_api_health() {
    echo "Checking frontend API health endpoint..."
    
    # Try to access the health API endpoint
    response=$(curl -f -s -m ${TIMEOUT} \
        -H "Accept: application/json" \
        "http://${HOST}:${PORT}/api/health" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo "Frontend API health check passed"
        echo "Response: $response"
        return 0
    else
        echo "Frontend API health endpoint not available (this may be expected)"
        return 0  # Don't fail the health check for this
    fi
}

# Function to check if the service is ready
check_service_ready() {
    echo "Checking if frontend service is ready..."
    
    # Check if the service is listening on the port
    if ! nc -z ${HOST} ${PORT} 2>/dev/null; then
        echo "Frontend service is not listening on port ${PORT}"
        return 1
    fi
    
    echo "Frontend service is listening on port ${PORT}"
    return 0
}

# Main health check
main() {
    echo "Starting frontend health check..."
    
    # Check if service is ready
    if ! check_service_ready; then
        echo "Service readiness check failed"
        exit 1
    fi
    
    # Check app health
    if ! check_app_health; then
        echo "App health check failed"
        exit 1
    fi
    
    # Optional: Check API health endpoint
    check_api_health
    
    echo "All frontend health checks passed"
    exit 0
}

# Install netcat if not available (for Alpine)
if ! command -v nc >/dev/null 2>&1; then
    echo "Installing netcat for port checking..."
    apk add --no-cache netcat-openbsd 2>/dev/null || true
fi

# Run main function
main 