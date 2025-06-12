# Multi-stage Dockerfile for Nellia Prospector
# Supports both MCP Server and Agents System deployments

# Base stage with common dependencies
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app directory and user
RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app

# Set Hugging Face home directory for caching models
# This directory will be created and permissioned below.
ENV HF_HOME=/app/.cache/huggingface/hub

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p /app/data /app/logs /app/harvester_output && \
    chown -R appuser:appuser /app

# Create and permission Hugging Face cache directory
RUN mkdir -p /app/.cache/huggingface/hub /app/.cache/huggingface_cache && \
    chown -R appuser:appuser /app/.cache

# MCP Server target
FROM base AS mcp-server

# Install additional dependencies for web server (uvicorn for FastAPI)
RUN pip install --no-cache-dir uvicorn

# Expose MCP server port
EXPOSE 5001

# Create health check endpoint script
RUN echo '#!/bin/bash\ncurl -f http://localhost:5001/health || exit 1' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /app/healthcheck.sh

# Start MCP server with Uvicorn
CMD ["uvicorn", "mcp_server:app", "--host", "0.0.0.0", "--port", "5001", "--workers", "2"]

# Agents System target
FROM base AS agents-system

# Install additional dependencies for agents system if needed
RUN pip install --no-cache-dir playwright && \
    playwright install --with-deps chromium

# Create startup script for agents system
RUN echo '#!/bin/bash\n\
    echo "Starting Nellia Prospector Agents System..."\n\
    echo "Environment: $NODE_ENV"\n\
    echo "MCP Server URL: $MCP_SERVER_URL"\n\
    echo "Log Level: $LOG_LEVEL"\n\
    \n\
    # Wait for MCP server to be ready\n\
    if [ ! -z "$MCP_SERVER_URL" ]; then\n\
    echo "Waiting for MCP server to be ready..."\n\
    timeout=60\n\
    while [ $timeout -gt 0 ]; do\n\
    if curl -f "$MCP_SERVER_URL/health" > /dev/null 2>&1; then\n\
    echo "MCP server is ready!"\n\
    break\n\
    fi\n\
    echo "Waiting for MCP server... ($timeout seconds remaining)"\n\
    sleep 2\n\
    timeout=$((timeout-2))\n\
    done\n\
    \n\
    if [ $timeout -le 0 ]; then\n\
    echo "Warning: MCP server not ready after 60 seconds, continuing anyway..."\n\
    fi\n\
    fi\n\
    \n\
    # Start the agents system\n\
    exec python enhanced_main.py "$@"\n' > /app/start-agents.sh && \
    chmod +x /app/start-agents.sh

# Switch to non-root user
USER appuser

# Start agents system
CMD ["/app/start-agents.sh"]

# Development target (optional)
FROM base AS development

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    black \
    mypy \
    ipython \
    jupyter

# Install playwright for development
RUN pip install --no-cache-dir playwright && \
    playwright install --with-deps chromium

# Switch to non-root user
USER appuser

# Default command for development
CMD ["python", "-c", "print('Development container ready. Use docker exec to run commands.')"]
