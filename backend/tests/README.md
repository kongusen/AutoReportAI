# 测试框架文档

## 测试结构概览

本项目的测试框架已经搭建完成，包含以下测试模块：

### 1. API 测试 (`tests/api/`)

- **`test_tasks.py`** - 任务管理API端点测试
  - 任务创建、状态查询、批量处理
  - 异步任务执行和监控
  - 错误处理和重试机制

- **`test_reports.py`** - 报告生成API端点测试
  - 报告生成工作流
  - 模板解析和占位符处理
  - 输出格式支持和质量控制

- **`test_settings.py`** - 设置管理API端点测试
  - AI模型配置管理
  - LLM服务器设置
  - 系统参数调优

### 2. 服务层测试 (`tests/services/`)

- **`test_data_processing.py`** - 数据处理服务测试
  - 模式感知数据分析
  - 可视化服务
  - 数据结构分析

- **`test_application_services.py`** - 应用层服务测试
  - 统一服务门面 (`UnifiedServiceFacade`)
  - 增强报告生成工作流 (`EnhancedReportGenerationWorkflow`)
  - 上下文构建器测试

### 3. 集成测试 (`tests/integration/`)

- **`test_api_integration.py`** - API集成测试
  - 端到端工作流测试
  - 服务间协作验证
  - 错误处理和恢复测试
  - 性能和并发测试

## 测试配置

### 全局配置 (`tests/conftest.py`)

提供了以下测试fixtures：
- 数据库会话管理
- 模拟用户和认证
- 测试数据工厂
- 性能监控工具
- 清理机制

### 环境变量
测试运行时会自动设置：
```
TESTING=1
DATABASE_URL=sqlite:///test.db
REDIS_URL=redis://localhost:6379/1
SECRET_KEY=test-secret-key-for-testing-only
```

## 运行测试

### 运行所有测试
```bash
pytest tests/ -v
```

### 运行特定模块
```bash
pytest tests/api/ -v
pytest tests/services/ -v
pytest tests/integration/ -v
```

### 运行单个测试文件
```bash
pytest tests/api/test_tasks.py -v
```

### 运行特定测试用例
```bash
pytest tests/api/test_tasks.py::TestTaskAPI::test_create_task -v
```

### 生成测试覆盖率报告
```bash
pytest tests/ --cov=app --cov-report=html
```

## 测试覆盖范围

### API端点测试覆盖
- ✅ 任务管理 API (创建、查询、批量处理)
- ✅ 报告生成 API (生成、状态查询、下载)
- ✅ 设置管理 API (AI配置、LLM服务器、系统设置)
- ✅ 图表生成 API (生成、优化、数据分析)

### 服务层测试覆盖
- ✅ 数据处理服务 (分析、可视化、结构解析)
- ✅ 应用层工作流 (报告生成、任务管理)
- ✅ 统一服务门面 (图表生成、数据分析)
- ✅ 上下文构建器 (时间、业务、文档上下文)

### 集成测试覆盖
- ✅ 完整报告生成工作流
- ✅ 图表生成和优化工作流
- ✅ 数据分析到图表推荐工作流
- ✅ 异步任务创建和监控
- ✅ 错误处理和恢复机制
- ✅ 并发性能测试

## 测试数据和模拟

### 测试数据工厂
- 用户数据生成
- 模板数据生成
- 数据源配置生成
- 任务数据生成

### 服务模拟
- Redis 缓存模拟
- Celery 任务队列模拟
- LLM 客户端模拟
- 数据连接器模拟

## 最佳实践

1. **测试独立性** - 每个测试都是独立的，不依赖其他测试的状态
2. **数据清理** - 自动清理测试产生的临时文件和数据
3. **模拟外部依赖** - 使用mock对象替代真实的外部服务
4. **异步测试支持** - 使用 `pytest-asyncio` 支持异步代码测试
5. **性能监控** - 集成性能监控工具，跟踪测试执行时间和内存使用

## 待改进项

1. **数据库集成测试** - 需要配置真实数据库进行集成测试
2. **端到端测试** - 完善完整业务流程的端到端测试
3. **负载测试** - 添加高并发和大数据量的压力测试
4. **安全测试** - 增加API安全性和权限控制测试

## 依赖要求

测试框架需要以下Python包：
```
pytest>=7.4.3
pytest-asyncio>=0.21.1
pytest-mock>=3.12.0
pytest-cov>=4.0.0
httpx>=0.28.1
aiosqlite>=0.21.0
```

确保在运行测试前安装这些依赖：
```bash
pip install pytest pytest-asyncio pytest-mock pytest-cov httpx aiosqlite
```