.PHONY: test test-unit test-integration test-e2e test-coverage lint format migrate init-db clean dev-setup docs docs-generate docs-validate docs-serve

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
	@echo "$(GREEN)Backend Project Management Tool$(NC)"
	@echo ""
	@echo "可用命令:"
	@echo "  $(YELLOW)make test$(NC)         - 运行所有测试"
	@echo "  $(YELLOW)make test-unit$(NC)    - 运行单元测试"
	@echo "  $(YELLOW)make test-integration$(NC) - 运行集成测试"
	@echo "  $(YELLOW)make test-e2e$(NC)     - 运行端到端测试"
	@echo "  $(YELLOW)make test-coverage$(NC) - 运行覆盖率测试"
	@echo "  $(YELLOW)make migrate$(NC)      - 运行数据库迁移"
	@echo "  $(YELLOW)make init-db$(NC)      - 初始化数据库"
	@echo "  $(YELLOW)make lint$(NC)         - 代码检查"
	@echo "  $(YELLOW)make format$(NC)       - 代码格式化"
	@echo "  $(YELLOW)make clean$(NC)        - 清理测试数据"
	@echo "  $(YELLOW)make dev-setup$(NC)    - 开发环境设置"
	@echo "  $(YELLOW)make docs$(NC)         - 生成和验证API文档"
	@echo "  $(YELLOW)make docs-generate$(NC) - 生成API文档"
	@echo "  $(YELLOW)make docs-validate$(NC) - 验证API文档"
	@echo "  $(YELLOW)make docs-serve$(NC)   - 启动文档服务器"

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

# 初始化数据库
init-db:
	@echo "$(GREEN)初始化数据库...$(NC)"
	python scripts/init_db.py

# 配置AI提供商
configure-ai:
	@echo "$(GREEN)配置AI提供商...$(NC)"
	python scripts/configure_ai_provider.py

# 运行单元测试
test-unit:
	@echo "$(GREEN)运行单元测试...$(NC)"
	pytest tests/unit/ -v -m "not slow"

# 运行集成测试
test-integration:
	@echo "$(GREEN)运行集成测试...$(NC)"
	pytest tests/integration/ -v

# 运行端到端测试
test-e2e:
	@echo "$(GREEN)运行端到端测试...$(NC)"
	pytest tests/e2e/ -v

# 运行简单E2E测试
test-e2e-simple:
	@echo "$(GREEN)运行简单端到端测试...$(NC)"
	python scripts/run_simple_e2e_test.py

# 运行完整E2E集成测试
test-e2e-full:
	@echo "$(GREEN)运行完整端到端集成测试...$(NC)"
	python scripts/run_e2e_integration_tests.py

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
	python -c "\
from app.db.session import engine; \
from sqlalchemy import inspect; \
inspector = inspect(engine); \
tables = inspector.get_table_names(); \
print('Tables:', tables); \
assert 'enhanced_data_sources' in tables; \
assert 'etl_jobs' in tables; \
print('✅ Schema validation passed')"

# 性能基准测试
perf-test:
	@echo "$(GREEN)运行性能基准测试...$(NC)"
	pytest tests/integration/test_performance_benchmarks.py -v

# 完整测试流程
test: install migrate test-unit test-integration validate-schema
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
dev-setup: install migrate init-db test-unit
	@echo "$(GREEN)开发环境设置完成！$(NC)"

# 生产环境检查
prod-check: lint test-coverage
	@echo "$(GREEN)生产环境检查完成！$(NC)"

# API文档生成和验证
docs: docs-generate docs-validate
	@echo "$(GREEN)✅ API文档生成和验证完成$(NC)"

# 文档生成相关命令
.PHONY: docs-generate docs-update docs-serve docs-clean

docs-generate:
	@echo "🚀 生成API文档..."
	@cd $(BACKEND_DIR) && python scripts/generate_api_docs.py

docs-update:
	@echo "🔄 更新API文档..."
	@cd $(BACKEND_DIR) && python scripts/update_api_docs.py --force

docs-watch:
	@echo "👀 监控API文档变更..."
	@cd $(BACKEND_DIR) && python scripts/update_api_docs.py --watch

docs-serve:
	@echo "🌐 启动文档服务器..."
	@cd $(BACKEND_DIR)/docs/api && python -m http.server 8080

docs-clean:
	@echo "🧹 清理生成的文档..."
	@rm -rf $(BACKEND_DIR)/docs/api/generated
	@rm -f $(BACKEND_DIR)/docs/api/.api_cache.json
