# --- Base image ---
FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps needed to build psycopg / other native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# --- Dependencies layer (cached separately from app code) ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- App code ---
COPY app ./app
COPY scripts ./scripts

# dbt project is mounted/copied separately if this container also runs dbt;
# omit if dbt runs in its own step/container.
# COPY ../dbt ./dbt

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD curl -f http://localhost:8000/health || exit 1

# Production default. For local dev with hot-reload, override the command
# in docker-compose.yml instead of baking --reload in here, e.g.:
#   command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]