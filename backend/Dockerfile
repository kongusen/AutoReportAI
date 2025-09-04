# ==========================================
# AutoReportAI Backend Dockerfile
# React Agent Architecture - 现代化多阶段构建
# ==========================================

# ==========================================
# 基础Python镜像
# ==========================================
FROM python:3.11-slim AS base

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# 安装系统依赖 - 分阶段安装以减少内存使用
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    git \
    postgresql-client \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# 安装字体支持 - 单独安装以避免内存不足
RUN apt-get update && apt-get install -y --no-install-recommends \
    fontconfig \
    fonts-dejavu \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# 安装matplotlib依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6-dev \
    libpng-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 安装轻量中文字体
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-wqy-microhei \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*

# 创建应用用户
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# 设置工作目录
WORKDIR /app

# 创建内联字体初始化脚本
RUN echo '#!/bin/bash\n\
set -e\n\
echo "🚀 AutoReportAI 字体初始化"\n\
echo "更新字体缓存..."\n\
fc-cache -fv\n\
echo "验证中文字体安装..."\n\
CHINESE_FONTS=$(fc-list :lang=zh | wc -l)\n\
echo "检测到 $CHINESE_FONTS 个中文字体"\n\
if [ "$CHINESE_FONTS" -gt 0 ]; then\n\
    echo "✅ 中文字体安装正常"\n\
else\n\
    echo "❌ 未检测到中文字体"\n\
fi\n\
mkdir -p /home/appuser/.cache/matplotlib\n\
chown -R appuser:appuser /home/appuser/.cache 2>/dev/null || true\n\
echo "✅ 字体初始化完成"\n\
' > /tmp/init_fonts.sh && \
chmod +x /tmp/init_fonts.sh && \
/tmp/init_fonts.sh && \
rm /tmp/init_fonts.sh

# ==========================================
# 依赖安装阶段
# ==========================================
FROM base AS dependencies

# 安装Python依赖
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

FROM dependencies AS development

# 安装开发依赖
RUN pip install --no-cache-dir \
    watchdog \
    debugpy \
    ipython \
    jupyter \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    isort \
    flake8 \
    mypy

# 复制应用代码
COPY --chown=appuser:appuser . .

# 创建React Agent架构必要目录
RUN mkdir -p logs cache storage temp uploads && \
    mkdir -p cache/llamaindex cache/react_agent cache/embeddings && \
    mkdir -p storage/templates storage/reports storage/exports && \
    chown -R appuser:appuser logs cache storage temp uploads

# 复制启动脚本
COPY --chown=appuser:appuser entrypoint.sh /usr/local/bin/
COPY --chown=appuser:appuser healthcheck.sh /usr/local/bin/
COPY --chown=appuser:appuser healthcheck_worker.sh /usr/local/bin/

# 设置脚本权限
RUN chmod +x /usr/local/bin/entrypoint.sh && \
    chmod +x /usr/local/bin/healthcheck.sh && \
    chmod +x /usr/local/bin/healthcheck_worker.sh

# 切换到应用用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD bash /usr/local/bin/healthcheck.sh

# 启动命令
CMD ["/usr/local/bin/entrypoint.sh"]

# ==========================================
# Celery Worker构建 - React Agent支持
# ==========================================
FROM dependencies AS worker

# 复制应用代码
COPY --chown=appuser:appuser . .

# 创建必要目录
RUN mkdir -p logs cache storage temp uploads && \
    mkdir -p cache/llamaindex cache/react_agent cache/embeddings && \
    chown -R appuser:appuser logs cache storage temp uploads

# 复制健康检查脚本
COPY --chown=appuser:appuser healthcheck_worker.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/healthcheck_worker.sh

# 切换到应用用户
USER appuser

# 健康检查
HEALTHCHECK --interval=60s --timeout=30s --start-period=10s --retries=3 \
    CMD bash /usr/local/bin/healthcheck_worker.sh

# 启动Celery Worker with React Agent support
CMD ["celery", "-A", "app.core.celery_scheduler", "worker", \
     "--loglevel=info", \
     "--concurrency=4", \
     "--max-tasks-per-child=1000", \
     "--without-gossip", \
     "--without-mingle", \
     "--without-heartbeat"]

# ==========================================
# Celery Beat构建
# ==========================================
FROM dependencies AS beat

# 复制应用代码
COPY --chown=appuser:appuser . .

# 创建必要目录
RUN mkdir -p logs cache storage temp uploads /tmp/celerybeat && \
    chown -R appuser:appuser logs cache storage temp uploads /tmp/celerybeat

# 切换到应用用户
USER appuser

# 启动Celery Beat
CMD ["celery", "-A", "app.core.celery_scheduler", "beat", \
     "--loglevel=info", \
     "--pidfile=/tmp/celerybeat/celerybeat.pid", \
     "--schedule=/tmp/celerybeat/celerybeat-schedule"]

# ==========================================
# 生产环境构建
# ==========================================
FROM dependencies AS production

# 复制生产所需文件
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser scripts ./scripts
# 只复制存在的配置文件
COPY --chown=appuser:appuser requirements.txt ./
COPY --chown=appuser:appuser entrypoint.sh /usr/local/bin/
COPY --chown=appuser:appuser healthcheck.sh /usr/local/bin/

# 创建目录并设置权限
RUN mkdir -p logs cache storage temp uploads && \
    mkdir -p cache/llamaindex cache/react_agent cache/embeddings && \
    mkdir -p storage/templates storage/reports storage/exports && \
    chown -R appuser:appuser logs cache storage temp uploads

# 设置脚本权限
RUN chmod +x /usr/local/bin/entrypoint.sh && \
    chmod +x /usr/local/bin/healthcheck.sh

# 移除开发文件
RUN rm -rf tests/ *.md .git/

# 安装Gunicorn for production
RUN pip install --no-cache-dir gunicorn

# 切换到应用用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD bash /usr/local/bin/healthcheck.sh

# 生产启动命令
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--keep-alive", "2", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100"]