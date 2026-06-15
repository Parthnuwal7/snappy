# Snappy backend — Cloud Run image.
#
# Builds from the project root so we copy only `backend/`. Run with:
#   docker build -f backend/Dockerfile -t snappy-backend .
# Or via Cloud Build: `gcloud run deploy --source=.` from project root with
# cloudbuild's auto-detection (set --source pointing at backend/).

FROM python:3.11-slim

# uv: ~10-100x faster than pip for resolution + install. Copying the static
# binary from the official image is the leanest install path.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# System deps: libpq for psycopg2, build tools for any wheels that need
# compiling. --no-install-recommends keeps the image small.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first so Docker can cache this layer across code changes.
# --system installs into the container's system Python (no venv needed inside
# a single-purpose container). gunicorn is already pinned in requirements.txt.
COPY backend/requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Copy application code.
COPY backend/ ./

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

EXPOSE 8080

# gunicorn app-factory pattern — calls create_app() to build the Flask app.
# Workers x threads = max concurrent requests handled per instance; keep
# Cloud Run's --concurrency in sync (we set 8 in the deploy command).
CMD exec gunicorn \
    --bind :$PORT \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    'app.main:create_app()'
