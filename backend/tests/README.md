# AutoReportAI 测试套件

## 目录结构

```
tests/
├── README.md                    # 测试说明文档
├── conftest.py                  # pytest配置文件
├── run_api_tests.py            # API测试运行器
├── final_api_test_summary.py   # 核心功能测试
├── comprehensive_api_test.py   # 全面API测试
├── configure_ai_provider.py    # AI提供商配置测试
├── reports/                    # 测试报告目录
│   └── API_TEST_REPORT.md     # API测试报告
├── scripts/                    # 测试脚本
│   ├── test_backend_final.py  # 端到端测试
│   ├── test_backend_simple.py # 简单功能测试
│   └── test_v2_api.py        # v2 API测试
├── e2e/                       # 端到端测试
├── frontend_api/              # 前端API测试
├── integration/               # 集成测试
└── test_data/                # 测试数据
```

## 测试类型

### 1. API功能测试
- **final_api_test_summary.py**: 核心功能快速测试
- **comprehensive_api_test.py**: 全面API功能测试
- **configure_ai_provider.py**: AI提供商配置测试

### 2. 端到端测试
- **scripts/test_backend_final.py**: 完整业务流程测试
- **scripts/test_backend_simple.py**: 简单功能验证

### 3. 集成测试
- **integration/**: 组件集成测试
- **e2e/**: 端到端场景测试

## 运行测试

### 运行所有API测试
```bash
make test-api
```

### 运行核心功能测试
```bash
make test-core
```

### 运行端到端测试
```bash
make test-e2e
```

### 运行单个测试脚本
```bash
# 核心功能测试
python tests/final_api_test_summary.py

# 全面API测试
python tests/comprehensive_api_test.py

# AI提供商配置
python tests/configure_ai_provider.py

# 统一测试运行器
python tests/run_api_tests.py
```

## 测试报告

测试报告位于 `tests/reports/` 目录中：
- `API_TEST_REPORT.md`: 详细的API测试报告
- `api_test_report_YYYYMMDD_HHMMSS.md`: 时间戳命名的测试报告

## 测试数据

测试数据位于 `tests/test_data/` 目录中：
- `csv_data/`: CSV格式测试数据
- `json_data/`: JSON格式测试数据
- `fixtures/`: 测试夹具
- `sample_files/`: 示例文件

## 测试配置

### 环境要求
- 后端服务运行在 `http://localhost:8000`
- 数据库连接正常
- Redis服务可用

### 测试用户
测试会自动创建临时用户，格式为：
- 用户名: `testuser_{unique_id}`
- 邮箱: `test_{unique_id}@example.com`
- 密码: `TestPass123!`

### AI提供商配置
测试会配置以下AI提供商：
- **小爱AI**: OpenAI兼容的API服务
- **API地址**: https://xiaoai.com/api/v1/chat/completions
- **模型**: gpt-4o-mini

## 测试结果解读

### 成功指标
- ✅ 健康检查通过
- ✅ 用户认证正常
- ✅ 数据源管理正常
- ✅ 模板管理正常
- ✅ AI提供商配置正常
- ✅ API端点响应正常

### 失败排查
1. 检查后端服务是否运行
2. 检查数据库连接
3. 检查API端点路径
4. 检查认证令牌
5. 检查请求参数格式

## 持续集成

测试套件支持CI/CD集成：
```bash
# 运行所有测试并生成覆盖率报告
make test-ci

# 运行API测试
make test-api

# 运行端到端测试
make test-e2e
```

## 注意事项

1. **测试隔离**: 每个测试使用唯一的用户和数据
2. **数据清理**: 测试完成后会自动清理测试数据
3. **并发安全**: 测试脚本支持并发运行
4. **错误处理**: 包含详细的错误信息和调试信息

## 更新日志

- **2025-08-07**: 创建API测试套件
- **2025-08-07**: 添加AI提供商配置测试
- **2025-08-07**: 完善测试报告生成
- **2025-08-07**: 整理测试目录结构 