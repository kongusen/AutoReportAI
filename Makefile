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
	docker-compose build --no-cache

docker-up:
	@echo "Starting services with Docker..."
	docker-compose up -d
	@echo "Services started. Access:"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Backend:  http://localhost:8000"
	@echo "  PgAdmin:  http://localhost:5050 (profile: admin)"

docker-down:
	@echo "Stopping Docker services..."
	docker-compose down

docker-dev:
	@echo "Starting development environment..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "Development environment started with hot reload enabled"

docker-test:
	@echo "Running tests in Docker..."
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
	docker-compose -f docker-compose.test.yml down -v

docker-logs:
	@echo "Showing Docker logs..."
	docker-compose logs -f

docker-health:
	@echo "Checking service health..."
	@docker-compose ps
	@echo ""
	@echo "Backend health:"
	@curl -f http://localhost:8000/health 2>/dev/null || echo "Backend not responding"
	@echo ""
	@echo "Frontend health:"
	@curl -f http://localhost:3000/ 2>/dev/null >/dev/null && echo "Frontend responding" || echo "Frontend not responding"

docker-clean:
	@echo "Cleaning Docker resources..."
	docker-compose down -v --remove-orphans
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