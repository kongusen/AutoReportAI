# AutoReportAI Makefile - 现代化测试和开发工具

.PHONY: help install install-dev install-test test test-all test-unit test-integration test-api test-agent test-charts test-docker test-minio test-e2e test-performance lint format clean coverage report services-up services-down docker-build docker-up docker-down

# ==========================================
# 变量定义
# ==========================================
# 检测Python环境
VENV_PYTHON := backend/venv/bin/python
VENV_PIP := backend/venv/bin/pip
PYTHON := $(shell if [ "$$CI" = "true" ] || [ "$$GITHUB_ACTIONS" = "true" ]; then echo "python"; elif [ -x "$(VENV_PYTHON)" ]; then echo "$(VENV_PYTHON)"; else echo "python3"; fi)
PIP := $(shell if [ "$$CI" = "true" ] || [ "$$GITHUB_ACTIONS" = "true" ]; then echo "pip"; elif [ -x "$(VENV_PYTHON)" ]; then echo "../venv/bin/pip"; else echo "pip3"; fi)
PYTEST := $(PYTHON) -m pytest
DOCKER_COMPOSE := docker-compose
TEST_RUNNER := $(PYTHON) run_tests.py
BACKEND_DIR := backend
FRONTEND_DIR := frontend
TESTS_DIR := tests
DEV_DIR := dev

# ==========================================
# 帮助信息
# ==========================================
help:
	@echo "AutoReportAI 开发工具"
	@echo ""
	@echo "安装命令:"
	@echo "  install        - 安装生产依赖"
	@echo "  install-dev    - 安装开发依赖"
	@echo "  install-test   - 安装测试依赖"
	@echo ""
	@echo "测试命令:"
	@echo "  test           - 运行快速测试套件"
	@echo "  test-all       - 运行完整测试套件"
	@echo "  test-unit      - 运行单元测试"
	@echo "  test-integration - 运行集成测试"
	@echo "  test-api       - 运行API测试"
	@echo "  test-agent     - 运行Agent测试"
	@echo "  test-charts    - 运行图表测试"
	@echo "  test-docker    - 运行Docker测试"
	@echo "  test-minio     - 运行Minio测试"
	@echo "  test-e2e       - 运行端到端测试"
	@echo "  test-performance - 运行性能测试"
	@echo ""
	@echo "代码质量:"
	@echo "  lint           - 代码质量检查"
	@echo "  format         - 代码格式化"
	@echo "  coverage       - 生成覆盖率报告"
	@echo "  report         - 打开覆盖率报告"
	@echo ""
	@echo "开发环境:"
	@echo "  services-up    - 启动核心服务(DB,Redis,Minio)"
	@echo "  services-down  - 停止核心服务"
	@echo "  docker-up      - 启动完整Docker环境"
	@echo "  docker-down    - 停止Docker环境"
	@echo "  clean          - 清理临时文件"

# ==========================================
# 安装命令
# ==========================================
install:
	@echo "📦 安装生产依赖..."
	$(PYTHON) -m pip install -r $(BACKEND_DIR)/requirements.txt
	cd $(FRONTEND_DIR) && npm install

install-dev:
	@echo "🔧 安装开发依赖..."
	$(PYTHON) -m pip install -r $(BACKEND_DIR)/requirements.txt
	cd $(FRONTEND_DIR) && npm install --include=dev

install-test: install-dev
	@echo "🧪 测试依赖已包含在requirements.txt中"

# ==========================================
# 测试系统
# ==========================================
test:
	@echo "🚀 运行快速测试套件..."
	@$(PYTHON) run_tests.py --unit --api --verbose

test-all:
	@echo "🏁 运行完整测试套件..."
	@$(PYTHON) run_tests.py --all --verbose

test-unit:
	@echo "🧪 运行单元测试..."
	@$(PYTHON) run_tests.py --unit --verbose

test-integration:
	@echo "🔗 运行集成测试..."
	@$(PYTHON) run_tests.py --integration --verbose

test-api:
	@echo "🌐 运行API测试..."
	@$(PYTHON) run_tests.py --api --verbose

test-agent:
	@echo "🤖 运行Agent测试..."
	@$(PYTHON) run_tests.py --agent --verbose

test-charts:
	@echo "📊 运行图表测试..."
	$(PYTHON) run_tests.py --charts --verbose

test-docker:
	@echo "🐳 运行Docker测试..."
	$(PYTHON) run_tests.py --docker --verbose

test-minio:
	@echo "📦 运行Minio测试..."
	$(PYTHON) run_tests.py --minio --verbose

test-e2e:
	@echo "🏁 运行端到端测试..."
	$(PYTHON) run_tests.py --e2e --verbose

test-performance:
	@echo "⚡ 运行性能测试..."
	$(PYTHON) run_tests.py --performance --verbose

# ==========================================
# 覆盖率和报告
# ==========================================
coverage:
	@echo "📈 生成覆盖率报告..."
	$(PYTHON) run_tests.py --coverage

report:
	@echo "📊 打开覆盖率报告..."
	@if command -v open >/dev/null 2>&1; then \
		open htmlcov/index.html; \
	elif command -v xdg-open >/dev/null 2>&1; then \
		xdg-open htmlcov/index.html; \
	else \
		echo "请手动打开 htmlcov/index.html"; \
	fi

# ==========================================
# 代码质量
# ==========================================
lint:
	@echo "🔍 运行代码质量检查..."
	$(PYTHON) run_tests.py --lint

format:
	@echo "🎨 代码格式化..."
	$(PYTHON) -m black $(BACKEND_DIR)/app $(TESTS_DIR)
	$(PYTHON) -m isort $(BACKEND_DIR)/app $(TESTS_DIR)
	cd $(FRONTEND_DIR) && npm run format 2>/dev/null || echo "前端格式化跳过"

# ==========================================
# 核心服务管理
# ==========================================
services-up:
	@echo "🔧 启动核心服务..."
	cd $(DEV_DIR) && $(DOCKER_COMPOSE) --env-file .env up -d db redis minio

services-down:
	@echo "🛑 停止核心服务..."
	cd $(DEV_DIR) && $(DOCKER_COMPOSE) stop db redis minio

# ==========================================
# Docker环境
# ==========================================
docker-build:
	@echo "🔨 构建Docker镜像..."
	cd $(DEV_DIR) && $(DOCKER_COMPOSE) build

docker-up:
	@echo "🚀 启动完整Docker环境..."
	cd $(DEV_DIR) && $(DOCKER_COMPOSE) --env-file .env up -d
	@echo "✅ Docker环境已启动"
	@echo "🌐 前端: http://localhost:3000"
	@echo "🔧 后端API: http://localhost:8000/docs"
	@echo "📦 Minio控制台: http://localhost:9001"

docker-down:
	@echo "🛑 停止Docker环境..."
	cd $(DEV_DIR) && $(DOCKER_COMPOSE) down

# ==========================================
# 清理命令
# ==========================================
clean:
	@echo "🧹 清理临时文件..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage .pytest_cache/ .mypy_cache/ coverage.xml
	cd $(FRONTEND_DIR) && rm -rf dist/ .next/ node_modules/.cache/ 2>/dev/null || true
	@echo "✅ 清理完成"

# ==========================================
# 开发工作流
# ==========================================
dev-setup: install-dev services-up
	@echo "🎉 开发环境设置完成!"

dev-test: services-up test-all
	@echo "🎯 开发环境测试完成"

# ==========================================
# 快捷命令别名
# ==========================================
t: test
ta: test-all
tu: test-unit
ti: test-integration
cov: coverage
up: docker-up
down: docker-down
build: docker-build