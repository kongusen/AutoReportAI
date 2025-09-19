# AutoReportAI - 智能报告生成系统

## 📋 项目概述

AutoReportAI 是一个基于**领域驱动设计(DDD) v2.0**架构的智能报告生成系统，集成了先进的Agent技术和LLM服务，为用户提供自动化的数据分析和报告生成能力。

## 🏗️ 技术架构

### DDD v2.0 架构设计

```
AutoReportAI/
├── backend/                    # 后端服务 (Python/FastAPI)
│   ├── app/
│   │   ├── api/               # API控制器层
│   │   ├── services/          # DDD服务层
│   │   │   ├── application/   # 应用层 - 工作流编排
│   │   │   ├── domain/        # 领域层 - 业务逻辑
│   │   │   ├── infrastructure/ # 基础设施层 - 技术服务
│   │   │   └── data/          # 数据层 - 持久化
│   │   ├── core/             # 核心配置和依赖
│   │   └── models/           # 数据模型
│   ├── scripts/              # 数据库脚本
│   └── requirements.txt      # Python依赖
├── frontend/                  # 前端应用 (Next.js/TypeScript)
│   ├── src/
│   │   ├── components/       # React组件
│   │   ├── pages/           # 页面组件
│   │   ├── services/        # API服务层
│   │   └── types/           # TypeScript类型定义
│   └── package.json         # Node.js依赖
└── docs/                    # 项目文档
```

### 核心技术栈

**后端技术栈:**
- **框架**: FastAPI + SQLAlchemy 2.0 + Alembic
- **数据库**: PostgreSQL + Redis
- **架构**: 领域驱动设计(DDD) v2.0
- **AI服务**: LLamaIndex + 多LLM提供商支持
- **任务队列**: Celery + Redis
- **认证**: JWT + OAuth2

**前端技术栈:**
- **框架**: Next.js 14 + TypeScript
- **UI**: Tailwind CSS + Headless UI
- **状态管理**: Zustand
- **图表**: ECharts + React
- **HTTP客户端**: Axios

## 🚀 快速开始

### 环境要求

- **Python**: 3.11+
- **Node.js**: 18+
- **PostgreSQL**: 14+
- **Redis**: 6+

### 后端启动

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件配置数据库等信息

# 5. 初始化数据库
python scripts/init_db.py

# 6. 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 前端启动

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 配置环境变量
cp .env.example .env.local
# 编辑 .env.local 文件

# 4. 启动开发服务器
npm run dev
```

### 访问应用

- **前端应用**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

## 🛠️ 开发指南

### DDD架构原则

1. **应用层**: 工作流编排，事务协调
2. **领域层**: 纯业务逻辑，领域服务
3. **基础设施层**: 技术实现，外部集成
4. **数据层**: 数据访问，持久化

### Agent系统集成

Agent系统作为基础设施层技术服务：

```python
# 业务流程示例
from app.services.application.tasks import TaskApplicationService

# 1. 应用层编排
task_service = TaskApplicationService(db, user_id)

# 2. 领域层业务逻辑
analysis = await task_service.analyze_task_with_domain_services(task_id)

# 3. 基础设施层Agent执行
result = await task_service.execute_task_through_agents(task_id, context)
```

### API开发规范

**统一响应格式**:
```typescript
interface APIResponse<T> {
  success: boolean;
  data?: T;
  message: string;
  errors: string[];
  warnings: string[];
  metadata: Record<string, any>;
  timestamp: string;
}
```

**DDD应用结果**:
```typescript
interface ApplicationResult<T> {
  success: boolean;
  result: OperationResult;
  data?: T;
  message: string;
  errors: string[];
  warnings: string[];
  metadata: Record<string, any>;
  execution_time_ms?: number;
}
```

## 📚 核心功能

### 🎯 模板管理
- 智能模板解析和占位符识别
- 自动SQL生成和验证
- 模板版本管理和共享

### 📊 数据源集成
- 多数据源支持 (PostgreSQL, MySQL, Doris, API, CSV)
- 智能Schema发现和关系分析
- 实时数据连接测试

### 🤖 智能报告生成
- Agent驱动的数据分析
- 自动图表生成和配置
- 多格式输出 (PDF, Word, HTML)

### ⚡ 任务调度
- 灵活的Cron表达式支持
- 分布式任务执行
- 实时任务监控和日志

## 🔧 配置说明

### 环境变量配置

```bash
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/autoreport
REDIS_URL=redis://localhost:6379/0

# AI服务配置
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# 应用配置
SECRET_KEY=your_secret_key
ENVIRONMENT=development
DEBUG=true

# 存储配置
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minio_access_key
MINIO_SECRET_KEY=minio_secret_key
```

### LLM服务配置

系统支持多种LLM提供商：

- **OpenAI**: GPT-3.5/GPT-4系列
- **Anthropic**: Claude系列
- **Google**: Gemini系列
- **本地模型**: Ollama集成

## 🧪 测试

### 后端测试

```bash
# 单元测试
pytest tests/unit/

# 集成测试
pytest tests/integration/

# DDD架构测试
pytest tests/test_ddd_architecture.py

# 覆盖率测试
pytest --cov=app tests/
```

### 前端测试

```bash
# 类型检查
npm run type-check

# ESLint检查
npm run lint

# 构建测试
npm run build
```

## 📖 文档

- **架构文档**: [SERVICE_ARCHITECTURE_WIKI.md](docs/SERVICE_ARCHITECTURE_WIKI.md)
- **API文档**: http://localhost:8000/docs (启动后端后访问)
- **数据流程**: [data_flow_diagram.md](docs/data_flow_diagram.md)
- **开发指南**: [placeholder_to_data_generation_flow.md](docs/placeholder_to_data_generation_flow.md)

## 🤝 贡献指南

1. **Fork** 项目仓库
2. 创建功能分支: `git checkout -b feature/amazing-feature`
3. 遵循DDD架构原则和代码规范
4. 添加相应的测试用例
5. 提交变更: `git commit -m 'Add amazing feature'`
6. 推送分支: `git push origin feature/amazing-feature`
7. 提交Pull Request

### 开发规范

- **代码风格**: 遵循Python PEP8和TypeScript Standard
- **架构原则**: 严格按照DDD v2.0分层架构
- **测试要求**: 新功能必须包含单元测试和集成测试
- **文档要求**: 更新相关的API文档和架构文档

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件获取详细信息。

## 🆘 支持

如果遇到问题或需要帮助：

1. 查看 [文档](docs/) 和 [FAQ](docs/FAQ.md)
2. 搜索现有的 [Issues](https://github.com/your-repo/issues)
3. 创建新的Issue并提供详细信息
4. 联系开发团队

## 🔮 路线图

- [ ] **v2.1**: 增强Agent系统，支持更多工具集成
- [ ] **v2.2**: 实时协作功能，多用户实时编辑
- [ ] **v2.3**: 移动端适配，PWA支持
- [ ] **v3.0**: 微服务架构，云原生部署

---

**AutoReportAI** - 让数据分析和报告生成变得简单智能！ 🚀