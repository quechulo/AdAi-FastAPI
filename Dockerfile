# Multi-stage Dockerfile for FastAPI on Google Cloud Run
# Stage 1: Build dependencies
FROM python:3.13-slim AS builder

WORKDIR /app

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY alembic.ini .
COPY alembic/ alembic/
COPY app/ app/

# Make sure scripts are in PATH
ENV PATH=/root/.local/bin:$PATH

# Ensure Python is available in PATH for MCP subprocess
ENV PYTHONUNBUFFERED=1

# Expose port (Cloud Run will set PORT env var dynamically)
EXPOSE 8080

# Health check
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#     CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health').read()"

# Run the application with uvicorn
# Cloud Run injects PORT environment variable, defaulting to 8080
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --loop uvloop
