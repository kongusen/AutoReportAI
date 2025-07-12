# CI/CD 测试系统设置指南

## 概述

本项目已经配置了完整的CI/CD流水线，包括：
- 代码质量检查（linting, formatting）
- 自动化测试（后端和前端）
- Docker镜像构建
- 安全扫描
- 自动部署

## 本地开发和测试

### 快速开始

```bash
# 查看所有可用命令
make help

# 安装所有依赖
make install

# 运行所有测试
make test

# 运行代码格式化
make format

# 运行代码检查
make lint
```

### 后端测试

```bash
# 启动测试数据库
make test-db

# 运行后端测试
make test-backend

# 使用Docker运行测试
make test-docker
```

### 前端测试

```bash
# 运行前端测试
make test-frontend

# 运行前端测试（观察模式）
cd frontend && npm run test:watch
```

## CI/CD 流水线

### 触发条件

CI/CD流水线会在以下情况下自动触发：
- 推送到 `main` 或 `develop` 分支
- 创建或更新 Pull Request

### 流水线阶段

1. **代码质量检查** (`quality-check`)
   - Python代码：flake8, black, isort, mypy
   - TypeScript代码：ESLint, Prettier
   - 并行运行，快速反馈

2. **后端测试** (`backend-test`)
   - 使用PostgreSQL服务
   - 运行pytest测试套件
   - 生成代码覆盖率报告
   - 上传覆盖率到Codecov

3. **前端测试** (`frontend-test`)
   - 运行Jest测试套件
   - 生成代码覆盖率报告
   - 上传覆盖率到Codecov

4. **构建Docker镜像** (`build-images`)
   - 仅在main分支触发
   - 构建backend, frontend, scheduler镜像
   - 推送到GitHub Container Registry

5. **安全扫描** (`security-scan`)
   - 使用Trivy扫描Docker镜像
   - 上传结果到GitHub Security tab

6. **部署** (`deploy-staging`, `deploy-production`)
   - Staging环境：自动部署
   - Production环境：需要手动批准

### 环境配置

#### GitHub Secrets

需要在GitHub仓库设置中配置以下secrets：

```bash
# 如果使用外部数据库
DATABASE_URL=postgresql://user:password@host:port/dbname

# 如果使用外部容器仓库
DOCKER_REGISTRY_USERNAME=your_username
DOCKER_REGISTRY_PASSWORD=your_password

# 如果使用云服务部署
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

#### 环境变量

- `REGISTRY`: 容器镜像仓库地址
- `IMAGE_NAME`: 镜像名称前缀

## 代码质量标准

### Python代码标准

- **代码风格**: 使用Black格式化，最大行长度88字符
- **导入排序**: 使用isort，兼容Black配置
- **代码检查**: 使用flake8，忽略与Black冲突的规则
- **类型检查**: 使用mypy进行静态类型检查

### TypeScript代码标准

- **代码风格**: 使用Prettier格式化
- **代码检查**: 使用ESLint with Next.js配置
- **类型检查**: 使用TypeScript编译器检查

### 测试覆盖率要求

- **后端**: 最低70%代码覆盖率
- **前端**: 最低70%代码覆盖率

## 故障排除

### 常见问题

1. **测试数据库连接失败**
   ```bash
   # 检查测试数据库是否运行
   make test-db
   
   # 查看数据库日志
   docker-compose -f docker-compose.test.yml logs test_db
   ```

2. **代码格式检查失败**
   ```bash
   # 自动修复格式问题
   make format
   ```

3. **依赖安装失败**
   ```bash
   # 清理缓存并重新安装
   make clean
   make install
   ```

4. **Docker镜像构建失败**
   ```bash
   # 本地构建测试
   docker-compose build
   
   # 查看构建日志
   docker-compose build --no-cache
   ```

### 调试技巧

1. **查看GitHub Actions日志**
   - 进入GitHub仓库的Actions页面
   - 点击失败的workflow
   - 查看详细的步骤日志

2. **本地复现CI环境**
   ```bash
   # 使用相同的Python版本
   python --version  # 应该是3.11
   
   # 使用相同的Node.js版本
   node --version    # 应该是18.x
   
   # 运行相同的测试命令
   make test
   ```

3. **检查代码覆盖率**
   ```bash
   # 生成详细的覆盖率报告
   cd backend && pytest --cov=app --cov-report=html
   # 在浏览器中打开 backend/htmlcov/index.html
   
   cd frontend && npm run test:coverage
   # 在浏览器中打开 frontend/coverage/lcov-report/index.html
   ```

## 最佳实践

1. **提交前检查**
   ```bash
   # 运行完整的检查
   make lint
   make test
   ```

2. **分支策略**
   - `main`: 生产环境代码
   - `develop`: 开发环境代码
   - `feature/*`: 功能分支
   - `hotfix/*`: 紧急修复分支

3. **Pull Request检查清单**
   - [ ] 所有测试通过
   - [ ] 代码覆盖率达标
   - [ ] 代码风格检查通过
   - [ ] 文档更新（如需要）
   - [ ] 没有安全漏洞

4. **部署检查清单**
   - [ ] 所有CI/CD步骤通过
   - [ ] 安全扫描无高危漏洞
   - [ ] 数据库迁移脚本准备就绪
   - [ ] 环境变量配置正确
   - [ ] 回滚计划准备就绪

## 监控和告警

### 覆盖率监控

- Codecov集成提供覆盖率趋势
- 覆盖率下降时会在PR中显示警告

### 安全监控

- GitHub Security tab显示安全扫描结果
- 高危漏洞会阻止部署

### 性能监控

- 构建时间监控
- 测试执行时间监控
- Docker镜像大小监控

## 扩展和定制

### 添加新的测试步骤

1. 在 `.github/workflows/ci-cd.yml` 中添加新的job
2. 更新 `Makefile` 添加对应的命令
3. 更新本文档

### 添加新的部署环境

1. 在GitHub仓库设置中创建新的Environment
2. 配置环境特定的secrets
3. 在workflow中添加新的部署job

### 自定义代码质量规则

1. 修改 `backend/.flake8` 或 `backend/pyproject.toml`
2. 修改 `frontend/.eslintrc.js` 或 `frontend/.prettierrc`
3. 更新CI workflow中的相应步骤 