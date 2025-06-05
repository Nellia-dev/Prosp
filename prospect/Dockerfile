# Multi-stage Dockerfile for Nellia Prospector
FROM python:3.12-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    make \
    libc6-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download and install Playwright browsers (needed for web scraping)
RUN playwright install --with-deps chromium

# Copy application code
COPY . .

# Create data and logs directories
RUN mkdir -p /app/data /app/logs

# ===================================
# MCP Server Stage
# ===================================
FROM base as mcp-server

# Set environment variables for MCP server
ENV PYTHONPATH=/app
ENV FLASK_APP=mcp-server/app.py
ENV FLASK_ENV=production

# Initialize MCP database
RUN cd /app/mcp-server && python init_db.py

# Expose MCP server port
EXPOSE 5001

# Health check for MCP server
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Start MCP server with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "--timeout", "120", "--chdir", "mcp-server", "app:app"]

# ===================================
# Agents System Stage
# ===================================
FROM base as agents-system

# Set environment variables for agents
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash nellia
RUN chown -R nellia:nellia /app
USER nellia

# Expose port for potential agent APIs (currently not used)
EXPOSE 7777

# Health check for agents system (check if main components are accessible)
HEALTHCHECK --interval=60s --timeout=30s --start-period=60s --retries=3 \
    CMD python -c "from agents.enhanced_lead_processor import EnhancedLeadProcessor; print('Agents system healthy')" || exit 1

# Default command runs enhanced main (can be overridden)
CMD ["python", "enhanced_main.py", "--help"]

# ===================================
# Development Stage (optional)
# ===================================
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir \
    jupyter \
    ipython \
    debugpy

# Install additional development tools
RUN apt-get update && apt-get install -y \
    vim \
    htop \
    tree \
    && rm -rf /var/lib/apt/lists/*

# Expose Jupyter port
EXPOSE 8888

# Development command
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]

# ===================================
# Legacy Harvester Stage (for backward compatibility)
# ===================================
FROM base as harvester

# Set environment for harvester
ENV PYTHONPATH=/app

# Expose harvester port
EXPOSE 7777

# Health check for harvester
HEALTHCHECK --interval=60s --timeout=30s --start-period=60s --retries=3 \
    CMD python -c "import harvester; print('Harvester healthy')" || exit 1

# Start harvester
CMD ["python", "harvester.py"]