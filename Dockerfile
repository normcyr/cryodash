# Use Debian slim base to simplify native dependency installation (psycopg)
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    TZ=America/Toronto

WORKDIR /app

# Install system dependencies and uv (curl needed)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       gcc \
       libpq-dev \
       curl \
       ca-certificates \
       tzdata \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && apt-get remove -y build-essential gcc \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy project files
COPY pyproject.toml LICENSE README.md ./
COPY cryodash ./cryodash

# Install Python dependencies with uv
RUN uv pip install --system -e .

# Create data and logs directories
RUN mkdir -p /app/data /app/logs

# Copy entrypoint and healthcheck scripts
COPY entrypoint.py /app/entrypoint.py
COPY healthcheck.sh /app/healthcheck.sh
RUN chmod +x /app/entrypoint.py /app/healthcheck.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD ["/app/healthcheck.sh"]

# Expose port
EXPOSE 8000

# Run Python entrypoint with shell to evaluate env vars
CMD ["sh", "-c", "python3 /app/entrypoint.py"]
