# AutoReportAI MCP Server Dockerfile

FROM docker.io/python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir uvicorn[standard]

# 复制应用代码
COPY . .

# 设置环境变量
ENV MCP_SERVER_HOST=0.0.0.0
ENV MCP_SERVER_PORT=8001
ENV BACKEND_BASE_URL=http://backend:8000/api/v1

# 暴露端口
EXPOSE 8001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

# 启动命令
CMD ["python", "main_sse.py"]