# AutoReportAI 测试套件

> 完整的测试框架，支持单元测试、集成测试、端到端测试和性能测试

## 📁 目录结构

```
tests/
├── __init__.py                 # 测试套件初始化
├── conftest.py                 # pytest配置和fixtures
├── README.md                   # 测试文档 (本文件)
├── fixtures/                   # 测试数据和模拟文件
│
├── unit/                       # 单元测试
│   ├── test_models.py         # 数据模型测试
│   ├── test_services.py       # 服务层测试
│   └── test_utils.py          # 工具函数测试
│
├── integration/                # 集成测试
│   ├── test_llm_connection.py # LLM集成测试
│   ├── test_database.py       # 数据库集成测试
│   └── test_redis.py          # Redis集成测试
│
├── api/                        # API测试
│   ├── test_fixed_apis.py     # 修复后的API测试
│   ├── test_frontend_connection.py # 前端连接测试
│   ├── test_auth.py           # 认证API测试
│   └── test_endpoints.py      # 端点测试
│
├── agent/                      # React Agent测试
│   ├── test_agent_chart_generation.py # Agent图表生成
│   ├── test_agent_doris_complete.py   # Agent完整Doris测试
│   └── test_agent_doris_sql.py        # Agent SQL测试
│
├── charts/                     # 图表测试
│   ├── test_chinese_charts.py        # 中文图表测试
│   └── test_final_chinese_charts.py  # 最终中文图表测试
│
├── docker/                     # Docker环境测试
│   ├── test_docker_fonts.py          # Docker字体测试
│   └── test_docker_fonts_simple.sh   # 简单字体测试脚本
│
├── minio/                      # 对象存储测试
│   ├── test_minio_integration.py     # Minio集成测试
│   └── test_minio_simple.sh          # 简单Minio测试脚本
│
├── e2e/                        # 端到端测试
│   └── test_real_business_flow.py    # 真实业务流程测试
│
└── performance/                # 性能测试
    ├── test_load.py           # 负载测试
    ├── test_memory.py         # 内存使用测试
    └── test_response_time.py  # 响应时间测试
```

## 🚀 快速开始

### 1. 安装测试依赖

```bash
# 安装所有测试依赖
pip install -r requirements-test.txt

# 或者只安装核心测试框架
pip install pytest pytest-asyncio pytest-cov
```

### 2. 运行测试

```bash
# 使用测试运行器（推荐）
python run_tests.py --help

# 运行所有测试
python run_tests.py --all

# 运行特定类型的测试
python run_tests.py --unit --integration
python run_tests.py --agent --charts
python run_tests.py --docker --minio

# 直接使用pytest
pytest tests/unit/
pytest tests/integration/ -v
pytest tests/ --cov=backend/app
```

### 3. 查看测试报告

```bash
# 生成HTML覆盖率报告
python run_tests.py --coverage
open htmlcov/index.html

# 运行代码质量检查
python run_tests.py --lint
```

## 📊 测试分类

### 单元测试 (Unit Tests)
- **目标**: 测试独立的函数、类和方法
- **特点**: 快速、隔离、无外部依赖
- **标记**: `@pytest.mark.unit`
- **位置**: `tests/unit/`

```python
@pytest.mark.unit
def test_data_processing_function():
    result = process_data([1, 2, 3])
    assert result == [2, 4, 6]
```

### 集成测试 (Integration Tests)
- **目标**: 测试组件间的交互
- **特点**: 涉及数据库、Redis、外部服务
- **标记**: `@pytest.mark.integration`
- **位置**: `tests/integration/`

```python
@pytest.mark.integration
async def test_database_connection():
    async with get_db_session() as session:
        result = await session.execute("SELECT 1")
        assert result.scalar() == 1
```

### API测试 (API Tests)
- **目标**: 测试HTTP API端点
- **特点**: 使用HTTP客户端测试实际API
- **标记**: `@pytest.mark.api`
- **位置**: `tests/api/`

```python
@pytest.mark.api
async def test_get_templates(client):
    response = await client.get("/api/v1/templates/")
    assert response.status_code == 200
```

### Agent测试 (Agent Tests)
- **目标**: 测试React Agent功能
- **特点**: 涉及LLM调用、工具使用
- **标记**: `@pytest.mark.agent`
- **位置**: `tests/agent/`

### 图表测试 (Charts Tests)
- **目标**: 测试图表生成功能
- **特点**: 验证图片生成、中文支持
- **标记**: `@pytest.mark.charts`
- **位置**: `tests/charts/`

### Docker测试 (Docker Tests)
- **目标**: 测试Docker环境配置
- **特点**: 字体、依赖、环境变量
- **标记**: `@pytest.mark.docker`
- **位置**: `tests/docker/`

### Minio测试 (Minio Tests)
- **目标**: 测试对象存储功能
- **特点**: 文件上传、下载、管理
- **标记**: `@pytest.mark.minio`
- **位置**: `tests/minio/`

### 端到端测试 (E2E Tests)
- **目标**: 测试完整的用户流程
- **特点**: 跨服务、真实场景
- **标记**: `@pytest.mark.e2e`
- **位置**: `tests/e2e/`

### 性能测试 (Performance Tests)
- **目标**: 测试系统性能指标
- **特点**: 负载、内存、响应时间
- **标记**: `@pytest.mark.performance`
- **位置**: `tests/performance/`

## 🛠️ 测试配置

### pytest.ini
核心pytest配置，包括：
- 测试发现规则
- 覆盖率配置
- 标记定义
- 警告过滤

### conftest.py
提供测试fixtures：
- `setup_test_env`: 测试环境变量
- `mock_openai_client`: 模拟LLM客户端
- `sample_data`: 测试数据
- `temp_storage_dir`: 临时存储目录

### 环境配置
- `.env.test`: 测试环境变量
- `requirements-test.txt`: 测试依赖

## 📋 测试最佳实践

### 1. 命名约定
```python
# ✅ 好的测试命名
def test_user_can_create_template_with_valid_data():
def test_chart_generation_fails_with_invalid_data():
def test_agent_returns_error_when_llm_unavailable():

# ❌ 差的测试命名
def test_template():
def test_chart():
def test_agent():
```

### 2. 测试结构 (AAA模式)
```python
def test_something():
    # Arrange - 准备测试数据
    user = User(name="test")
    template = Template(name="test template")
    
    # Act - 执行被测试的操作
    result = user.create_template(template)
    
    # Assert - 验证结果
    assert result.success
    assert result.template.id is not None
```

### 3. 使用Fixtures
```python
@pytest.fixture
def user():
    return User(name="test_user")

@pytest.fixture  
def template(user):
    return user.create_template("test template")

def test_template_usage(template):
    assert template.name == "test template"
```

### 4. 参数化测试
```python
@pytest.mark.parametrize("input,expected", [
    ("北京", "beijing"),
    ("上海", "shanghai"),
    ("深圳", "shenzhen"),
])
def test_city_name_conversion(input, expected):
    result = convert_city_name(input)
    assert result == expected
```

### 5. 异步测试
```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result is not None
```

### 6. 异常测试
```python
def test_function_raises_exception_with_invalid_input():
    with pytest.raises(ValueError, match="Invalid input"):
        process_invalid_data("bad data")
```

### 7. 跳过和条件测试
```python
@pytest.mark.skipif(sys.platform == "win32", reason="Unix only")
def test_unix_feature():
    pass

@pytest.mark.skip_if_no_docker
def test_docker_functionality():
    pass
```

## 🔧 常用命令

### 基础测试命令
```bash
# 运行所有测试
pytest

# 详细输出
pytest -v

# 运行特定文件
pytest tests/unit/test_models.py

# 运行特定测试函数
pytest tests/unit/test_models.py::test_user_creation

# 运行匹配模式的测试
pytest -k "test_user"

# 运行特定标记的测试
pytest -m "unit"
pytest -m "integration and not slow"
```

### 覆盖率相关
```bash
# 生成覆盖率报告
pytest --cov=backend/app

# 生成HTML覆盖率报告
pytest --cov=backend/app --cov-report=html

# 只显示缺少覆盖的行
pytest --cov=backend/app --cov-report=term-missing

# 覆盖率失败阈值
pytest --cov=backend/app --cov-fail-under=80
```

### 并行测试
```bash
# 安装pytest-xdist
pip install pytest-xdist

# 并行运行测试
pytest -n auto
pytest -n 4  # 使用4个进程
```

### 调试相关
```bash
# 遇到失败时进入调试器
pytest --pdb

# 捕获输出
pytest -s

# 显示最慢的10个测试
pytest --durations=10
```

## 🎯 覆盖率目标

| 组件 | 目标覆盖率 | 当前状态 |
|------|-----------|----------|
| Models | ≥95% | 🔄 待提升 |
| Services | ≥90% | 🔄 待提升 |
| API Endpoints | ≥85% | 🔄 待提升 |
| Utilities | ≥95% | 🔄 待提升 |
| Agent Tools | ≥80% | 🔄 待提升 |
| **总体目标** | **≥85%** | **🔄 待提升** |

## 📈 持续集成

### GitHub Actions工作流
- **lint**: 代码质量检查
- **unit-tests**: 单元测试 (多Python版本)
- **integration-tests**: 集成测试 (带服务)
- **docker-tests**: Docker环境测试
- **frontend-tests**: 前端测试
- **e2e-tests**: 端到端测试
- **performance-tests**: 性能测试
- **security-scan**: 安全扫描

### 本地测试钩子
```bash
# 安装pre-commit钩子
pip install pre-commit
pre-commit install

# 手动运行钩子
pre-commit run --all-files
```

## 🐛 调试测试

### 1. 使用pytest的调试功能
```bash
# 进入Python调试器
pytest --pdb

# 遇到失败时自动进入调试器
pytest --pdb-trace
```

### 2. 使用日志
```python
import logging

def test_with_logging():
    logging.info("测试开始")
    result = complex_operation()
    logging.debug(f"中间结果: {result}")
    assert result.success
```

### 3. 临时调试标记
```python
@pytest.mark.debug  # 临时标记
def test_problematic_function():
    pass

# 只运行调试测试
pytest -m debug
```

## 📝 贡献指南

### 添加新测试
1. 选择合适的测试类别
2. 创建测试文件 (`test_*.py`)
3. 添加适当的标记
4. 编写测试文档
5. 更新覆盖率目标

### 测试代码审查清单
- [ ] 测试命名清晰描述测试内容
- [ ] 使用AAA模式组织测试
- [ ] 适当使用fixtures避免重复代码
- [ ] 添加必要的pytest标记
- [ ] 测试覆盖正常和异常情况
- [ ] 异步代码使用`@pytest.mark.asyncio`
- [ ] 包含必要的文档字符串

## 🔗 相关资源

- [pytest官方文档](https://docs.pytest.org/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [pytest-cov](https://github.com/pytest-dev/pytest-cov)
- [Factory Boy](https://factoryboy.readthedocs.io/)
- [Faker](https://faker.readthedocs.io/)

---

**测试愉快! 🎉** 记住：好的测试让重构变得安全，让新功能开发更有信心！