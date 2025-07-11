[English Version](./README.md)

# AutoReportAI - 自动化报告生成系统

AutoReportAI 是一个强大的、**由任务驱动的**自动化报告生成平台。用户可以通过配置一个**任务（Task）**来定义报告的整个生命周期：使用哪个Word模板，从哪个数据源获取数据，何时通过Cron表达式进行调度，以及最终报告发送给哪些收件人。

## ✨ 主要功能

- **任务驱动与调度**:
    - 以“任务”为核心，编排报告生成的所有环节。
    - 支持Cron表达式，实现灵活的定时调度（如每小时、每天、每周）。
- **数据ETL与宽表**:
    - 在报告生成前，自动从外部数据源执行ETL流程。
    - 将数据加载到本地的**分析宽表**中，实现高效率的数据查询。
- **动态Word模板**: 支持在 `.docx` 模板中使用 `{{text}}`, `[chart:name]`, `[table:name]` 等多种占位符。
- **多源数据获取**: 可集中管理和连接多种数据源（SQL、CSV、API）。
- **可配置AI服务**:
    - 支持通过API配置和切换不同的AI供应商（如OpenAI）。
    - 利用大语言模型（LLM）根据自然语言描述和数据动态生成图表和分析文本。
- **报告历史与审计**:
    - 自动记录每一次任务执行的结果（成功或失败）。
    - 可追溯历史报告文件和错误信息。
- **Web管理界面**: 提供一个基于Next.js的现代化Web界面，用于管理任务、数据源、AI供应商等核心资源。
- **用户认证与授权**: 基于JWT的安全机制，保护所有核心API。

## 🛠️ 技术栈

- **后端**: FastAPI, Python 3.9, SQLAlchemy, Pandas
- **任务调度**: APScheduler
- **前端**: Next.js, React, TypeScript, Tailwind CSS, Axios
- **数据库**: PostgreSQL
- **部署与开发**: Docker, Docker Compose
- **AI集成**: OpenAI

## 🚀 本地开发环境设置

本项目采用“Docker + 本地虚拟环境”的混合模式进行开发，以兼顾效率和环境一致性。

### 1. 先决条件

- [Docker](https://www.docker.com/get-started/) 和 Docker Compose
- [Python 3.9+](https://www.python.org/downloads/)
- [Node.js](https://nodejs.org/) (v18 或更高) 和 npm

### 2. 后端API服务设置

1.  **启动数据库服务**:
    ```bash
    docker-compose up -d
    ```
    *该命令会根据 `docker-compose.yml` 在后台启动一个PostgreSQL数据库容器。*

2.  **创建`.env`文件**:
    在 `backend/` 目录下，创建一个名为 `.env` 的文件，并填入以下内容。
    ```dotenv
    # backend/.env
    DATABASE_URL=postgresql://autoreport:autoreport@localhost:5432/autoreport
    ```

3.  **创建并激活Python虚拟环境**:
    ```bash
    # 在项目根目录运行
    python3 -m venv venv
    source ven/bin/activate
    ```
    *在Windows上，激活命令为 `venv\Scripts\activate`*

4.  **安装Python依赖**:
    ```bash
    pip install -r backend/requirements.txt
    ```

5.  **启动后端API服务器**:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir ./backend
    ```
    *服务将在 `http://localhost:8000` 上运行。请**保持此终端运行**。*
    *首次启动时，它会自动在数据库中创建所有表，并生成一个默认用户。*

### 3. 调度器服务设置

**在一个新的终端窗口中**，确保你仍然在激活的Python虚拟环境中 (`source venv/bin/activate`)，然后运行以下命令：

```bash
python scheduler/main.py
```
*这将启动独立的调度器进程。它会连接到数据库，加载所有活动任务，并根据其Cron计划等待执行。请**保持此终端运行**以确保定时任务能被触发。*

### 4. 前端设置 (Frontend)

1.  **安装Node.js依赖**:
    ```bash
    # 在一个新终端中，于项目根目录运行
    npm install --prefix frontend
    ```

2.  **启动前端开发服务器**:
    ```bash
    npm run dev --prefix frontend
    ```
    *服务将在 `http://localhost:3000` 上运行。*

### 5. 访问应用

- **前端应用**: 打开浏览器，访问 `http://localhost:3000`。
- **后端API文档**: 访问 `http://localhost:8000/docs` 可以查看由FastAPI自动生成的Swagger UI。

**默认登录凭证**:
- **用户名**: `admin@example.com`
- **密码**: `password` 