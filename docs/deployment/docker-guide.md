# Docker Deployment Guide

This guide covers the Docker configuration and deployment options for the AutoReportAI application.

## Overview

The application uses a multi-service Docker architecture with the following components:

- **Backend**: FastAPI application with Python 3.11
- **Frontend**: Next.js application with Node.js 18
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Admin Tools**: PgAdmin (optional)

## Quick Start

### Production Deployment

```bash
# Clone the repository
git clone <repository-url>
cd autoreport-ai

# Copy environment configuration
cp .env.docker.example .env

# Edit environment variables
nano .env

# Start all services
make docker-up
```

### Development Environment

```bash
# Start development environment with hot reload
make docker-dev

# Or manually:
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## Docker Configuration Files

### Main Configuration Files

- `docker-compose.yml` - Production configuration
- `docker-compose.dev.yml` - Development overrides
- `docker-compose.test.yml` - Testing configuration
- `.env.docker.example` - Environment variables template

### Dockerfiles

- `backend/Dockerfile` - Multi-stage backend build
- `frontend/Dockerfile` - Multi-stage frontend build
- `backend/.dockerignore` - Backend build exclusions
- `frontend/.dockerignore` - Frontend build exclusions

## Environment Configuration

### Required Environment Variables

```bash
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=autoreport
DATABASE_URL=postgresql://postgres:password@db:5432/autoreport

# Backend
SECRET_KEY=your-secret-key
ENVIRONMENT=production
LOG_LEVEL=INFO

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

### Optional Environment Variables

```bash
# Redis
REDIS_URL=redis://redis:6379

# Email (if using email features)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# External APIs
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

## Service Architecture

### Network Configuration

All services communicate through a custom bridge network (`autoreport-network`) with subnet `172.20.0.0/16`.

### Volume Management

- `postgres_data` - Database persistence
- `redis_data` - Redis persistence
- `backend_logs` - Application logs
- `pgadmin_data` - PgAdmin configuration

### Health Checks

All services include comprehensive health checks:

- **Database**: `pg_isready` command
- **Redis**: `redis-cli ping` command
- **Backend**: Custom health check script
- **Frontend**: Custom health check script

## Multi-Stage Builds

### Backend Dockerfile

```dockerfile
# Stage 1: Builder - Install dependencies
FROM python:3.11-slim as builder
# ... dependency installation

# Stage 2: Production - Copy artifacts
FROM python:3.11-slim as production
# ... production setup
```

### Frontend Dockerfile

```dockerfile
# Stage 1: Dependencies - Install node modules
FROM node:18-alpine AS deps
# ... dependency installation

# Stage 2: Builder - Build application
FROM node:18-alpine AS builder
# ... build process

# Stage 3: Production - Serve application
FROM node:18-alpine AS production
# ... production setup
```

## Available Commands

### Make Commands

```bash
# Docker operations
make docker-build    # Build all images
make docker-up       # Start all services
make docker-down     # Stop all services
make docker-dev      # Start development environment
make docker-test     # Run tests in containers
make docker-logs     # View service logs
make docker-health   # Check service health
make docker-clean    # Clean Docker resources

# Legacy commands (backward compatibility)
make build          # Same as docker-build
make up             # Same as docker-up
make down           # Same as docker-down
```

### Direct Docker Compose Commands

```bash
# Production
docker-compose up -d
docker-compose down
docker-compose logs -f

# Development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Testing
docker-compose -f docker-compose.test.yml up --build
```

## Development Workflow

### Local Development with Docker

1. **Start development environment**:
   ```bash
   make docker-dev
   ```

2. **Access services**:
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000
   - PgAdmin: http://localhost:5050

3. **View logs**:
   ```bash
   make docker-logs
   ```

4. **Run tests**:
   ```bash
   make docker-test
   ```

### Hot Reload

Development configuration includes:
- Backend: `uvicorn --reload` for Python hot reload
- Frontend: `npm run dev` for Next.js hot reload
- Volume mounts for source code changes

## Testing Configuration

### Test Services

- `test_db` - Isolated test database
- `test_redis` - Isolated test Redis
- `backend_test` - Backend test runner
- `frontend_test` - Frontend test runner
- `integration_test` - Integration test runner

### Running Tests

```bash
# All tests
make docker-test

# Backend tests only
docker-compose -f docker-compose.test.yml up backend_test

# Frontend tests only
docker-compose -f docker-compose.test.yml up frontend_test

# Integration tests
docker-compose -f docker-compose.test.yml up integration_test
```

## Production Deployment

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Minimum 2GB RAM
- Minimum 10GB disk space

### Deployment Steps

1. **Prepare environment**:
   ```bash
   cp .env.docker.example .env
   # Edit .env with production values
   ```

2. **Build images**:
   ```bash
   make docker-build
   ```

3. **Start services**:
   ```bash
   make docker-up
   ```

4. **Verify deployment**:
   ```bash
   make docker-health
   ```

### Production Optimizations

- Multi-stage builds reduce image size by ~60%
- Non-root users for security
- Resource limits configured
- Health checks for reliability
- Proper volume management for data persistence

## Monitoring and Maintenance

### Health Monitoring

```bash
# Check all services
make docker-health

# Check specific service
docker-compose exec backend /healthcheck.sh
docker-compose exec frontend /healthcheck.sh
```

### Log Management

```bash
# View all logs
make docker-logs

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend

# View logs with timestamps
docker-compose logs -f -t
```

### Resource Monitoring

```bash
# View resource usage
docker stats

# View service status
docker-compose ps
```

## Troubleshooting

### Common Issues

1. **Port conflicts**:
   ```bash
   # Check port usage
   netstat -tulpn | grep :3000
   netstat -tulpn | grep :8000
   ```

2. **Permission issues**:
   ```bash
   # Fix volume permissions
   sudo chown -R $USER:$USER ./backend/logs
   ```

3. **Database connection issues**:
   ```bash
   # Check database health
   docker-compose exec db pg_isready -U postgres
   ```

4. **Memory issues**:
   ```bash
   # Check memory usage
   docker stats --no-stream
   ```

### Debug Mode

Enable debug logging:

```bash
# Set in .env
LOG_LEVEL=DEBUG
NODE_ENV=development

# Restart services
make docker-down
make docker-up
```

## Security Considerations

### Production Security

- Non-root users in containers
- Minimal base images (Alpine Linux)
- No sensitive data in images
- Environment variable management
- Network isolation
- Resource limits

### Environment Variables

Never commit sensitive data:
- Use `.env` files (gitignored)
- Use Docker secrets in production
- Rotate keys regularly
- Use strong passwords

## Performance Optimization

### Image Size Optimization

- Multi-stage builds
- `.dockerignore` files
- Minimal base images
- Layer caching optimization

### Runtime Optimization

- Resource limits
- Health check intervals
- Connection pooling
- Caching strategies

## Backup and Recovery

### Database Backup

```bash
# Create backup
docker-compose exec db pg_dump -U postgres autoreport > backup.sql

# Restore backup
docker-compose exec -T db psql -U postgres autoreport < backup.sql
```

### Volume Backup

```bash
# Backup volumes
docker run --rm -v autoreport_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

## Migration Guide

### From Legacy Setup

1. Export existing data
2. Update configuration files
3. Build new images
4. Import data
5. Verify functionality

### Version Updates

1. Pull latest code
2. Rebuild images
3. Run database migrations
4. Restart services
5. Verify health checks

## Support and Resources

- Docker Documentation: https://docs.docker.com/
- Docker Compose Reference: https://docs.docker.com/compose/
- FastAPI Docker Guide: https://fastapi.tiangolo.com/deployment/docker/
- Next.js Docker Guide: https://nextjs.org/docs/deployment#docker-image