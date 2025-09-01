# Multi-stage build optimized for DDD architecture and AI/ML workloads
FROM python:3.11-slim AS base

# Base environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# =============================================================================
# Dependencies Builder Stage - 预编译 AI/ML 依赖
# =============================================================================
FROM base AS deps-builder

# Install build dependencies
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        libc6-dev \
        libpq-dev \
        libffi-dev \
        libssl-dev \
        pkg-config \
        git && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and pre-compile wheels
COPY requirements.txt /tmp/
# First install basic dependencies to ensure compatibility
RUN pip install --upgrade pip setuptools wheel
# Pre-compile all dependencies including their dependencies
RUN pip wheel --no-cache-dir --wheel-dir /tmp/wheels \
    -r /tmp/requirements.txt

# =============================================================================
# Runtime Stage - 优化的运行时镜像
# =============================================================================
FROM base AS runtime

# Install only runtime dependencies
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        wget \
        dumb-init \
        procps && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# AI/ML workload memory optimization
ENV MALLOC_ARENA_MAX=2 \
    MALLOC_MMAP_THRESHOLD_=131072 \
    MALLOC_TRIM_THRESHOLD_=131072 \
    MALLOC_MMAP_MAX_=65536

# AI framework cache directories
ENV LLAMAINDEX_CACHE_DIR=/app/cache/llamaindex \
    TRANSFORMERS_CACHE=/app/cache/transformers \
    HF_HOME=/app/cache/huggingface

# Create app user and group
RUN groupadd --gid 1001 app && \
    useradd --uid 1001 --gid app --shell /bin/bash --create-home app

# Set working directory
WORKDIR /app

# Install pre-compiled dependencies
COPY --from=deps-builder /tmp/wheels /tmp/wheels
COPY requirements.txt /tmp/
RUN pip install --find-links /tmp/wheels -r /tmp/requirements.txt && \
    rm -rf /tmp/wheels /tmp/requirements.txt

# Create DDD architecture directories and cache dirs
RUN mkdir -p /app/{logs,reports,uploads,storage} \
    /app/cache/{llamaindex,transformers,huggingface} \
    /app/app/{ai,application,data,domain,infrastructure} && \
    chown -R app:app /app

# Copy application code in DDD layer order for better caching
COPY --chown=app:app app/core/ /app/app/core/
COPY --chown=app:app app/models/ /app/app/models/
COPY --chown=app:app app/schemas/ /app/app/schemas/
COPY --chown=app:app app/crud/ /app/app/crud/
COPY --chown=app:app app/db/ /app/app/db/
COPY --chown=app:app app/services/infrastructure/ /app/app/services/infrastructure/
COPY --chown=app:app app/services/domain/ /app/app/services/domain/
COPY --chown=app:app app/services/data/ /app/app/services/data/
COPY --chown=app:app app/services/application/ /app/app/services/application/
COPY --chown=app:app app/services/agents/ /app/app/services/agents/
COPY --chown=app:app app/services/llm/ /app/app/services/llm/
COPY --chown=app:app app/services/cache/ /app/app/services/cache/
COPY --chown=app:app app/api/ /app/app/api/
COPY --chown=app:app app/websocket/ /app/app/websocket/
COPY --chown=app:app app/config/ /app/app/config/
COPY --chown=app:app app/__init__.py app/main.py /app/app/

# Copy configuration and scripts
COPY --chown=app:app config/ /app/config/
COPY --chown=app:app scripts/ /app/scripts/

# Copy additional files
COPY --chown=app:app pytest.ini pyproject.toml /app/

# Copy entrypoint and healthcheck scripts
COPY --chown=app:app entrypoint.sh /app/entrypoint.sh
COPY --chown=app:app healthcheck.sh /app/healthcheck.sh
COPY --chown=app:app healthcheck_worker.sh /app/healthcheck_worker.sh

# Make scripts executable first (before bytecode compilation)
RUN chmod +x /app/entrypoint.sh /app/healthcheck.sh /app/healthcheck_worker.sh /app/scripts/startup_check.py

# Pre-compile Python bytecode for faster startup (but keep startup_check.py)
RUN python -m compileall -b /app/app/ /app/scripts/ && \
    find /app/app -name "*.py" -delete && \
    find /app/scripts -name "*.py" -not -name "startup_check.py" -delete && \
    find /app/app /app/scripts -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Switch to app user
USER app

# Expose port
EXPOSE 8000

# Enhanced health check for new architecture
HEALTHCHECK --interval=30s --timeout=20s --start-period=60s --retries=3 \
    CMD /app/healthcheck.sh

# Set default entrypoint
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["/app/entrypoint.sh", "api"] 