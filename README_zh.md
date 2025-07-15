<div align="center">
  <img src="https://raw.githubusercontent.com/user-attachments/assets/15ba393a-864a-4f1c-8af2-8b43834a3b04" width="150" alt="AutoReportAI Logo">
  <h1>AutoReportAI</h1>
  <p>
    <b>一个由AI驱动、企业级的智能自动化报告生成系统。</b>
  </p>
  <p>
    AutoReportAI 通过集成先进AI技术和全面数据分析的完全自动化、可定制工作流，将原始数据转化为精美的Word文档（.docx）。
  </p>

  <p>
    <a href="https://github.com/kongusen/AutoReportAI/stargazers"><img src="https://img.shields.io/github/stars/kongusen/AutoReportAI?style=flat-square" alt="GitHub stars"></a>
    <a href="https://github.com/kongusen/AutoReportAI/forks"><img src="https://img.shields.io/github/forks/kongusen/AutoReportAI?style=flat-square" alt="GitHub forks"></a>
    <a href="https://github.com/kongusen/AutoReportAI/issues"><img src="https://img.shields.io/github/issues/kongusen/AutoReportAI?style=flat-square" alt="GitHub issues"></a>
    <a href="./LICENSE"><img src="https://img.shields.io/github/license/kongusen/AutoReportAI?style=flat-square" alt="License"></a>
    <img src="https://img.shields.io/badge/Tests-100%25%20Passing-brightgreen?style=flat-square" alt="Tests">
  </p>

  <p>
    <a href="./README.md">English</a> | <b>简体中文</b>
  </p>
</div>

---

## ✨ 核心功能

AutoReportAI 是一个融合AI智能和企业级可靠性以及现代用户体验的综合自动化平台。

- **🤖 AI驱动分析**: 集成多个AI供应商（OpenAI、本地模型）进行智能数据分析、内容生成和报告合成，支持动态占位符填充。
- **🕒 高级任务调度**: 基于`APScheduler`的强大Cron调度系统，支持自动任务执行、全面错误处理和执行历史跟踪。
- **📊 全面ETL流水线**: 功能完备的ETL引擎，从多种数据源（数据库、API、文件）获取数据，通过可配置转换处理，并加载到分析数据中心。
- **🎨 动态模板系统**: 智能模板管理，支持占位符检测、变量替换和AI驱动的内容生成。支持复杂文档结构和格式化。
- **📈 高级数据分析**: 内置统计分析、数据可视化、增长计算和趋势分析，具备图表生成能力。
- **🔌 多供应商AI集成**: 可插拔AI架构，支持OpenAI、本地模型和自定义供应商，具备智能回退机制。
- **👥 用户管理与配置**: 完整的用户认证、基于角色的访问控制、用户配置文件和个性化设置管理。
- **🗂️ 完整审计追踪**: 全面记录所有操作、任务执行、错误和系统事件，提供详细的历史跟踪和报告。
- **🌐 现代化Web界面**: 基于Next.js、TypeScript和Tailwind CSS构建的美观响应式UI，支持深色/浅色主题、仪表板分析和直观导航。
- **🔧 企业级就绪**: 生产级部署，包含Docker容器化、CI/CD流水线、全面测试套件和数据库迁移。

## 🏛️ 系统架构

系统采用微服务架构设计，职责清晰分离，专为可扩展性和可维护性而设计。

```mermaid
graph TD
    subgraph "用户界面"
        A[Web浏览器]
        B[移动/平板设备]
    end

    subgraph "前端层 (Next.js + TypeScript)"
        C[仪表板]
        D[任务管理]
        E[模板编辑器]
        F[数据源配置]
        G[分析与报告]
        H[用户管理]
    end

    subgraph "API层 (FastAPI)"
        I{API网关}
        I --> J[认证与授权]
        I --> K[任务管理API]
        I --> L[模板管理API]
        I --> M[数据源API]
        I --> N[ETL作业API]
        I --> O[分析API]
        I --> P[用户配置API]
    end
    
    subgraph "调度与编排"
        Q[APScheduler主进程]
        R[任务队列管理器]
        S[错误恢复系统]
    end

    subgraph "核心服务"
        T[ETL服务引擎]
        U[AI服务层]
        V[数据分析服务]
        W[可视化服务]
        X[报告合成服务]
        Y[统计服务]
    end

    subgraph "AI供应商"
        Z[OpenAI集成]
        AA[本地AI模型]
        BB[自定义AI供应商]
    end

    subgraph "数据层 (PostgreSQL)"
        CC[(主数据库)]
        CC --> DD[用户与认证表]
        CC --> EE[任务与调度表]
        CC --> FF[模板与映射表]
        CC --> GG[分析数据中心]
        CC --> HH[审计与历史表]
    end

    subgraph "外部数据源"
        II[业务数据库]
        JJ[REST APIs]
        KK[CSV/Excel文件]
        LL[云存储]
    end

    A --> C
    B --> C
    C --> I
    
    Q --> R
    Q --> K
    Q --> T
    
    T --> II
    T --> JJ
    T --> KK
    T --> LL
    T --> GG
    
    U --> Z
    U --> AA
    U --> BB
    
    V --> GG
    W --> GG
    Y --> GG
    
    X --> U
    X --> V
    X --> W
```

## 🛠️ 技术栈

| 类别               | 技术栈                                                                                                                                  |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| **后端**           | <img src="https://img.shields.io/badge/Python-3.9+-blue.svg?logo=python&style=flat-square" alt="Python"> <img src="https://img.shields.io/badge/FastAPI-0.104+-blue.svg?logo=fastapi&style=flat-square" alt="FastAPI"> <img src="https://img.shields.io/badge/SQLAlchemy-2.0+-orange.svg?style=flat-square" alt="SQLAlchemy"> <img src="https://img.shields.io/badge/Alembic-1.12+-green.svg?style=flat-square" alt="Alembic"> |
| **调度器**         | <img src="https://img.shields.io/badge/APScheduler-3.10+-green.svg?style=flat-square" alt="APScheduler"> <img src="https://img.shields.io/badge/Cron-表达式-yellow.svg?style=flat-square" alt="Cron"> |
| **前端**           | <img src="https://img.shields.io/badge/Next.js-14+-black.svg?logo=next.js&style=flat-square" alt="Next.js"> <img src="https://img.shields.io/badge/React-18+-blue.svg?logo=react&style=flat-square" alt="React"> <img src="https://img.shields.io/badge/TypeScript-5+-blue.svg?logo=typescript&style=flat-square" alt="TypeScript"> <img src="https://img.shields.io/badge/Tailwind_CSS-3+-cyan.svg?logo=tailwind-css&style=flat-square" alt="Tailwind CSS"> |
| **数据库**         | <img src="https://img.shields.io/badge/PostgreSQL-15+-blue.svg?logo=postgresql&style=flat-square" alt="PostgreSQL"> <img src="https://img.shields.io/badge/数据库迁移-Alembic-orange.svg?style=flat-square" alt="Migrations"> |
| **AI集成**         | <img src="https://img.shields.io/badge/OpenAI-1.3+-blue.svg?logo=openai&style=flat-square" alt="OpenAI"> <img src="https://img.shields.io/badge/本地模型-支持-green.svg?style=flat-square" alt="Local Models"> <img src="https://img.shields.io/badge/自定义供应商-可插拔-purple.svg?style=flat-square" alt="Custom Providers"> |
| **数据处理**       | <img src="https://img.shields.io/badge/Pandas-2.0+-green.svg?logo=pandas&style=flat-square" alt="Pandas"> <img src="https://img.shields.io/badge/NumPy-1.24+-blue.svg?logo=numpy&style=flat-square" alt="NumPy"> <img src="https://img.shields.io/badge/Matplotlib-3.7+-orange.svg?style=flat-square" alt="Matplotlib"> |
| **DevOps与测试**   | <img src="https://img.shields.io/badge/Docker-24+-blue.svg?logo=docker&style=flat-square" alt="Docker"> <img src="https://img.shields.io/badge/Docker_Compose-2.0+-blue.svg?style=flat-square" alt="Docker Compose"> <img src="https://img.shields.io/badge/Pytest-7.4+-green.svg?style=flat-square" alt="Pytest"> <img src="https://img.shields.io/badge/Jest-29+-red.svg?logo=jest&style=flat-square" alt="Jest"> |
| **文档生成**       | <img src="https://img.shields.io/badge/python--docx-0.8+-blue.svg?style=flat-square" alt="python-docx"> <img src="https://img.shields.io/badge/模板引擎-自定义-purple.svg?style=flat-square" alt="Template Engine"> |

## 🚀 快速上手

本项目采用针对本地开发优化的混合开发模式：数据库在Docker中运行，应用服务在本地运行，便于调试和快速迭代。

### 1. 先决条件

- [Docker](https://www.docker.com/get-started/) 和 Docker Compose (v2.0+)
- [Python 3.9+](https://www.python.org/downloads/) 和 pip
- [Node.js 18+](https://nodejs.org/) 和 npm
- [Git](https://git-scm.com/) 版本控制工具

### 2. 环境配置

1.  **克隆仓库**:
    ```bash
    git clone https://github.com/kongusen/AutoReportAI.git
    cd AutoReportAI
    ```

2.  **启动数据库基础设施**:
    ```bash
    docker-compose up -d
    ```
    *在后台启动PostgreSQL。数据库将在 `localhost:5432` 可用。*

3.  **配置环境变量**:
    在 `backend/` 目录创建 `.env` 文件：
    ```dotenv
    # backend/.env
    DATABASE_URL=postgresql://autoreport:autoreport@localhost:5432/autoreport
    SECRET_KEY=your-secret-key-here
    AI_PROVIDER=openai
    OPENAI_API_KEY=your-openai-api-key  # 可选，用于AI功能
    ```

### 3. 后端设置与API服务器

1.  **创建Python虚拟环境**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Windows系统: venv\Scripts\activate
    ```

2.  **安装依赖**:
    ```bash
    pip install -r backend/requirements.txt
    ```

3.  **初始化数据库**:
    ```bash
    cd backend
    alembic upgrade head
    python initial_data.py  # 创建默认管理员用户
    cd ..
    ```

4.  **启动API服务器**:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir ./backend
    ```
    *后端API在 `http://localhost:8000` 可用，启用自动重载。*

### 4. 调度器服务

在**新终端**中激活虚拟环境：

```bash
python scheduler/main.py
```
*启动任务调度器，监控和执行预定报告。保持运行以实现自动化。*

### 5. 前端开发服务器

1.  **安装前端依赖**:
    ```bash
    npm install --prefix frontend
    ```

2.  **启动开发服务器**:
    ```bash
    npm run dev --prefix frontend
    ```
    *前端在 `http://localhost:3000` 可用，支持热重载。*

### 6. 访问应用程序

- **🌐 Web应用程序**: `http://localhost:3000`
- **📚 API文档**: `http://localhost:8000/docs` (Swagger UI)
- **🔍 API替代文档**: `http://localhost:8000/redoc` (ReDoc)

**默认管理员凭据**:
- **邮箱**: `admin@example.com`
- **密码**: `password`

### 7. 运行测试

**后端测试**:
```bash
cd backend
pytest -v  # 运行所有后端测试
pytest test_ci_cd.py -v  # 运行CI/CD特定测试
```

**前端测试**:
```bash
npm test --prefix frontend  # 运行前端单元测试
npm run test:coverage --prefix frontend  # 生成覆盖率报告
```

**集成测试**:
```bash
cd backend
python test_complex_scenarios.py  # 测试复杂工作流
```

## 📊 项目状态与CI/CD

✅ **后端测试**: 6/6 通过 (100% 成功率)
- 数据库连接和迁移
- API端点功能  
- 数据模型关系和约束
- 错误处理和恢复
- 性能基准测试

✅ **前端测试**: 3/3 通过 (100% 覆盖率)
- 组件渲染和交互
- 工具函数和辅助方法
- 与后端API的集成

✅ **系统集成**: 完整工作流测试完成
- 端到端报告生成
- 多用户场景
- 并发任务执行
- 错误恢复机制

## 🎯 功能完整性

### ✅ 已完成功能

- **🏗️ 核心基础设施**
  - ✅ 数据库模型和关系
  - ✅ API端点和路由
  - ✅ 认证和安全
  - ✅ 数据库迁移和数据初始化

- **🤖 AI与分析**
  - ✅ 多供应商AI集成（OpenAI、本地模型）
  - ✅ 数据分析和统计计算
  - ✅ 图表生成和可视化
  - ✅ 智能内容生成

- **📋 任务管理**
  - ✅ 高级任务创建和调度
  - ✅ 基于Cron的自动化
  - ✅ 错误处理和重试机制
  - ✅ 执行历史和日志记录

- **📄 模板系统**
  - ✅ 模板上传和管理
  - ✅ 占位符检测和映射
  - ✅ 动态内容替换
  - ✅ 文档合成引擎

- **👥 用户管理**
  - ✅ 用户认证和配置文件
  - ✅ 基于角色的访问控制
  - ✅ 个人设置和偏好
  - ✅ 账户管理界面

- **🌐 现代UI/UX**
  - ✅ 响应式仪表板与分析
  - ✅ 深色/浅色主题支持
  - ✅ 直观导航和表单
  - ✅ 实时状态更新

- **🔧 DevOps与质量**
  - ✅ Docker容器化
  - ✅ 全面测试套件
  - ✅ CI/CD流水线实现
  - ✅ 代码质量和代码检查

### 🚧 路线图与未来增强

- **📈 高级分析**
  - [ ] 可交互的仪表板，支持钻取功能
  - [ ] 自定义KPI定义和跟踪
  - [ ] 预测分析和预测
  - [ ] 高级数据可视化选项（Plotly、D3.js）

- **🔗 增强集成**
  - [ ] 云存储供应商（AWS S3、Google Cloud、Azure）
  - [ ] 更多数据库类型（MySQL、SQLite、MongoDB）
  - [ ] 商业智能工具集成
  - [ ] Webhook和API通知系统

- **🚀 性能与可扩展性**
  - [ ] 负载均衡器水平扩展
  - [ ] 缓存层（Redis）提升性能
  - [ ] Celery后台作业处理
  - [ ] 数据库查询优化和索引

- **🛡️ 企业功能**
  - [ ] 高级审计日志和合规性
  - [ ] 单点登录（SSO）集成
  - [ ] 高级安全策略和加密
  - [ ] 多租户架构支持

## 🧪 测试策略

我们的全面测试方法确保可靠性和可维护性：

- **单元测试**: 高覆盖率的单个组件测试
- **集成测试**: 端到端工作流验证
- **性能测试**: 负载测试和优化基准
- **安全测试**: 认证、授权和数据保护
- **CI/CD流水线**: 每次提交和部署的自动化测试

## 🤝 贡献

我们欢迎贡献！以下是开始的方法：

1. **Fork仓库**并创建功能分支
2. **使用快速入门指南设置开发环境**
3. **为新功能编写测试**
4. **确保所有测试通过**后再提交
5. **创建详细描述的pull request**

### 开发指南

- 后端代码遵循Python PEP 8风格指南
- 前端使用TypeScript和React最佳实践
- 为新功能编写全面测试
- 更新API变更的文档
- 确保CI/CD测试通过后再合并

## 📄 许可证

本项目基于MIT许可证授权。详情请见 [LICENSE](./LICENSE) 文件。

---

<div align="center">
  <p><b>用❤️构建，致力于智能自动化和数据驱动洞察</b></p>
  <p>AutoReportAI - 自动将数据转化为知识</p>
</div> 