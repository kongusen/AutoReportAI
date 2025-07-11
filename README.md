<div align="center">
  <img src="https://raw.githubusercontent.com/user-attachments/assets/15ba393a-864a-4f1c-8af2-8b43834a3b04" width="150" alt="AutoReportAI Logo">
  <h1>AutoReportAI</h1>
  <p>
    <b>An intelligent, task-driven, and scheduler-centric automated report generation system.</b>
  </p>
  <p>
    AutoReportAI transforms raw data into polished Word documents (`.docx`) through a fully automated, customizable workflow.
  </p>

  <p>
    <a href="https://github.com/your-username/AutoReportAI/stargazers"><img src="https://img.shields.io/github/stars/your-username/AutoReportAI?style=flat-square" alt="GitHub stars"></a>
    <a href="https://github.com/your-username/AutoReportAI/forks"><img src="https://img.shields.io/github/forks/your-username/AutoReportAI?style=flat-square" alt="GitHub forks"></a>
    <a href="https://github.com/your-username/AutoReportAI/issues"><img src="https://img.shields.io/github/issues/your-username/AutoReportAI?style=flat-square" alt="GitHub issues"></a>
    <a href="./LICENSE"><img src="https://img.shields.io/github/license/your-username/AutoReportAI?style=flat-square" alt="License"></a>
  </p>

  <p>
    <b>English</b> | <a href="./README_zh.md">简体中文</a>
  </p>
</div>

---

## ✨ Key Features

AutoReportAI is not just a report generator; it's a complete automation platform built on a robust, scheduler-centric architecture.

- **🤖 Task-Driven Workflow**: Define a `Task` to orchestrate the entire reporting lifecycle—what data to use, which template to apply, when to run, and who to notify.
- **🕒 Cron-Based Scheduling**: Leverage the power of `APScheduler` for fine-grained, automated task execution using standard cron expressions.
- **📊 ETL & Data Mart**: Before each report, a dedicated **ETL service** fetches data from external sources and loads it into a local "wide table" (analytics data mart). This decouples data retrieval from report generation, ensuring high performance and data consistency.
- **🧩 Dynamic Report Composition**: Reports are assembled dynamically. A `ToolDispatcherService` uses AI to interpret needs, fetch data from the local data mart, and generate content blocks (text, tables, charts). A `ReportCompositionService` then intelligently populates these blocks into `.docx` templates.
- **🔌 Pluggable AI Providers**: Abstracted AI services allow you to switch between different Large Language Models (e.g., OpenAI, a local mock) via a simple configuration change.
- **🗂️ Comprehensive History & Auditing**: Every task execution, whether successful or failed, is logged in a `ReportHistory` table. This provides a complete audit trail, including error messages and paths to generated reports.
- **🌐 Modern Web Interface**: A sleek frontend built with Next.js and Tailwind CSS for managing tasks, data sources, AI providers, and viewing report history.

## 🏛️ System Architecture

The system is orchestrated by a central scheduler, which triggers a two-phase process: the ETL phase and the Report Generation phase.

```mermaid
graph TD
    subgraph "User/Admin"
        A[Browser]
    end

    subgraph "Frontend (Next.js)"
        B[Web UI]
    end

    subgraph "Backend (FastAPI)"
        C{API Gateway}
        C -- "/tasks" --> G[1. Task Management]
        C -- "/templates" --> D[Template Mgmt]
        C -- "/data-sources" --> E[Data Source Mgmt]
        C -- "/history" --> K[Report History]
    end
    
    subgraph "Scheduler (APScheduler)"
        O[Master Scheduler Process]
    end

    subgraph "Core Services"
        I[ETLService]
        P[ToolDispatcherService]
        Q[ReportCompositionService]
    end

    subgraph "Data Persistence (PostgreSQL)"
        J[(Database)]
        J -- R/W --> Task
        J -- R/W --> Template
        J -- R/W --> DataSource
        J -- Write --> AnalyticsData[Local Data Mart]
        J -- Write --> ReportHistory
    end

    subgraph "External Dependencies"
        M[Business DBs/CSVs/APIs]
    end

    A -- Visits --> B
    B -- Calls API --> C
    
    O -- "1. Reads schedule" --> Task
    O -- "2. Triggers ETL" --> I
    I -- "Reads config" --> DataSource
    I -- "Fetches from" --> M
    I -- "Writes to" --> AnalyticsData
    
    O -- "3. Triggers Tools" --> P
    P -- "Reads from" --> AnalyticsData
    
    O -- "4. Triggers Composition" --> Q
    Q -- "Assembles results from" --> P
    
    O -- "5. Logs result" --> ReportHistory
```

## 🛠️ Tech Stack

| Category          | Technology                                                                                                                              |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Backend**       | <img src="https://img.shields.io/badge/Python-3.9-blue.svg?logo=python&style=flat-square" alt="Python"> <img src="https://img.shields.io/badge/FastAPI-0.103-blue.svg?logo=fastapi&style=flat-square" alt="FastAPI"> <img src="https://img.shields.io/badge/SQLAlchemy-2.0-orange.svg?style=flat-square" alt="SQLAlchemy"> |
| **Scheduler**     | <img src="https://img.shields.io/badge/APScheduler-3.10-green.svg?style=flat-square" alt="APScheduler">                                     |
| **Frontend**      | <img src="https://img.shields.io/badge/Next.js-14-black.svg?logo=next.js&style=flat-square" alt="Next.js"> <img src="https://img.shields.io/badge/React-18-blue.svg?logo=react&style=flat-square" alt="React"> <img src="https://img.shields.io/badge/TypeScript-5-blue.svg?logo=typescript&style=flat-square" alt="TypeScript"> <img src="https://img.shields.io/badge/Tailwind_CSS-3-cyan.svg?logo=tailwind-css&style=flat-square" alt="Tailwind CSS"> |
| **Database**      | <img src="https://img.shields.io/badge/PostgreSQL-15-blue.svg?logo=postgresql&style=flat-square" alt="PostgreSQL">                       |
| **DevOps**        | <img src="https://img.shields.io/badge/Docker-24-blue.svg?logo=docker&style=flat-square" alt="Docker">                                      |
| **AI Integration**| <img src="https://img.shields.io/badge/OpenAI-1.3-blue.svg?logo=openai&style=flat-square" alt="OpenAI">                                       |


## 🚀 Quick Start

This project uses a hybrid development model: core infrastructure (PostgreSQL) runs in Docker, while application services run locally.

### 1. Prerequisites

- [Docker](https://www.docker.com/get-started/) & Docker Compose
- [Python 3.9+](https://www.python.org/downloads/)
- [Node.js](https://nodejs.org/) (v18 or higher) & npm

### 2. Backend API Setup

1.  **Start Database Service**:
    ```bash
    docker-compose up -d
    ```
    *This spins up a PostgreSQL container in the background.*

2.  **Create `.env` file**:
    Create a file named `.env` in the `backend/` directory with the following content:
    ```dotenv
    # backend/.env
    DATABASE_URL=postgresql://autoreport:autoreport@localhost:5432/autoreport
    ```

3.  **Setup Python Environment**:
    ```bash
    # From the project root
    python3 -m venv venv
    source venv/bin/activate
    # On Windows, use: venv\Scripts\activate
    ```

4.  **Install Python Dependencies**:
    ```bash
    pip install -r backend/requirements.txt
    ```

5.  **Run Backend API Server**:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir ./backend
    ```
    *The API server will be available at `http://localhost:8000`. Keep this terminal running.*

### 3. Scheduler Service Setup

In a **new terminal**, ensure the Python virtual environment is activated (`source venv/bin/activate`) and run:

```bash
python scheduler/main.py
```
*This starts the standalone scheduler process. It will connect to the database, load active tasks, and wait to execute them based on their cron schedules. Keep this terminal running.*

### 4. Frontend Setup

1.  **Install Node.js Dependencies**:
    ```bash
    # From the project root, in a new terminal
    npm install --prefix frontend
    ```

2.  **Run Frontend Dev Server**:
    ```bash
    npm run dev --prefix frontend
    ```
    *The web application will be available at `http://localhost:3000`.*

### 5. Accessing the Application

- **Web App**: Navigate to `http://localhost:3000`.
- **API Docs**: Explore the auto-generated Swagger UI at `http://localhost:8000/docs`.

**Default Login**:
- **Username**: `admin@example.com`
- **Password**: `password`

## 🗺️ Roadmap

We have ambitious plans for AutoReportAI. Here are some of the features we're looking to build next:

- [ ] **Frontend Completion**:
    - [ ] Fully functional Task creation and editing form.
    - [ ] Interactive report history viewer with logs and download links.
    - [ ] Dashboard for system status overview.
- [ ] **More Tool Integrations**:
    - [ ] Advanced charting options (e.g., Plotly).
    - [ ] Direct data manipulation tools within the dispatcher.
- [ ] **Enhanced Data Sources**:
    - [ ] Support for more databases (e.g., MySQL, SQLite).
    - [ ] Support for cloud storage buckets (S3, GCS) as data sources.
- [ ] **Improved User Management**:
    - [ ] Role-based access control (RBAC).
    - [ ] User group management for report distribution.
- [ ] **Testing & CI/CD**:
    - [ ] Comprehensive unit and integration test coverage.
    - [ ] GitHub Actions workflow for automated testing and deployment.

## 🤝 Contributing

Contributions are welcome! If you have ideas for new features, improvements, or bug fixes, please open an issue to discuss it first.

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.
