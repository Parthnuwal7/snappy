# Snappy backend — Cloud Run image (self-contained; build context = backend/).
#
# Deploy from the repo root with:
#   gcloud run deploy snappy-backend --source backend --region asia-northeast1
#
# Building from backend/ keeps the Cloud Build upload small — only this folder
# is sent as context (see .dockerignore), not the frontend/website/node_modules.

FROM python:3.11-slim

# uv: ~10-100x faster than pip. Copy the static binary from the official image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# System deps: libpq for psycopg2, gcc for any wheels needing compilation.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first so this layer caches across code-only changes.
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Application code.
COPY . .

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

EXPOSE 8080

# App-factory pattern. workers x threads = concurrent requests per instance;
# keep Cloud Run --concurrency in sync (8).
CMD exec gunicorn \
    --bind :$PORT \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    'app.main:create_app()'
