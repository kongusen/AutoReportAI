.PHONY: test test-ci test-complex test-relationships test-coverage lint format migrate test-db

# 环境变量
export DATABASE_URL ?= postgresql://test:test@localhost:5432/test_db
export PYTHONPATH := $(shell pwd)

# 颜色输出
GREEN := \033[32m
RED := \033[31m
YELLOW := \033[33m
NC := \033[0m

# 默认目标
help:
	@echo "$(GREEN)Enhanced Data Source CI/CD 测试工具$(NC)"
	@echo ""
	@echo "可用命令:"
	@echo "  $(YELLOW)make test$(NC)         - 运行所有测试"
	@echo "  $(YELLOW)make test-ci$(NC)      - 运行CI优化测试"
	@echo "  $(YELLOW)make test-complex$(NC) - 运行复杂场景测试"
	@echo "  $(YELLOW)make test-relationships$(NC) - 运行关系测试"
	@echo "  $(YELLOW)make test-coverage$(NC) - 运行覆盖率测试"
	@echo "  $(YELLOW)make migrate$(NC)      - 运行数据库迁移"
	@echo "  $(YELLOW)make lint$(NC)         - 代码检查"
	@echo "  $(YELLOW)make format$(NC)       - 代码格式化"
	@echo "  $(YELLOW)make clean$(NC)        - 清理测试数据"

# 安装依赖
install:
	@echo "$(GREEN)安装依赖...$(NC)"
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-asyncio black flake8

# 数据库迁移
migrate:
	@echo "$(GREEN)运行数据库迁移...$(NC)"
	alembic upgrade head

# 降级迁移
migrate-down:
	@echo "$(YELLOW)降级数据库迁移...$(NC)"
	alembic downgrade -1

# 重置数据库
reset-db:
	@echo "$(RED)重置数据库...$(NC)"
	alembic downgrade base
	alembic upgrade head

# 运行CI优化测试
test-ci:
	@echo "$(GREEN)运行CI/CD优化测试...$(NC)"
	python test_ci_cd.py

# 运行复杂场景测试
test-complex:
	@echo "$(GREEN)运行复杂场景测试...$(NC)"
	python test_complex_scenarios.py

# 运行关系测试
test-relationships:
	@echo "$(GREEN)运行关系测试...$(NC)"
	python test_relationships.py

# 运行单元测试
test-unit:
	@echo "$(GREEN)运行单元测试...$(NC)"
	pytest tests/ -v

# 运行覆盖率测试
test-coverage:
	@echo "$(GREEN)运行覆盖率测试...$(NC)"
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term

# 代码检查
lint:
	@echo "$(GREEN)运行代码检查...$(NC)"
	flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 app/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# 代码格式化
format:
	@echo "$(GREEN)格式化代码...$(NC)"
	black app/ --line-length 88
	black tests/ --line-length 88

# 验证Schema
validate-schema:
	@echo "$(GREEN)验证Schema一致性...$(NC)"
	python -c "
from app.db.session import engine
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print('Tables:', tables)
assert 'enhanced_data_sources' in tables
assert 'etl_jobs' in tables
print('✅ Schema validation passed')
"

# 性能基准测试
perf-test:
	@echo "$(GREEN)运行性能基准测试...$(NC)"
	python -c "
import time
from test_ci_cd import CICDTester
tester = CICDTester()
start = time.time()
result = tester.test_performance_baseline()
duration = time.time() - start
print(f'Performance test: {duration:.2f}s')
assert result, 'Performance test failed'
"

# 完整测试流程
test: install migrate test-ci test-unit validate-schema
	@echo "$(GREEN)所有测试完成！$(NC)"

# 清理
clean:
	@echo "$(YELLOW)清理测试数据...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage

# 开发环境设置
dev-setup: install migrate test-relationships
	@echo "$(GREEN)开发环境设置完成！$(NC)"

# 生产环境检查
prod-check: lint test-coverage
	@echo "$(GREEN)生产环境检查完成！$(NC)"
