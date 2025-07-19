# 故障排除指南

在开发过程中遇到问题是在所难免的。本指南旨在收集常见问题及其解决方案，帮助您快速解决开发中遇到的障碍。

## 后端问题 (Backend)

### 问题: `docker-compose up` 失败，提示端口已被占用
- **错误信息**: `Error starting userland proxy: listen tcp4 0.0.0.0:5432: bind: address already in use`
- **原因**: 您的主机上已有另一个服务（很可能是另一个PostgreSQL实例）占用了5432端口。
- **解决方案**:
  1.  **找到并停止占用端口的服务**:
      ```bash
      # macOS / Linux
      sudo lsof -i :5432
      sudo kill -9 <PID>
      ```
  2.  **修改 `docker-compose.yml`**:
      将 `ports` 映射更改为另一个未被占用的端口，例如 `5433:5432`。
      ```yaml
      # docker-compose.yml
      services:
        db:
          ports:
            - "5433:5432" # 将主机端口改为5433
      ```
      同时，您需要更新后端 `.env` 文件中的 `POSTGRES_PORT` 为 `5433`。

### 问题: `alembic upgrade head` 失败
- **错误信息**: 可能会有多种，如 `Target database is not up to date` 或 `FAILED: No such table: alembic_version`。
- **原因**:
  - 数据库与迁移文件状态不一致。
  - 数据库中没有 `alembic_version` 表（通常是第一次运行失败导致）。
  - 手动修改了数据库结构。
- **解决方案**:
  - **对于干净的开发数据库**: 最简单的方法是重置数据库。
    ```bash
    # 在项目根目录
    docker-compose down -v # -v 会删除数据库数据卷
    docker-compose up -d db
    
    # 在 backend 目录
    alembic upgrade head
    ```
  - **如果不想删除数据**:
    1.  检查当前数据库的版本: `alembic current`
    2.  检查迁移历史: `alembic history --verbose`
    3.  尝试将数据库标记为最新版本: `alembic stamp head`，然后重试。
    4.  如果问题复杂，可能需要手动介入数据库，或在Alembic社区寻求帮助。**切勿在生产环境随意操作。**

### 问题: `ModuleNotFoundError: No module named 'app'`
- **原因**: Python解释器无法找到您的项目模块。这通常是因为您没有在项目根目录（或正确的目录）下运行命令，或者虚拟环境未激活。
- **解决方案**:
  1.  确保您的Python虚拟环境已激活。
  2.  确保您在 `backend` 目录下运行 `uvicorn` 或 `pytest` 命令。
  3.  检查您的 `PYTHONPATH` 是否正确设置。项目结构已经配置为相对导入，通常不需要手动设置 `PYTHONPATH`。

### 问题: `SECRET_KEY` 相关的安全警告
- **原因**: `.env` 文件中的 `SECRET_KEY` 太简单或未设置。
- **解决方案**:
  - 生成一个足够复杂的密钥并更新到 `.env` 文件中。
    ```bash
    openssl rand -hex 32
    ```

## 前端问题 (Frontend)

### 问题: `npm install` 失败
- **原因**:
  - 网络问题，无法从npm仓库下载包。
  - Node.js或npm版本不兼容。
  - 缓存问题。
- **解决方案**:
  1.  **检查Node.js版本**: 确保您的Node版本符合 `package.json` 中 `engines` 字段的要求。
  2.  **清除缓存**: `npm cache clean --force`
  3.  **删除 `node_modules` 和 `package-lock.json`**:
      ```bash
      rm -rf node_modules package-lock.json
      npm install
      ```
  4.  **检查网络**: 如果您在中国大陆，可以尝试使用淘宝镜像源 `npm config set registry https://registry.npmmirror.com`。

### 问题: 连接后端API失败 (Fetch/CORS error)
- **错误信息**: 浏览器控制台出现 `net::ERR_CONNECTION_REFUSED` 或 CORS 策略错误。
- **原因**:
  - 后端服务未运行。
  - 前端 `.env.local` 文件中的 `NEXT_PUBLIC_API_BASE_URL` 配置错误。
  - 后端CORS配置不允许来自前端源 (`http://localhost:3000`) 的请求。
- **解决方案**:
  1.  确保您的后端FastAPI服务正在 `http://localhost:8000` 上运行。
  2.  检查 `frontend/.env.local` 文件，确保 `NEXT_PUBLIC_API_BASE_URL` 的值是 `http://localhost:8000`。
  3.  检查 `backend/app/main.py` 中的 `CORSMiddleware` 配置，确保 `allow_origins` 包含了 `http://localhost:3000`。

### 问题: Next.js Hydration Error
- **错误信息**: `Error: Hydration failed because the initial UI does not match what was rendered on the server.`
- **原因**: 服务器端渲染(SSR)的HTML与客户端首次渲染的HTML不匹配。这通常发生在代码中存在仅在客户端执行的逻辑，如访问 `window` 对象、使用 `localStorage`，或者基于 `Math.random()` 渲染。
- **解决方案**:
  1.  **使用 `useEffect`**: 将仅限客户端的逻辑移入 `useEffect` hook 中，因为它只在客户端执行。
  2.  **动态导入**: 对于完全不应在服务器上渲染的组件，使用 `next/dynamic` 进行动态导入，并关闭SSR。
      ```tsx
      import dynamic from 'next/dynamic'
      const NoSsrComponent = dynamic(() => import('../components/NoSsr'), { ssr: false })
      ```
  3.  **检查 `suppressHydrationWarning`**: 对于不可避免的微小差异（如时间戳），可以在元素上添加 `suppressHydrationWarning={true}` 属性，但这应作为最后手段。

---

如果这里没有您遇到的问题，请随时向团队提问或在项目的Issue中进行讨论！ 