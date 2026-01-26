FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml LICENSE README.md ./
COPY cryodash ./cryodash

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -e .

# Create data and logs directories
RUN mkdir -p /app/data /app/logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Expose port
EXPOSE 8000

# Default command - run with uvicorn factory pattern
CMD ["uvicorn", "cryodash.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
