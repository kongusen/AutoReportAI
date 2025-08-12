# Simple production image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
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
        git \
        dumb-init \
        procps && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Create app user and group
RUN groupadd --gid 1001 app && \
    useradd --uid 1001 --gid app --shell /bin/bash --create-home app

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    -r requirements.txt

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