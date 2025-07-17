# PESS Scoring System Dockerfile
# Multi-stage build for optimized production image

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VERSION=1.0.0

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set build arguments
ARG BUILD_DATE
ARG VERSION=1.0.0

# Add labels
LABEL maintainer="Jr Dev Agent Team" \
      version=${VERSION} \
      description="PESS - Prompt Effectiveness Scoring System" \
      build-date=${BUILD_DATE}

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    APP_HOME=/app \
    APP_USER=pessuser \
    APP_GROUP=pessgroup

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user and group
RUN groupadd -r ${APP_GROUP} && \
    useradd -r -g ${APP_GROUP} -d ${APP_HOME} -s /sbin/nologin -c "PESS Service User" ${APP_USER}

# Create application directory
WORKDIR ${APP_HOME}

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data tmp && \
    chown -R ${APP_USER}:${APP_GROUP} ${APP_HOME} && \
    chmod -R 755 ${APP_HOME}

# Create health check script
RUN echo '#!/bin/bash\n\
curl -f http://localhost:8005/health || exit 1' > /usr/local/bin/health-check && \
    chmod +x /usr/local/bin/health-check

# Switch to non-root user
USER ${APP_USER}

# Expose port
EXPOSE 8005

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /usr/local/bin/health-check

# Environment variables for configuration
ENV DATABASE_URL=postgresql://pess_user:pess_password@postgres:5432/pess_db \
    LOG_LEVEL=INFO \
    WORKERS=1 \
    MAX_CONNECTIONS=100 \
    TIMEOUT=300

# Volume for persistent data
VOLUME ["${APP_HOME}/data", "${APP_HOME}/logs"]

# Default command
CMD ["python", "-m", "uvicorn", "pess_scoring.service:app", "--host", "0.0.0.0", "--port", "8005", "--workers", "1", "--log-level", "info"]

# Alternative commands for different environments
# Development: docker run -e ENV=development pess-scoring
# Production: docker run -e ENV=production pess-scoring
# Debug: docker run -e ENV=debug pess-scoring

# Build information
RUN echo "PESS Scoring System v${VERSION} built on ${BUILD_DATE}" > /app/build-info.txt

# Security: Remove any potentially sensitive files
RUN find ${APP_HOME} -name "*.pyc" -delete && \
    find ${APP_HOME} -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Final verification
RUN python -c "import pess_scoring; print('PESS Scoring System loaded successfully')" 