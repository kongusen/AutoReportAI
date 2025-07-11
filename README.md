# AutoReportAI - 自动化报告生成系统

AutoReportAI 是一个强大的、模板驱动的自动化报告生成平台。用户可以上传Word文档作为报告模板，通过灵活配置的数据源（SQL、CSV、API）自动填充数据，并利用可插拔的AI服务（如OpenAI）智能生成图表和分析文本，最终实现报告的自动化生成、分发和归档。

## ✨ 主要功能

- **动态Word模板**: 支持在 `.docx` 模板中使用 `{{text}}`, `[chart:name]`, `[table:name]` 等多种占位符。
- **多源数据获取**: 可集中管理和连接多种数据源，包括：
    - **SQL数据库**: 直接执行SQL查询。
    - **CSV文件**: 从本地文件系统读取数据。
    - **外部API**: 调用第三方REST API获取数据。
- **可配置AI服务**:
    - 支持通过API配置和切换不同的AI供应商（如OpenAI）。
    - 利用大语言模型（LLM）根据自然语言描述和数据动态生成图表。
    - 利用LLM对数据进行分析并生成摘要文本。
- **用户认证与授权**: 基于JWT的安全机制，保护所有核心API。
- **Web管理界面**: 提供一个基于Next.js的现代化Web界面，用于：
    - 登录和用户管理。
    - 统一管理数据源和AI供应商配置。
    - (待开发) 模板管理、任务调度、报告查看。

## 🛠️ 技术栈

- **后端**: FastAPI, Python 3.9, SQLAlchemy, Pandas
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

### 2. 后端设置 (Backend)

1.  **启动数据库服务**:
    ```bash
    docker-compose up -d
    ```
    *该命令会根据 `docker-compose.yml` 在后台启动一个PostgreSQL数据库容器。*

2.  **创建`.env`文件**:
    在 `backend/` 目录下，创建一个名为 `.env` 的文件，并填入以下内容。这个文件用于存放本地开发所需的环境变量。
    ```dotenv
    # backend/.env
    DATABASE_URL=postgresql://autoreport:autoreport@localhost:5432/autoreport
    ```

3.  **创建并激活Python虚拟环境**:
    ```bash
    # 在项目根目录运行
    python3 -m venv venv
    source venv/bin/activate
    ```
    *在Windows上，激活命令为 `venv\Scripts\activate`*

4.  **安装Python依赖**:
    ```bash
    pip install -r backend/requirements.txt
    ```

5.  **启动后端开发服务器**:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir ./backend
    ```
    *服务将在 `http://localhost:8000` 上运行，并支持热重载。*
    *首次启动时，它会自动在数据库中创建所有表，并生成一个默认用户。*

### 3. 前端设置 (Frontend)

1.  **安装Node.js依赖**:
    ```bash
    # 在项目根目录运行
    npm install --prefix frontend
    ```

2.  **启动前端开发服务器**:
    ```bash
    npm run dev --prefix frontend
    ```
    *服务将在 `http://localhost:3000` 上运行，并支持热重载。*

### 4. 访问应用

- **前端应用**: 打开浏览器，访问 `http://localhost:3000`。
- **后端API文档**: 访问 `http://localhost:8000/docs` 可以查看由FastAPI自动生成的Swagger UI。

**默认登录凭证**:
- **用户名**: `admin@example.com`
- **密码**: `password`
