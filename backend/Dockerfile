# Multi-stage build for optimized and stable production image
# Stage 1: Base image with system dependencies
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Configure apt for better reliability
RUN echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4 && \
    echo 'Acquire::http::Pipeline-Depth "0";' >> /etc/apt/apt.conf.d/99force-ipv4 && \
    echo 'Acquire::http::No-Cache "true";' >> /etc/apt/apt.conf.d/99force-ipv4 && \
    echo 'Acquire::BrokenProxy "true";' >> /etc/apt/apt.conf.d/99force-ipv4

# Stage 2: Dependencies builder
FROM base as builder

# Install system dependencies required for building Python packages
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        wget \
        gcc \
        g++ \
        libc6-dev \
        libpq-dev \
        libffi-dev \
        libssl-dev \
        pkg-config \
        git && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Set working directory
WORKDIR /app

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --no-cache-dir --upgrade \
    pip==23.3.1 \
    setuptools==69.0.2 \
    wheel==0.42.0

# Copy requirements file
COPY requirements.txt /app/

# Install Python dependencies with better error handling
RUN pip install --no-cache-dir --timeout=300 \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    -r requirements.txt

# Stage 3: Production runtime
FROM base as production

# Install only runtime dependencies
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
        curl \
        wget \
        libpq5 \
        libffi8 \
        libssl3 \
        ca-certificates \
        dumb-init \
        procps && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Create app user and group with specific UID/GID for consistency
RUN groupadd --gid 1001 app && \
    useradd --uid 1001 --gid app --shell /bin/bash --create-home app

# Copy virtual environment from builder
COPY --from=builder --chown=app:app /opt/venv /opt/venv

# Set PATH to use virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/logs /app/reports /app/uploads /app/storage && \
    chown -R app:app /app

# Copy application code
COPY --chown=app:app . /app/

# Copy entrypoint and healthcheck scripts
COPY --chown=app:app entrypoint.sh /app/entrypoint.sh
COPY --chown=app:app healthcheck.sh /app/healthcheck.sh

# Make scripts executable
RUN chmod +x /app/entrypoint.sh /app/healthcheck.sh

# Switch to app user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=15s --start-period=40s --retries=3 \
    CMD /app/healthcheck.sh

# Set default entrypoint
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["/app/entrypoint.sh", "api"] 