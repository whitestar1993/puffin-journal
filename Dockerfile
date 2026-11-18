# syntax=docker/dockerfile:1

# ---- 1. Frontend build -------------------------------------------------------
FROM node:22-alpine AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- 2. Python dependencies --------------------------------------------------
FROM python:3.13-slim AS backend-build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1
RUN python -m venv /venv
ENV PATH=/venv/bin:$PATH
WORKDIR /app
COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install .

# ---- Optional: run the test suite (`docker build --target test .`) -----------
FROM backend-build AS test
COPY backend/ ./
RUN pip install ".[dev]" && pytest -q -p no:cacheprovider

# ---- 3. Runtime --------------------------------------------------------------
FROM python:3.13-slim AS runtime
ENV PATH=/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data \
    STATIC_DIR=/app/static \
    TZ=UTC

RUN groupadd --gid 1000 app \
 && useradd --uid 1000 --gid app --no-create-home --shell /usr/sbin/nologin app \
 && mkdir -p /data && chown app:app /data

COPY --from=backend-build /venv /venv
WORKDIR /app
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY --from=frontend /src/dist ./static
COPY docker/entrypoint.sh /entrypoint.sh

USER app
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"

ENTRYPOINT ["/entrypoint.sh"]
