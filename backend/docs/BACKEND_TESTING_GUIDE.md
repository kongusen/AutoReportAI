# AutoReportAI 后端测试指南

## 概述

本文档提供了AutoReportAI后端系统的完整测试指南，包括单元测试、集成测试和端到端测试。

## 测试架构

### 测试类型
- **单元测试**: 测试单个组件和函数
- **集成测试**: 测试组件间的交互
- **端到端测试**: 测试完整用户工作流

### 测试文件结构
```
backend/
├── tests/
│   ├── unit/           # 单元测试
│   ├── integration/    # 集成测试
│   ├── e2e/           # 端到端测试
│   └── conftest.py    # 测试配置
├── test_backend_final.py  # 端到端测试脚本
├── test_runner.py     # 测试运行器
└── docs/
    └── BACKEND_TESTING_GUIDE.md
```

## 快速开始

### 1. 环境准备

确保后端服务已正确配置：

```bash
# 安装依赖
cd backend
pip install -r requirements/development.txt

# 启动后端服务
make run-backend
```

### 2. 运行测试

#### 使用测试运行器（推荐）

```bash
# 运行所有测试
python test_runner.py

# 运行特定类型测试
python test_runner.py --mode unit
python test_runner.py --mode integration
python test_runner.py --mode e2e

# 查看帮助
python test_runner.py --help
```

#### 直接运行测试脚本

```bash
# 运行端到端测试
python test_backend_final.py

# 运行pytest测试
python -m pytest tests/ -v
```

## 端到端测试流程

### 测试覆盖的功能

1. **用户管理**
   - 用户注册
   - 用户登录
   - 用户信息更新

2. **数据源管理**
   - 创建数据源
   - 验证数据源连接
   - 数据源列表查询

3. **模板管理**
   - 创建模板
   - 模板验证
   - 模板列表查询

4. **任务管理**
   - 创建任务
   - 任务列表查询

5. **ETL作业管理**
   - 创建ETL作业
   - ETL作业列表查询

6. **报告生成**
   - 生成报告
   - 报告历史查询

7. **仪表板**
   - 获取统计数据
   - 系统概览

### 测试数据

测试使用以下数据：
- 用户名: `testuser_[随机ID]`
- 邮箱: `test_[随机ID]@example.com`
- 密码: `TestPass123!`
- 数据源: SQLite测试数据库
- 模板: 包含智能占位符的测试模板

## 测试用例详情

### 1. 健康检查测试
验证后端服务是否正常运行。

### 2. 用户工作流测试
完整测试用户从注册到生成报告的全流程：
1. 用户注册
2. 用户登录
3. 创建数据源
4. 创建模板
5. 创建任务
6. 创建ETL作业
7. 生成报告
8. 验证数据

### 3. 错误处理测试
测试各种错误情况：
- 无效的用户注册数据
- 错误的登录凭据
- 未授权访问
- 无效的数据格式

### 4. 性能测试
- API响应时间测试
- 并发操作测试
- 批量操作测试

## 测试配置

### 环境变量
```bash
# 测试数据库
DATABASE_URL=sqlite:///./test.db

# 测试API配置
API_V2_STR=/api/v2
```

### 测试依赖
- `pytest`: 测试框架
- `requests`: HTTP客户端
- `uuid`: 生成唯一标识符

## 常见问题

### 1. 测试失败
- 确保后端服务已启动
- 检查端口8000是否被占用
- 验证数据库连接

### 2. 权限错误
- 检查JWT令牌是否正确
- 确认用户权限设置

### 3. 数据验证失败
- 检查输入数据格式
- 验证数据源连接字符串

## 扩展测试

### 添加新测试用例

1. **单元测试**
```python
# tests/unit/test_new_feature.py
def test_new_feature():
    assert new_feature() == expected_result
```

2. **集成测试**
```python
# tests/integration/test_new_integration.py
def test_api_integration(client):
    response = client.post("/api/v2/endpoint", json=data)
    assert response.status_code == 201
```

3. **端到端测试**
在 `test_backend_final.py` 中添加新的测试方法。

## 持续集成

### GitHub Actions 配置
测试已集成到CI/CD流程中，每次提交都会自动运行：
- 单元测试
- 集成测试
- 代码覆盖率检查

### 本地CI测试
```bash
# 模拟CI环境测试
make test-ci
```

## 最佳实践

1. **测试命名**
   - 使用描述性名称
   - 遵循 `test_` 前缀约定

2. **测试数据**
   - 使用唯一标识符避免冲突
   - 清理测试数据

3. **错误处理**
   - 提供清晰的错误信息
   - 记录测试失败详情

4. **性能测试**
   - 设置合理的超时时间
   - 监控响应时间

## 支持

如有问题，请查看：
- 项目文档: `docs/`
- 错误日志: `logs/`
- GitHub Issues: [项目仓库](https://github.com/kongusen/AutoReportAI)
