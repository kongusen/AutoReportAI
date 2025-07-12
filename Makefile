.PHONY: help install test test-backend test-frontend lint format clean build up down

# Default target
help:
	@echo "Available commands:"
	@echo "  install        - Install all dependencies"
	@echo "  test           - Run all tests"
	@echo "  test-backend   - Run backend tests"
	@echo "  test-frontend  - Run frontend tests"
	@echo "  lint           - Run linting on all code"
	@echo "  format         - Format all code"
	@echo "  clean          - Clean up build artifacts"
	@echo "  build          - Build all services"
	@echo "  up             - Start all services"
	@echo "  down           - Stop all services"
	@echo "  test-db        - Start test database"

# Install dependencies
install:
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
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

# Build services
build:
	docker-compose build

# Start services
up:
	docker-compose up -d

# Stop services
down:
	docker-compose down

# Start test database
test-db:
	docker-compose -f docker-compose.test.yml up -d test_db

# Run tests with Docker
test-docker:
	docker-compose -f docker-compose.test.yml up --build backend_test

# Stop test services
test-down:
	docker-compose -f docker-compose.test.yml down -v 