<div align="center">
  <img src="https://raw.githubusercontent.com/user-attachments/assets/15ba393a-864a-4f1c-8af2-8b43834a3b04" width="150" alt="AutoReportAI Logo">
  <h1>AutoReportAI</h1>
  <p>
    <b>An intelligent, AI-powered, and enterprise-ready automated report generation system.</b>
  </p>
  <p>
    AutoReportAI transforms raw data into polished Word documents (`.docx`) through a fully automated, customizable workflow with advanced AI integration and comprehensive data analytics.
  </p>

  <p>
    <a href="https://github.com/kongusen/AutoReportAI/stargazers"><img src="https://img.shields.io/github/stars/kongusen/AutoReportAI?style=flat-square" alt="GitHub stars"></a>
    <a href="https://github.com/kongusen/AutoReportAI/forks"><img src="https://img.shields.io/github/forks/kongusen/AutoReportAI?style=flat-square" alt="GitHub forks"></a>
    <a href="https://github.com/kongusen/AutoReportAI/issues"><img src="https://img.shields.io/github/issues/kongusen/AutoReportAI?style=flat-square" alt="GitHub issues"></a>
    <a href="./LICENSE"><img src="https://img.shields.io/github/license/kongusen/AutoReportAI?style=flat-square" alt="License"></a>
    <img src="https://img.shields.io/badge/Tests-100%25%20Passing-brightgreen?style=flat-square" alt="Tests">
  </p>

  <p>
    <b>English</b> | <a href="./README_zh.md">简体中文</a>
  </p>
</div>

---

## ✨ Key Features

AutoReportAI is a comprehensive automation platform that combines AI-powered intelligence with enterprise-grade reliability and modern user experience.

- **🤖 AI-Powered Analysis**: Integrated multiple AI providers (OpenAI, local models) for intelligent data analysis, content generation, and report composition with dynamic placeholder population.
- **🕒 Advanced Task Scheduling**: Robust cron-based scheduling with `APScheduler` for automated task execution, comprehensive error handling, and execution history tracking.
- **📊 Comprehensive ETL Pipeline**: Full-featured ETL engine that fetches data from multiple sources (databases, APIs, files), processes it through configurable transformations, and loads into analytics data marts.
- **🎨 Dynamic Template System**: Smart template management with placeholder detection, variable substitution, and AI-powered content generation. Supports complex document structures and formatting.
- **📈 Advanced Data Analytics**: Built-in statistical analysis, data visualization, growth calculation, and trend analysis with chart generation capabilities.
- **🔌 Multi-Provider AI Integration**: Pluggable AI architecture supporting OpenAI, local models, and custom providers with intelligent fallback mechanisms.
- **👥 User Management & Profiles**: Complete user authentication, role-based access control, user profiles, and personalized settings management.
- **🗂️ Complete Audit Trail**: Comprehensive logging of all operations, task executions, errors, and system events with detailed history tracking and reporting.
- **🌐 Modern Web Interface**: Beautiful, responsive UI built with Next.js, TypeScript, and Tailwind CSS featuring dark/light themes, dashboard analytics, and intuitive navigation.
- **🔧 Enterprise-Ready**: Production-grade deployment with Docker containerization, CI/CD pipeline, comprehensive testing suite, and database migrations.

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
- [Python 3.9+](https://www.python.org/downloads/) with pip
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
    pip install -r backend/requirements.txt
    ```

3.  **Initialize Database**:
    ```bash
    cd backend
    alembic upgrade head
    python initial_data.py  # Creates default admin user
    cd ..
    ```

4.  **Start API Server**:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir ./backend
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

### 7. Running Tests

**Backend Tests**:
```bash
cd backend
pytest -v  # Run all backend tests
pytest test_ci_cd.py -v  # Run CI/CD specific tests
```

**Frontend Tests**:
```bash
npm test --prefix frontend  # Run frontend unit tests
npm run test:coverage --prefix frontend  # With coverage report
```

**Integration Tests**:
```bash
cd backend
python test_complex_scenarios.py  # Test complex workflows
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

## 🧪 Testing Strategy

Our comprehensive testing approach ensures reliability and maintainability:

- **Unit Tests**: Individual component testing with high coverage
- **Integration Tests**: End-to-end workflow validation
- **Performance Tests**: Load testing and optimization benchmarks
- **Security Tests**: Authentication, authorization, and data protection
- **CI/CD Pipeline**: Automated testing on every commit and deployment

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
