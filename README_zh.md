<div align="center">
  <img src="https://raw.githubusercontent.com/user-attachments/assets/15ba393a-864a-4f1c-8af2-8b43834a3b04" width="150" alt="AutoReportAI Logo">
  <h1>AutoReportAI</h1>
  <p>
    <b>一个由任务驱动、以调度器为核心的智能自动化报告生成系统。</b>
  </p>
  <p>
    AutoReportAI 通过一个完全自动化、可定制的工作流，将原始数据转化为精美的Word文档（.docx）。
  </p>

  <p>
    <a href="https://github.com/your-username/AutoReportAI/stargazers"><img src="https://img.shields.io/github/stars/your-username/AutoReportAI?style=flat-square" alt="GitHub stars"></a>
    <a href="https://github.com/your-username/AutoReportAI/forks"><img src="https://img.shields.io/github/forks/your-username/AutoReportAI?style=flat-square" alt="GitHub forks"></a>
    <a href="https://github.com/your-username/AutoReportAI/issues"><img src="https://img.shields.io/github/issues/your-username/AutoReportAI?style=flat-square" alt="GitHub issues"></a>
    <a href="./LICENSE"><img src="https://img.shields.io/github/license/your-username/AutoReportAI?style=flat-square" alt="License"></a>
  </p>

  <p>
    <a href="./README.md">English</a> | <b>简体中文</b>
  </p>
</div>

---

## ✨ 核心功能

AutoReportAI 不仅仅是一个报告生成器，它是一个构建在强大的、以调度器为中心的架构之上的完整自动化平台。

- **🤖 任务驱动工作流**: 通过定义一个`任务（Task）`来编排整个报告生命周期——使用什么数据、应用哪个模板、何时运行以及通知谁。
- **🕒 基于Cron的调度**: 利用 `APScheduler` 的强大功能，通过标准的Cron表达式实现精细化的自动任务执行。
- **📊 ETL与数据中心**: 在每份报告生成前，一个专门的**ETL服务**会从外部数据源获取数据，并将其加载到本地的“宽表”（分析数据中心）中。这将数据检索与报告生成解耦，确保了高性能和数据一致性。
- **🧩 动态报告合成**: 报告是动态组装的。`ToolDispatcherService` 使用AI来解释需求，从本地数据中心获取数据，并生成内容块（文本、表格、图表）。然后，`ReportCompositionService` 将这些块智能地填充到 `.docx` 模板中。
- **🔌 可插拔的AI供应商**: 抽象化的AI服务允许您通过简单的配置更改，在不同的大语言模型（例如，OpenAI、本地模拟模型）之间切换。
- **🗂️ 全面的历史与审计**: 每一次任务执行，无论成功与否，都会被记录在`ReportHistory`表中。这提供了一个完整的审计追踪，包括错误信息和生成报告的路径。
- **🌐 现代化的Web界面**: 一个使用Next.js和Tailwind CSS构建的时尚前端，用于管理任务、数据源、AI供应商和查看报告历史。

## 🏛️ 系统架构

系统由一个中央调度器编排，该调度器触发一个分为两个阶段的过程：ETL阶段和报告生成阶段。

```mermaid
graph TD
    subgraph "用户/管理员"
        A[浏览器]
    end

    subgraph "前端 (Next.js)"
        B[Web界面]
    end

    subgraph "后端 (FastAPI)"
        C{API网关}
        C -- "/tasks" --> G[1. 任务管理]
        C -- "/templates" --> D[模板管理]
        C -- "/data-sources" --> E[数据源管理]
        C -- "/history" --> K[报告历史]
    end
    
    subgraph "调度器 (APScheduler)"
        O[主调度进程]
    end

    subgraph "核心服务"
        I[ETL服务]
        P[工具调度服务]
        Q[报告合成服务]
    end

    subgraph "数据持久化 (PostgreSQL)"
        J[(数据库)]
        J -- "读/写" --> Task
        J -- "读/写" --> Template
        J -- "读/写" --> DataSource
        J -- "写" --> AnalyticsData[本地数据中心]
        J -- "写" --> ReportHistory[报告历史]
    end

    subgraph "外部依赖"
        M[业务数据库/CSV/API]
    end

    A -- "访问" --> B
    B -- "调用API" --> C
    
    O -- "1. 读取调度计划" --> Task
    O -- "2. 触发ETL" --> I
    I -- "读取配置" --> DataSource
    I -- "从外部获取" --> M
    I -- "写入" --> AnalyticsData
    
    O -- "3. 触发工具" --> P
    P -- "从本地读取" --> AnalyticsData
    
    O -- "4. 触发合成" --> Q
    Q -- "组装结果来源" --> P
    
    O -- "5. 记录结果" --> ReportHistory
```

## 🛠️ 技术栈

| 类别              | 技术栈                                                                                                                                  |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **后端**          | <img src="https://img.shields.io/badge/Python-3.9-blue.svg?logo=python&style=flat-square" alt="Python"> <img src="https://img.shields.io/badge/FastAPI-0.103-blue.svg?logo=fastapi&style=flat-square" alt="FastAPI"> <img src="https://img.shields.io/badge/SQLAlchemy-2.0-orange.svg?style=flat-square" alt="SQLAlchemy"> |
| **调度器**        | <img src="https://img.shields.io/badge/APScheduler-3.10-green.svg?style=flat-square" alt="APScheduler">                                     |
| **前端**          | <img src="https://img.shields.io/badge/Next.js-14-black.svg?logo=next.js&style=flat-square" alt="Next.js"> <img src="https://img.shields.io/badge/React-18-blue.svg?logo=react&style=flat-square" alt="React"> <img src="https://img.shields.io/badge/TypeScript-5-blue.svg?logo=typescript&style=flat-square" alt="TypeScript"> <img src="https://img.shields.io/badge/Tailwind_CSS-3-cyan.svg?logo=tailwind-css&style=flat-square" alt="Tailwind CSS"> |
| **数据库**        | <img src="https://img.shields.io/badge/PostgreSQL-15-blue.svg?logo=postgresql&style=flat-square" alt="PostgreSQL">                       |
| **DevOps**        | <img src="https://img.shields.io/badge/Docker-24-blue.svg?logo=docker&style=flat-square" alt="Docker">                                      |
| **AI集成**        | <img src="https://img.shields.io/badge/OpenAI-1.3-blue.svg?logo=openai&style=flat-square" alt="OpenAI">                                       |

## 🚀 快速上手

本项目采用混合开发模式：核心基础设施（PostgreSQL）在Docker中运行，而应用服务在本地运行。

### 1. 先决条件

- [Docker](https://www.docker.com/get-started/) 和 Docker Compose
- [Python 3.9+](https://www.python.org/downloads/)
- [Node.js](https://nodejs.org/) (v18 或更高版本) 和 npm

### 2. 后端API设置

1.  **启动数据库服务**:
    ```bash
    docker-compose up -d
    ```
    *该命令会在后台启动一个PostgreSQL容器。*

2.  **创建`.env`文件**:
    在 `backend/` 目录下创建一个名为 `.env` 的文件，并填入以下内容：
    ```dotenv
    # backend/.env
    DATABASE_URL=postgresql://autoreport:autoreport@localhost:5432/autoreport
    ```

3.  **设置Python环境**:
    ```bash
    # 在项目根目录运行
    python3 -m venv venv
    source venv/bin/activate
    # 在Windows上，使用: venv\Scripts\activate
    ```

4.  **安装Python依赖**:
    ```bash
    pip install -r backend/requirements.txt
    ```

5.  **运行后端API服务器**:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir ./backend
    ```
    *API服务器将在 `http://localhost:8000` 上可用。请保持此终端运行。*

### 3. 调度器服务设置

在**一个新的终端**中，确保Python虚拟环境已激活 (`source venv/bin/activate`)，然后运行：

```bash
python scheduler/main.py
```
*这将启动独立的调度器进程。它将连接到数据库，加载活动任务，并根据其cron计划等待执行。请保持此终端运行。*

### 4. 前端设置

1.  **安装Node.js依赖**:
    ```bash
    # 在项目根目录的一个新终端中运行
    npm install --prefix frontend
    ```

2.  **运行前端开发服务器**:
    ```bash
    npm run dev --prefix frontend
    ```
    *Web应用程序将在 `http://localhost:3000` 上可用。*

### 5. 访问应用

- **Web应用**: 访问 `http://localhost:3000`。
- **API文档**: 在 `http://localhost:8000/docs` 探索自动生成的Swagger UI。

**默认登录凭证**:
- **用户名**: `admin@example.com`
- **密码**: `password`

## 🗺️ 路线图

我们为AutoReportAI制定了宏大的计划。以下是我们接下来希望构建的一些功能：

- [ ] **完成前端开发**:
    - [ ] 功能完备的任务创建和编辑表单。
    - [ ] 可交互的报告历史查看器，包含日志和下载链接。
    - [ ] 用于系统状态概览的仪表盘。
- [ ] **更多工具集成**:
    - [ ] 高级图表选项（例如，Plotly）。
    - [ ] 在调度器中直接进行数据操作的工具。
- [ ] **增强的数据源**:
    - [ ] 支持更多数据库（例如，MySQL, SQLite）。
    - [ ] 支持云存储桶（S3, GCS）作为数据源。
- [ ] **改进的用户管理**:
    - [ ] 基于角色的访问控制（RBAC）。
    - [ ] 用于报告分发的用户组管理。
- [ ] **测试与CI/CD**:
    - [ ] 全面的单元和集成测试覆盖。
    - [ ] 用于自动化测试和部署的GitHub Actions工作流。

## 🤝 贡献

欢迎贡献！如果您对新功能、改进或错误修复有任何想法，请先创建一个issue进行讨论。

## 📄 许可证

本项目根据MIT许可证授权。详情请见 [LICENSE](./LICENSE) 文件。 