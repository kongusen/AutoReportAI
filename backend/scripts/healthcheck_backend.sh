#!/bin/bash
# Backend Health Check Script

# Check if the backend API is responding
if curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    exit 0
else
    exit 1
fi