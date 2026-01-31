# Face Similarity Platform - Docker Configuration
# Using uv package manager for fast, reliable builds

# ========================================
# Stage 1: Base Python Image with UV
# ========================================
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_SYSTEM_PYTHON=1

# Install system dependencies and uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1-mesa-glx \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install uv

# Create non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# ========================================
# Stage 2: Dependencies
# ========================================
FROM base as dependencies

WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock* ./

# Install Python dependencies with uv
RUN uv sync --frozen --no-dev

# ========================================
# Stage 3: Production
# ========================================
FROM dependencies as production

WORKDIR /app

# Copy application code
COPY --chown=appuser:appgroup . .

# Create data directories
RUN mkdir -p data/raw data/processed data/embeddings logs && \
    chown -R appuser:appgroup data logs

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Run application
CMD ["uv", "run", "python", "run.py"]

# ========================================
# Stage 4: Development
# ========================================
FROM dependencies as development

WORKDIR /app

# Install dev dependencies
RUN uv sync --frozen

# Copy application code
COPY --chown=appuser:appgroup . .

# Create data directories
RUN mkdir -p data/raw data/processed data/embeddings logs && \
    chown -R appuser:appgroup data logs

USER appuser

EXPOSE 8000

# Run with reload for development
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
