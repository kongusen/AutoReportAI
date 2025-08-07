# Multi-stage build for optimized production image
# Stage 1: Build stage
FROM docker.io/python:3.11-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Configure apt to use IPv4 only and disable parallel downloads
RUN echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4 && \
    echo 'Acquire::http::Pipeline-Depth "0";' >> /etc/apt/apt.conf.d/99force-ipv4 && \
    echo 'Acquire::http::No-Cache true;' >> /etc/apt/apt.conf.d/99force-ipv4 && \
    echo 'Acquire::BrokenProxy    "true";' >> /etc/apt/apt.conf.d/99force-ipv4

# Install system dependencies for building
RUN apt-get update --fix-missing && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements files
COPY ./requirements/ /app/requirements/

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org && \
    pip install --no-cache-dir -r /app/requirements/production.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org

# Stage 2: Production stage
FROM python:3.11-slim AS production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# Configure apt to use IPv4 only and disable parallel downloads
RUN echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4 && \
    echo 'Acquire::http::Pipeline-Depth "0";' >> /etc/apt/apt.conf.d/99force-ipv4 && \
    echo 'Acquire::http::No-Cache true;' >> /etc/apt/apt.conf.d/99force-ipv4 && \
    echo 'Acquire::BrokenProxy    "true";' >> /etc/apt/apt.conf.d/99force-ipv4

# Install only runtime dependencies
RUN apt-get update --fix-missing && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN addgroup --system --gid 1001 app && \
    adduser --system --uid 1001 --gid 1001 app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=app:app . /app

# Copy and set up health check script
COPY --chown=app:app ./scripts/healthcheck_backend.sh /healthcheck.sh
RUN chmod +x /healthcheck.sh

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD /healthcheck.sh

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
