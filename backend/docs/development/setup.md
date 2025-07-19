# 开发环境设置指南

本指南将帮助您在本地机器上设置AutoReportAI的开发环境。

## 1. 概述

AutoReportAI项目采用现代化的全栈架构：
- **后端**: 基于 [FastAPI](https://fastapi.tiangolo.com/) 的Python应用，负责API、业务逻辑和数据处理。
- **前端**: 基于 [Next.js](https://nextjs.org/) 和 [TypeScript](https://www.typescriptlang.org/) 的React应用，提供用户界面。
- **数据库**: 使用 [PostgreSQL](https://www.postgresql.org/)，通过 [Docker](https://www.docker.com/) 运行以便于管理。
- **依赖管理**: 后端使用 `pip` + `venv`，前端使用 `npm`。
- **数据库迁移**: 使用 [Alembic](https://alembic.sqlalchemy.org/en/latest/) 管理数据库模式变更。

## 2. 环境要求

在开始之前，请确保您已安装以下工具：
- **Python**: 3.9 或更高版本
- **Node.js**: 18.x 或更高版本 (推荐使用 `nvm` 管理)
- **Docker** 和 **Docker Compose**: 最新版本
- **Git**: 最新版本

## 3. 后端设置

### 3.1 克隆仓库
```bash
git clone https://github.com/your-org/AutoReportAI.git
cd AutoReportAI/backend
```

### 3.2 设置Python虚拟环境
我们推荐使用`venv`进行环境隔离。

```bash
# 创建虚拟环境
python3 -m venv ../venv

# 激活虚拟环境
# macOS / Linux
source ../venv/bin/activate
# Windows
# ..\venv\Scripts\activate
```

### 3.3 安装依赖
项目提供了不同环境的依赖文件。

```bash
# 安装开发环境所需的所有依赖
pip install -r requirements/development.txt
```

### 3.4 配置环境变量
环境变量是管理应用配置的关键。

1.  **复制示例文件**:
    ```bash
    # 在 backend 目录下
    cp .env.example .env
    ```

2.  **编辑 `.env` 文件**:
    打开 `.env` 文件并根据您的本地环境进行配置。至少需要配置 `POSTGRES_PASSWORD` 和 `SECRET_KEY`。
    
    ```dotenv
    # .env
    
    # 数据库配置
    POSTGRES_SERVER=localhost
    POSTGRES_PORT=5432
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=your_super_secret_password # 替换为强密码
    POSTGRES_DB=autoreport_dev
    
    # FastAPI
    SECRET_KEY=a_very_secret_key_that_is_long_and_random # 使用 openssl rand -hex 32 生成
    
    # ...其他配置...
    ```

### 3.5 启动数据库
我们使用Docker Compose来管理数据库服务。

```bash
# 确保Docker正在运行
# 在项目根目录 AutoReportAI/ 下运行
docker-compose up -d db
```
这将会在后台启动一个PostgreSQL数据库容器。

### 3.6 运行数据库迁移
使用Alembic来创建和更新数据库表结构。

```bash
# 确保虚拟环境已激活
# 在 backend 目录下运行
alembic upgrade head
```
这将根据 `migrations/versions` 中的迁移脚本更新数据库。

### 3.7 初始化数据 (可选)
如果需要填充一些初始数据（如超级用户），可以运行初始化脚本。

```bash
# 在 backend 目录下运行
python app/initial_data.py
```

### 3.8 运行后端开发服务器
现在可以启动FastAPI应用了。

```bash
# 在 backend 目录下运行
uvicorn app.main:app --reload
```
服务器将在 `http://localhost:8000` 上运行。您可以在 `http://localhost:8000/docs` 查看API文档。

### 3.9 使用 `Makefile`
为了简化操作，我们提供了一个 `Makefile`。

```bash
# 运行开发服务器
make run

# 运行所有测试
make test

# 格式化代码
make format

# 检查代码风格
make lint
```

## 4. 前端设置

### 4.1 安装依赖
```bash
cd ../frontend
npm install
```

### 4.2 配置环境变量
1.  **复制示例文件**:
    ```bash
    cp .env.local.example .env.local
    ```

2.  **编辑 `.env.local` 文件**:
    通常默认配置即可连接本地后端。
    ```env
    # .env.local
    NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
    ```

### 4.3 运行前端开发服务器
```bash
npm run dev
```
前端应用将在 `http://localhost:3000` 上运行。

## 5. 开发工作流

1.  从 `main` 分支创建一个新的特性分支: `git checkout -b feature/my-new-feature`
2.  在后端或前端进行代码修改。
3.  **后端**:
    - 如果修改了数据库模型，创建新的迁移: `alembic revision --autogenerate -m "Add new feature"`
    - 运行迁移: `alembic upgrade head`
    - 编写或更新测试。
    - 运行测试: `make test`
    - 格式化和检查代码: `make format && make lint`
4.  **前端**:
    - 编写或更新组件和页面。
    - 编写或更新测试。
    - 运行测试: `npm test`
    - 格式化和检查代码: `npm run format && npm run lint`
5.  提交您的更改。
6.  推送分支并发起Pull Request。