.PHONY: help install test test-backend test-frontend lint format clean build up down docker-build docker-up docker-down docker-dev docker-test docker-logs docker-health

# Default target
help:
	@echo "Available commands:"
	@echo ""
	@echo "Local Development:"
	@echo "  install        - Install all dependencies"
	@echo "  test           - Run all tests"
	@echo "  test-backend   - Run backend tests"
	@echo "  test-frontend  - Run frontend tests"
	@echo "  lint           - Run linting on all code"
	@echo "  format         - Format all code"
	@echo "  clean          - Clean up build artifacts"
	@echo ""
	@echo "Docker Commands:"
	@echo "  docker-build   - Build all Docker images"
	@echo "  docker-up      - Start all services with Docker"
	@echo "  docker-down    - Stop all Docker services"
	@echo "  docker-dev     - Start development environment"
	@echo "  docker-test    - Run tests in Docker"
	@echo "  docker-logs    - Show Docker logs"
	@echo "  docker-health  - Check service health"
	@echo "  docker-clean   - Clean Docker resources"
	@echo ""
	@echo "Celery Commands:"
	@echo "  celery-worker        - Start Celery worker"
	@echo "  celery-worker-stop   - Stop Celery worker"
	@echo "  celery-worker-restart- Restart Celery worker"
	@echo "  celery-worker-logs   - Show Celery worker logs"
	@echo "  celery-beat          - Start Celery beat scheduler"
	@echo "  celery-beat-stop     - Stop Celery beat scheduler"
	@echo "  celery-beat-restart  - Restart Celery beat scheduler"
	@echo "  celery-beat-logs     - Show Celery beat logs"
	@echo "  celery-flower        - Start Flower monitoring"
	@echo "  celery-flower-stop   - Stop Flower monitoring"
	@echo "  celery-flower-logs   - Show Flower logs"
	@echo "  celery-all           - Start all Celery services"
	@echo "  celery-all-stop      - Stop all Celery services"
	@echo "  celery-all-restart   - Restart all Celery services"
	@echo "  celery-status        - Check Celery services status"
	@echo ""
	@echo "Legacy Commands:"
	@echo "  build          - Build services (legacy)"
	@echo "  up             - Start services (legacy)"
	@echo "  down           - Stop services (legacy)"

# Install dependencies
install:
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements/development.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

# Run all tests
test: test-backend test-frontend

# Run backend tests
test-backend:
	@echo "Running backend tests..."
	cd backend && python -m pytest --cov=app --cov-report=term-missing -v

# Run frontend tests
test-frontend:
	@echo "Running frontend tests..."
	cd frontend && npm test -- --coverage --watchAll=false

# Run linting
lint:
	@echo "Linting backend code..."
	cd backend && flake8 .
	cd backend && black --check .
	cd backend && isort --check-only .
	@echo "Linting frontend code..."
	cd frontend && npm run lint

# Format code
format:
	@echo "Formatting backend code..."
	cd backend && black .
	cd backend && isort .
	@echo "Formatting frontend code..."
	cd frontend && npm run format

# Clean up
clean:
	@echo "Cleaning up..."
	cd backend && find . -type d -name "__pycache__" -exec rm -rf {} +
	cd backend && find . -name "*.pyc" -delete
	cd frontend && rm -rf .next
	cd frontend && rm -rf node_modules/.cache

# Docker Commands
docker-build:
	@echo "Building Docker images..."
	cd autoreporait-docker && docker-compose build --no-cache

docker-up:
	@echo "Starting services with Docker..."
	cd autoreporait-docker && docker-compose up -d
	@echo "Services started. Access:"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Backend:  http://localhost:8000"
	@echo "  PgAdmin:  http://localhost:5050 (profile: admin)"

docker-down:
	@echo "Stopping Docker services..."
	cd autoreporait-docker && docker-compose down

# Celery Commands
celery-worker:
	@echo "Starting Celery worker..."
	cd autoreporait-docker && docker-compose up -d celery-worker

celery-worker-stop:
	@echo "Stopping Celery worker..."
	cd autoreporait-docker && docker-compose stop celery-worker

celery-worker-restart:
	@echo "Restarting Celery worker..."
	cd autoreporait-docker && docker-compose restart celery-worker

celery-worker-logs:
	@echo "Showing Celery worker logs..."
	cd autoreporait-docker && docker-compose logs -f celery-worker

celery-beat:
	@echo "Starting Celery beat scheduler..."
	cd autoreporait-docker && docker-compose up -d celery-beat

celery-beat-stop:
	@echo "Stopping Celery beat scheduler..."
	cd autoreporait-docker && docker-compose stop celery-beat

celery-beat-restart:
	@echo "Restarting Celery beat scheduler..."
	cd autoreporait-docker && docker-compose restart celery-beat

celery-beat-logs:
	@echo "Showing Celery beat logs..."
	cd autoreporait-docker && docker-compose logs -f celery-beat

celery-flower:
	@echo "Starting Flower monitoring..."
	cd autoreporait-docker && docker-compose --profile monitoring up -d flower

celery-flower-stop:
	@echo "Stopping Flower monitoring..."
	cd autoreporait-docker && docker-compose --profile monitoring stop flower

celery-flower-logs:
	@echo "Showing Flower logs..."
	cd autoreporait-docker && docker-compose --profile monitoring logs -f flower

celery-all:
	@echo "Starting all Celery services..."
	cd autoreporait-docker && docker-compose up -d celery-worker celery-beat

celery-all-stop:
	@echo "Stopping all Celery services..."
	cd autoreporait-docker && docker-compose stop celery-worker celery-beat

celery-all-restart:
	@echo "Restarting all Celery services..."
	cd autoreporait-docker && docker-compose restart celery-worker celery-beat

celery-status:
	@echo "Checking Celery services status..."
	@cd autoreporait-docker && docker-compose ps celery-worker celery-beat flower 2>/dev/null || echo "Some Celery services not found"

docker-dev:
	@echo "Starting development environment..."
	cd autoreporait-docker && docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "Development environment started with hot reload enabled"

docker-test:
	@echo "Running tests in Docker..."
	cd autoreporait-docker && docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
	cd autoreporait-docker && docker-compose -f docker-compose.test.yml down -v

docker-logs:
	@echo "Showing Docker logs..."
	cd autoreporait-docker && docker-compose logs -f

docker-health:
	@echo "Checking service health..."
	@cd autoreporait-docker && docker-compose ps
	@echo ""
	@echo "Backend health:"
	@curl -f http://localhost:8000/health 2>/dev/null || echo "Backend not responding"
	@echo ""
	@echo "Frontend health:"
	@curl -f http://localhost:3000/ 2>/dev/null >/dev/null && echo "Frontend responding" || echo "Frontend not responding"

docker-clean:
	@echo "Cleaning Docker resources..."
	cd autoreporait-docker && docker-compose down -v --remove-orphans
	docker system prune -f
	docker volume prune -f

# Legacy commands (for backward compatibility)
build: docker-build
up: docker-up
down: docker-down

# Test database commands
test-db:
	docker-compose -f docker-compose.test.yml up -d test_db

test-docker: docker-test

test-down:
	docker-compose -f docker-compose.test.yml down -v 