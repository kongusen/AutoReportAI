# 开发环境搭建指南

本文档详细说明如何在本地搭建 AutoReportAI 的开发环境。

## 📋 环境要求

### 基础要求
- **Python**: 3.11+
- **Node.js**: 18+
- **Docker**: 20.0+
- **Docker Compose**: 2.0+

### 数据库要求
- **PostgreSQL**: 14+ (用于元数据存储)
- **Redis**: 6.0+ (用于缓存和任务队列)

### 可选外部数据源
- **Apache Doris**: 1.0+ (支持的数据源)
- **MySQL**: 8.0+
- **其他兼容的SQL数据库**

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd AutoReportAI
```

### 2. 后端环境搭建

#### 2.1 创建虚拟环境
```bash
cd backend
python -m venv venv

# Windows
venv\\Scripts\\activate

# Linux/Mac
source venv/bin/activate
```

#### 2.2 安装依赖
```bash
pip install -r requirements.txt
```

#### 2.3 环境配置
```bash
# 复制环境配置文件
cp env.example .env

# 编辑 .env 文件，配置数据库连接等信息
# DATABASE_URL=postgresql://user:password@localhost:5432/autoreport
# REDIS_URL=redis://localhost:6379
```

#### 2.4 数据库初始化
```bash
# 启动 PostgreSQL 和 Redis
docker-compose up -d db redis

# 运行数据库迁移
python scripts/init_db.py
```

#### 2.5 启动后端服务
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 前端环境搭建

#### 3.1 安装依赖
```bash
cd frontend
npm install
```

#### 3.2 启动前端服务
```bash
npm run dev
```

## 🐳 Docker 开发环境

### 使用 Docker Compose 启动完整环境
```bash
# 在项目根目录执行
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f backend
```

### Docker 服务说明
- **backend**: FastAPI 后端服务 (端口: 8000)
- **frontend**: Next.js 前端服务 (端口: 3000)
- **db**: PostgreSQL 数据库 (端口: 5432)
- **redis**: Redis 缓存服务 (端口: 6379)
- **celery**: Celery 任务队列
- **minio**: MinIO 对象存储 (可选)

## 🔧 开发工具配置

### VS Code 配置
推荐安装以下扩展：
- Python
- Pylance
- TypeScript and JavaScript Language Features
- ESLint
- Prettier
- Docker

### Python 代码规范
项目使用以下工具确保代码质量：
```bash
# 代码格式化
black .

# 导入排序
isort .

# 类型检查
mypy .

# 代码检查
flake8 .
```

### 前端代码规范
```bash
# 代码格式化
npm run format

# 类型检查
npm run type-check

# 代码检查
npm run lint
```

## 🧪 测试环境

### 后端测试
```bash
# 单元测试
pytest

# 集成测试
pytest tests/integration/

# 覆盖率报告
pytest --cov=app tests/
```

### 前端测试
```bash
# 单元测试
npm run test

# E2E 测试
npm run test:e2e
```

## 🗂️ 项目结构

### 后端结构 (backend/)
```
app/
├── api/               # API 路由和端点
├── core/              # 核心配置和工具
├── crud/              # 数据库操作
├── models/            # 数据库模型
├── schemas/           # Pydantic 模式
├── services/          # 业务逻辑层
│   ├── agents/        # DAG 智能代理
│   ├── application/   # 应用层
│   ├── domain/        # 领域层
│   ├── infrastructure/# 基础设施层
│   └── data/          # 数据访问层
└── main.py            # 应用入口
```

### 前端结构 (frontend/)
```
src/
├── app/               # Next.js 页面
├── components/        # React 组件
├── features/          # 业务功能模块
├── hooks/             # 自定义 Hooks
├── lib/               # 工具库
├── services/          # API 服务
├── stores/            # 状态管理
└── types/             # TypeScript 类型
```

## 🐛 常见问题

### 1. Python 依赖冲突
```bash
# 清理虚拟环境重新安装
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 数据库连接失败
检查以下配置：
- PostgreSQL 服务是否启动
- 数据库连接字符串是否正确
- 防火墙是否阻止连接

### 3. 前端服务无法启动
```bash
# 清理缓存重新安装
rm -rf node_modules package-lock.json
npm install
```

### 4. Docker 服务异常
```bash
# 重启所有服务
docker-compose down
docker-compose up -d

# 查看具体错误
docker-compose logs <service-name>
```

## 🔍 调试指南

### 后端调试
- 使用 VS Code 的 Python 调试器
- 设置断点进行单步调试
- 查看 FastAPI 自动生成的文档：http://localhost:8000/docs

### 前端调试
- 使用浏览器开发者工具
- React DevTools 扩展
- Next.js 内置的错误页面和热重载

### DAG 系统调试
- 查看 DAG 执行日志
- 使用智能代理的调试模式
- 监控上下文工程的状态

## 🚀 性能优化

### 后端优化
- 使用数据库连接池
- Redis 缓存热点数据
- 异步处理长时间任务

### 前端优化
- 组件懒加载
- 图片优化
- 合理使用缓存

## 📚 开发资源

### 官方文档
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Next.js 文档](https://nextjs.org/docs)
- [PostgreSQL 文档](https://www.postgresql.org/docs/)

### 项目文档
- [DAG架构设计](./AGENTS_DAG_ARCHITECTURE.md)
- [API使用指南](./api-guide.md)
- [部署指南](./deployment-guide.md)

---

*最后更新：2025-08-29*