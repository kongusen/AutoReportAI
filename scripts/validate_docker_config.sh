#!/bin/bash
# Docker configuration validation script

set -e

echo "🐳 Validating Docker Configuration..."
echo "=================================="

# Check if Docker is installed and running
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker is not running"
    exit 1
fi

echo "✅ Docker is installed and running"

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed"
    exit 1
fi

echo "✅ Docker Compose is available"

# Validate main docker-compose.yml
echo ""
echo "📋 Validating docker-compose.yml..."
if docker-compose config --quiet; then
    echo "✅ docker-compose.yml is valid"
else
    echo "❌ docker-compose.yml has errors"
    exit 1
fi

# Validate test configuration
echo ""
echo "📋 Validating docker-compose.test.yml..."
if docker-compose -f docker-compose.test.yml config --quiet; then
    echo "✅ docker-compose.test.yml is valid"
else
    echo "❌ docker-compose.test.yml has errors"
    exit 1
fi

# Validate development configuration
echo ""
echo "📋 Validating docker-compose.dev.yml..."
if docker-compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet; then
    echo "✅ docker-compose.dev.yml is valid"
else
    echo "❌ docker-compose.dev.yml has errors"
    exit 1
fi

# Check Dockerfiles
echo ""
echo "📋 Checking Dockerfiles..."

if [ -f "backend/Dockerfile" ]; then
    echo "✅ Backend Dockerfile exists"
else
    echo "❌ Backend Dockerfile missing"
    exit 1
fi

if [ -f "frontend/Dockerfile" ]; then
    echo "✅ Frontend Dockerfile exists"
else
    echo "❌ Frontend Dockerfile missing"
    exit 1
fi

# Check .dockerignore files
echo ""
echo "📋 Checking .dockerignore files..."

if [ -f "backend/.dockerignore" ]; then
    echo "✅ Backend .dockerignore exists"
else
    echo "⚠️  Backend .dockerignore missing (recommended)"
fi

if [ -f "frontend/.dockerignore" ]; then
    echo "✅ Frontend .dockerignore exists"
else
    echo "⚠️  Frontend .dockerignore missing (recommended)"
fi

# Check health check scripts
echo ""
echo "📋 Checking health check scripts..."

if [ -f "scripts/healthcheck_backend.sh" ] && [ -x "scripts/healthcheck_backend.sh" ]; then
    echo "✅ Backend health check script exists and is executable"
else
    echo "❌ Backend health check script missing or not executable"
    exit 1
fi

if [ -f "scripts/healthcheck_frontend.sh" ] && [ -x "scripts/healthcheck_frontend.sh" ]; then
    echo "✅ Frontend health check script exists and is executable"
else
    echo "❌ Frontend health check script missing or not executable"
    exit 1
fi

# Check environment template
echo ""
echo "📋 Checking environment configuration..."

if [ -f ".env.docker.example" ]; then
    echo "✅ Environment template exists"
else
    echo "⚠️  Environment template missing (recommended)"
fi

# Check documentation
echo ""
echo "📋 Checking documentation..."

if [ -f "docs/deployment/docker-guide.md" ]; then
    echo "✅ Docker deployment guide exists"
else
    echo "⚠️  Docker deployment guide missing (recommended)"
fi

echo ""
echo "🎉 Docker configuration validation completed successfully!"
echo ""
echo "Next steps:"
echo "1. Copy .env.docker.example to .env and configure your environment"
echo "2. Run 'make docker-build' to build the images"
echo "3. Run 'make docker-up' to start the services"
echo "4. Run 'make docker-health' to check service health"