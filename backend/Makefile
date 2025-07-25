.PHONY: help install test test-unit test-integration test-e2e test-all test-ci lint format clean

# 默认目标
help:
	@echo "AutoReportAI 后端测试命令"
	@echo "========================"
	@echo "install      - 安装测试依赖"
	@echo "test         - 运行所有测试"
	@echo "test-unit    - 运行单元测试"
	@echo "test-integration - 运行集成测试"
	@echo "test-e2e     - 运行端到端测试"
	@echo "test-ci      - CI环境测试"
	@echo "lint         - 代码检查"
	@echo "format       - 代码格式化"
	@echo "clean        - 清理测试数据"
	@echo "coverage     - 生成测试覆盖率报告"

# 安装测试依赖
install:
	pip install -r requirements/development.txt

# 运行所有测试
test:
	python test_runner.py

# 运行单元测试
test-unit:
	python -m pytest tests/unit -v --tb=short

# 运行集成测试
test-integration:
	python -m pytest tests/integration -v --tb=short

# 运行端到端测试
test-e2e:
	python test_backend_final.py

# CI环境测试
test-ci:
	python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term --cov-fail-under=80

# 代码检查
lint:
	flake8 app tests
	black --check app tests
	isort --check-only app tests

# 代码格式化
format:
	black app tests
	isort app tests

# 清理测试数据
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml

# 生成测试覆盖率报告
coverage:
	python -m pytest tests/ --cov=app --cov-report=html --cov-report=term
	@echo "覆盖率报告已生成: htmlcov/index.html"

# 启动测试环境
test-server:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 检查后端状态
check-backend:
	@curl -s http://localhost:8000/api/v2/system/health || echo "后端未运行"

# 快速测试（仅端到端）
test-quick:
	python test_backend_final.py

# 调试模式测试
test-debug:
	python -m pytest tests/ -v --tb=long --log-cli-level=DEBUG
