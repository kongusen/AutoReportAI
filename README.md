<div align="center">
  <img src="https://raw.githubusercontent.com/user-attachments/assets/15ba393a-864a-4f1c-8af2-8b43834a3b04" width="150" alt="AutoReportAI Logo">
  <h1>AutoReportAI</h1>
  <p>
    <b>智能化、AI驱动的企业级自动报告生成系统</b>
  </p>
  <p>
    AutoReportAI 通过完全自动化、可定制的工作流程，结合先进的 AI 集成和全面的数据分析功能，将原始数据转换为精美的 Word 文档（`.docx`）报告。
  </p>

  <p>
    <a href="https://github.com/kongusen/AutoReportAI/stargazers"><img src="https://img.shields.io/github/stars/kongusen/AutoReportAI?style=flat-square" alt="GitHub stars"></a>
    <a href="https://github.com/kongusen/AutoReportAI/forks"><img src="https://img.shields.io/github/forks/kongusen/AutoReportAI?style=flat-square" alt="GitHub forks"></a>
    <a href="https://github.com/kongusen/AutoReportAI/issues"><img src="https://img.shields.io/github/issues/kongusen/AutoReportAI?style=flat-square" alt="GitHub issues"></a>
    <a href="./LICENSE"><img src="https://img.shields.io/github/license/kongusen/AutoReportAI?style=flat-square" alt="License"></a>
  </p>

  <p>
    <a href="https://github.com/kongusen/AutoReportAI/actions/workflows/ci-cd.yml"><img src="https://img.shields.io/github/actions/workflow/status/kongusen/AutoReportAI/ci-cd.yml?branch=main&label=CI%2FCD&style=flat-square" alt="CI/CD Pipeline"></a>
    <a href="https://github.com/kongusen/AutoReportAI/actions/workflows/quality.yml"><img src="https://img.shields.io/github/actions/workflow/status/kongusen/AutoReportAI/quality.yml?branch=main&label=Quality%20Gate&style=flat-square" alt="Quality Gate"></a>
    <a href="https://github.com/kongusen/AutoReportAI/actions/workflows/unit-tests.yml"><img src="https://img.shields.io/github/actions/workflow/status/kongusen/AutoReportAI/unit-tests.yml?branch=main&label=Unit%20Tests&style=flat-square" alt="Unit Tests"></a>
    <a href="https://github.com/kongusen/AutoReportAI/actions/workflows/integration-tests.yml"><img src="https://img.shields.io/github/actions/workflow/status/kongusen/AutoReportAI/integration-tests.yml?branch=main&label=Integration%20Tests&style=flat-square" alt="Integration Tests"></a>
    <a href="https://codecov.io/gh/kongusen/AutoReportAI"><img src="https://img.shields.io/codecov/c/github/kongusen/AutoReportAI?style=flat-square" alt="Code Coverage"></a>
  </p>

  <p>
    <a href="./README_EN.md">English</a> | <b>简体中文</b>
  </p>
</div>

---

## ✨ 核心特性

AutoReportAI 是一个综合性自动化平台，将 AI 智能与企业级可靠性和现代化用户体验相结合。

- **🤖 AI 智能分析**: 集成多个 AI 提供商（OpenAI、本地模型），实现智能数据分析、内容生成和动态占位符填充的报告组合。
- **🕒 高级任务调度**: 基于 `APScheduler` 的强大 cron 调度系统，支持自动化任务执行、全面的错误处理和执行历史跟踪。
- **📊 全面 ETL 流水线**: 功能完整的 ETL 引擎，从多个数据源（数据库、API、文件）获取数据，通过可配置的转换处理并加载到分析数据仓库。
- **🎨 动态模板系统**: 智能模板管理，支持占位符检测、变量替换和 AI 驱动的内容生成，支持复杂的文档结构和格式化。
- **📈 高级数据分析**: 内置统计分析、数据可视化、增长计算和趋势分析，具备图表生成能力。
- **🔌 多提供商 AI 集成**: 可插拔的 AI 架构，支持 OpenAI、本地模型和自定义提供商，具备智能故障转移机制。
- **👥 用户管理与档案**: 完整的用户认证、基于角色的访问控制、用户档案和个性化设置管理。
- **🗂️ 完整审计跟踪**: 全面记录所有操作、任务执行、错误和系统事件，提供详细的历史跟踪和报告。
- **🌐 现代化 Web 界面**: 使用 Next.js、TypeScript 和 Tailwind CSS 构建的精美响应式 UI，支持深浅主题、仪表板分析和直观导航。
- **🔧 企业就绪**: 生产级部署，包含 Docker 容器化、CI/CD 流水线、全面测试套件和数据库迁移。

## 🏛️ System Architecture

The system features a microservices architecture with clear separation of concerns, designed for scalability and maintainability.

```mermaid
graph TD
    subgraph "User Interface"
        A[Web Browser]
        B[Mobile/Tablet]
    end

    subgraph "Frontend Layer (Next.js + TypeScript)"
        C[Dashboard]
        D[Task Management]
        E[Template Editor]
        F[Data Source Config]
        G[Analytics & Reports]
        H[User Management]
    end

    subgraph "API Layer (FastAPI)"
        I{API Gateway}
        I --> J[Authentication & Authorization]
        I --> K[Task Management API]
        I --> L[Template Management API]
        I --> M[Data Source API]
        I --> N[ETL Job API]
        I --> O[Analytics API]
        I --> P[User Profile API]
    end
    
    subgraph "Scheduler & Orchestration"
        Q[APScheduler Master Process]
        R[Task Queue Manager]
        S[Error Recovery System]
    end

    subgraph "Core Services"
        T[ETL Service Engine]
        U[AI Service Layer]
        V[Data Analysis Service]
        W[Visualization Service]
        X[Report Composition Service]
        Y[Statistics Service]
    end

    subgraph "AI Providers"
        Z[OpenAI Integration]
        AA[Local AI Models]
        BB[Custom AI Providers]
    end

    subgraph "Data Layer (PostgreSQL)"
        CC[(Primary Database)]
        CC --> DD[User & Auth Tables]
        CC --> EE[Task & Schedule Tables]
        CC --> FF[Template & Mapping Tables]
        CC --> GG[Analytics Data Mart]
        CC --> HH[Audit & History Tables]
    end

    subgraph "External Data Sources"
        II[Business Databases]
        JJ[REST APIs]
        KK[CSV/Excel Files]
        LL[Cloud Storage]
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

## 🛠️ Tech Stack

| Category              | Technology Stack                                                                                                                        |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Backend**           | <img src="https://img.shields.io/badge/Python-3.9+-blue.svg?logo=python&style=flat-square" alt="Python"> <img src="https://img.shields.io/badge/FastAPI-0.104+-blue.svg?logo=fastapi&style=flat-square" alt="FastAPI"> <img src="https://img.shields.io/badge/SQLAlchemy-2.0+-orange.svg?style=flat-square" alt="SQLAlchemy"> <img src="https://img.shields.io/badge/Alembic-1.12+-green.svg?style=flat-square" alt="Alembic"> |
| **Scheduler**         | <img src="https://img.shields.io/badge/APScheduler-3.10+-green.svg?style=flat-square" alt="APScheduler"> <img src="https://img.shields.io/badge/Cron-Expressions-yellow.svg?style=flat-square" alt="Cron"> |
| **Frontend**          | <img src="https://img.shields.io/badge/Next.js-14+-black.svg?logo=next.js&style=flat-square" alt="Next.js"> <img src="https://img.shields.io/badge/React-18+-blue.svg?logo=react&style=flat-square" alt="React"> <img src="https://img.shields.io/badge/TypeScript-5+-blue.svg?logo=typescript&style=flat-square" alt="TypeScript"> <img src="https://img.shields.io/badge/Tailwind_CSS-3+-cyan.svg?logo=tailwind-css&style=flat-square" alt="Tailwind CSS"> |
| **Database**          | <img src="https://img.shields.io/badge/PostgreSQL-15+-blue.svg?logo=postgresql&style=flat-square" alt="PostgreSQL"> <img src="https://img.shields.io/badge/Database_Migrations-Alembic-orange.svg?style=flat-square" alt="Migrations"> |
| **AI Integration**    | <img src="https://img.shields.io/badge/OpenAI-1.3+-blue.svg?logo=openai&style=flat-square" alt="OpenAI"> <img src="https://img.shields.io/badge/Local_Models-Supported-green.svg?style=flat-square" alt="Local Models"> <img src="https://img.shields.io/badge/Custom_Providers-Pluggable-purple.svg?style=flat-square" alt="Custom Providers"> |
| **Data Processing**   | <img src="https://img.shields.io/badge/Pandas-2.0+-green.svg?logo=pandas&style=flat-square" alt="Pandas"> <img src="https://img.shields.io/badge/NumPy-1.24+-blue.svg?logo=numpy&style=flat-square" alt="NumPy"> <img src="https://img.shields.io/badge/Matplotlib-3.7+-orange.svg?style=flat-square" alt="Matplotlib"> |
| **DevOps & Testing**  | <img src="https://img.shields.io/badge/Docker-24+-blue.svg?logo=docker&style=flat-square" alt="Docker"> <img src="https://img.shields.io/badge/Docker_Compose-2.0+-blue.svg?style=flat-square" alt="Docker Compose"> <img src="https://img.shields.io/badge/Pytest-7.4+-green.svg?style=flat-square" alt="Pytest"> <img src="https://img.shields.io/badge/Jest-29+-red.svg?logo=jest&style=flat-square" alt="Jest"> |
| **Document Generation** | <img src="https://img.shields.io/badge/python--docx-0.8+-blue.svg?style=flat-square" alt="python-docx"> <img src="https://img.shields.io/badge/Template_Engine-Custom-purple.svg?style=flat-square" alt="Template Engine"> |

## 🚀 Quick Start

This project uses a hybrid development model optimized for local development: database runs in Docker while application services run locally for easier debugging and faster iteration.

### 1. Prerequisites

- [Docker](https://www.docker.com/get-started/) & Docker Compose (v2.0+)
- [Python 3.11+](https://www.python.org/downloads/) with pip
- [Node.js 18+](https://nodejs.org/) & npm
- [Git](https://git-scm.com/) for version control

### 2. Environment Setup

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/kongusen/AutoReportAI.git
    cd AutoReportAI
    ```

2.  **Start Database Infrastructure**:
    ```bash
    docker-compose up -d
    ```
    *This starts PostgreSQL in the background. Database will be available at `localhost:5432`.*

3.  **Configure Environment Variables**:
    Create `.env` file in the `backend/` directory:
    ```dotenv
    # backend/.env
    DATABASE_URL=postgresql://autoreport:autoreport@localhost:5432/autoreport
    SECRET_KEY=your-secret-key-here
    AI_PROVIDER=openai
    OPENAI_API_KEY=your-openai-api-key  # Optional, for AI features
    ```

### 3. Backend Setup & API Server

1.  **Create Python Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  **Install Dependencies**:
    ```bash
    cd backend
    pip install -r requirements/development.txt  # For development
    # OR pip install -r requirements/production.txt  # For production
    ```

3.  **Initialize Database**:
    ```bash
    # Using Makefile (recommended)
    make dev-setup  # Sets up everything: dependencies, database, initial data, tests
    
    # OR manually:
    alembic upgrade head
    python scripts/init_db.py  # Creates default admin user
    ```

4.  **Start API Server**:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```
    *Backend API available at `http://localhost:8000` with auto-reload enabled.*

### 4. Scheduler Service

In a **new terminal** with the virtual environment activated:

```bash
python scheduler/main.py
```
*Starts the task scheduler that monitors and executes scheduled reports. Keep running for automation.*

### 5. Frontend Development Server

1.  **Install Frontend Dependencies**:
    ```bash
    npm install --prefix frontend
    ```

2.  **Start Development Server**:
    ```bash
    npm run dev --prefix frontend
    ```
    *Frontend available at `http://localhost:3000` with hot-reload.*

### 6. Access the Application

- **🌐 Web Application**: `http://localhost:3000`
- **📚 API Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **🔍 API Alternative Docs**: `http://localhost:8000/redoc` (ReDoc)

**Default Admin Credentials**:
- **Email**: `admin@example.com`
- **Password**: `password`

### 7. Development Commands

The backend includes a comprehensive Makefile for common development tasks:

```bash
cd backend

# Development setup (installs deps, migrates DB, runs tests)
make dev-setup

# Testing commands
make test           # Run all tests
make test-unit      # Run unit tests only (fast)
make test-integration  # Run integration tests
make test-e2e       # Run end-to-end tests
make test-coverage  # Run tests with coverage report

# Code quality
make lint           # Run code linting
make format         # Format code with black
make prod-check     # Production readiness check

# Database operations
make migrate        # Run database migrations
make reset-db       # Reset database (caution!)
make init-db        # Initialize with sample data

# Utilities
make clean          # Clean temporary files
make help           # Show all available commands
```

### 8. Running Tests

Our testing strategy includes multiple test categories for comprehensive coverage:

**Quick Unit Tests** (< 30 seconds):
```bash
cd backend
make test-unit
# OR: pytest tests/unit/ -v -m "not slow"
```

**Integration Tests** (< 5 minutes):
```bash
cd backend
make test-integration
# OR: pytest tests/integration/ -v
```

**End-to-End Tests** (< 15 minutes):
```bash
cd backend
make test-e2e
# OR: pytest tests/e2e/ -v
```

**All Tests with Coverage**:
```bash
cd backend
make test-coverage
# Generates HTML coverage report in htmlcov/
```

**Frontend Tests**:
```bash
npm test --prefix frontend              # Run unit tests
npm run test:coverage --prefix frontend # With coverage report
```

**Performance & Benchmarks**:
```bash
cd backend
make perf-test  # Run performance benchmarks
```

## 📊 Project Status & CI/CD

✅ **Backend Tests**: 6/6 passing (100% success rate)
- Database connectivity and migrations
- API endpoint functionality  
- Data model relationships and constraints
- Error handling and recovery
- Performance benchmarks

✅ **Frontend Tests**: 3/3 passing (100% coverage)
- Component rendering and interactions
- Utility functions and helpers
- Integration with backend APIs

✅ **System Integration**: Full workflow testing completed
- End-to-end report generation
- Multi-user scenarios
- Concurrent task execution
- Error recovery mechanisms

## 🎯 Feature Completeness

### ✅ Completed Features

- **🏗️ Core Infrastructure**
  - ✅ Database models and relationships
  - ✅ API endpoints and routing
  - ✅ Authentication and security
  - ✅ Database migrations and seeding

- **🤖 AI & Analytics**
  - ✅ Multi-provider AI integration (OpenAI, local models)
  - ✅ Data analysis and statistical calculations
  - ✅ Chart generation and visualization
  - ✅ Intelligent content generation

- **📋 Task Management**
  - ✅ Advanced task creation and scheduling
  - ✅ Cron-based automation
  - ✅ Error handling and retry mechanisms
  - ✅ Execution history and logging

- **📄 Template System**
  - ✅ Template upload and management
  - ✅ Placeholder detection and mapping
  - ✅ Dynamic content substitution
  - ✅ Document composition engine

- **👥 User Management**
  - ✅ User authentication and profiles
  - ✅ Role-based access control
  - ✅ Personal settings and preferences
  - ✅ Account management interface

- **🌐 Modern UI/UX**
  - ✅ Responsive dashboard with analytics
  - ✅ Dark/light theme support
  - ✅ Intuitive navigation and forms
  - ✅ Real-time status updates

- **🔧 DevOps & Quality**
  - ✅ Docker containerization
  - ✅ Comprehensive testing suite
  - ✅ CI/CD pipeline implementation
  - ✅ Code quality and linting

### 🚧 Roadmap & Future Enhancements

- **📈 Advanced Analytics**
  - [ ] Interactive dashboards with drill-down capabilities
  - [ ] Custom KPI definitions and tracking
  - [ ] Predictive analytics and forecasting
  - [ ] Advanced data visualization options (Plotly, D3.js)

- **🔗 Enhanced Integrations**
  - [ ] Cloud storage providers (AWS S3, Google Cloud, Azure)
  - [ ] More database types (MySQL, SQLite, MongoDB)
  - [ ] Business intelligence tools integration
  - [ ] Webhook and API notification systems

- **🚀 Performance & Scalability**
  - [ ] Horizontal scaling with load balancers
  - [ ] Caching layer (Redis) for improved performance
  - [ ] Background job processing with Celery
  - [ ] Database query optimization and indexing

- **🛡️ Enterprise Features**
  - [ ] Advanced audit logging and compliance
  - [ ] Single Sign-On (SSO) integration
  - [ ] Advanced security policies and encryption
  - [ ] Multi-tenant architecture support

## 📁 Project Structure

The project follows a clean, organized structure optimized for maintainability and scalability:

```
AutoReportAI/
├── backend/                    # Backend API and services
│   ├── app/                   # Main application code
│   │   ├── api/              # API routes and endpoints
│   │   ├── core/             # Core configuration and utilities
│   │   ├── crud/             # Database CRUD operations
│   │   ├── db/               # Database configuration
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic services
│   │   └── websocket/        # WebSocket handlers
│   ├── tests/                # Comprehensive test suite
│   │   ├── unit/            # Fast unit tests
│   │   ├── integration/     # Integration tests
│   │   ├── e2e/            # End-to-end tests
│   │   └── test_data/      # Test fixtures and data
│   ├── migrations/          # Database migrations
│   ├── scripts/            # Utility scripts
│   ├── requirements/       # Dependency management
│   │   ├── base.txt       # Core dependencies
│   │   ├── development.txt # Development dependencies
│   │   ├── testing.txt    # Testing dependencies
│   │   └── production.txt # Production dependencies
│   ├── pyproject.toml     # Project configuration
│   ├── pytest.ini        # Test configuration
│   └── Makefile          # Development commands
├── frontend/              # Next.js frontend application
│   ├── src/
│   │   ├── app/          # App router pages
│   │   ├── components/   # React components
│   │   ├── lib/         # Utilities and API clients
│   │   └── types/       # TypeScript type definitions
│   └── package.json     # Frontend dependencies
├── scheduler/            # Task scheduling service
├── .github/             # CI/CD workflows
│   └── workflows/
│       ├── ci-cd.yml           # Main CI/CD pipeline
│       ├── quality.yml         # Code quality checks
│       ├── unit-tests.yml      # Unit test execution
│       └── integration-tests.yml # Integration test execution
└── docker-compose.yml   # Development infrastructure
```

### Key Structure Benefits

- **🔍 Clear Separation**: Application code, tests, and configuration are clearly separated
- **📊 Test Organization**: Tests are categorized by type (unit, integration, e2e) for efficient execution
- **⚙️ Modular Dependencies**: Requirements are split by environment for optimized deployments
- **🚀 CI/CD Ready**: Structured for automated testing and deployment pipelines
- **📚 Self-Documenting**: Directory structure makes the codebase easy to navigate and understand

## 🧪 Testing Strategy

Our comprehensive testing approach ensures reliability and maintainability:

- **Unit Tests**: Individual component testing with high coverage (>90% target)
- **Integration Tests**: End-to-end workflow validation with real database connections
- **Performance Tests**: Load testing and optimization benchmarks
- **Security Tests**: Authentication, authorization, and data protection
- **CI/CD Pipeline**: Automated testing on every commit and deployment with quality gates

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository** and create your feature branch
2. **Set up development environment** using the quick start guide
3. **Write tests** for new functionality
4. **Ensure all tests pass** before submitting
5. **Create a pull request** with detailed description

### Development Guidelines

- Follow Python PEP 8 style guide for backend code
- Use TypeScript and React best practices for frontend
- Write comprehensive tests for new features
- Update documentation for API changes
- Ensure CI/CD tests pass before merging

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for complete details.

---

<div align="center">
  <p><b>Built with ❤️ for intelligent automation and data-driven insights</b></p>
  <p>AutoReportAI - Transforming data into knowledge, automatically.</p>
</div>
