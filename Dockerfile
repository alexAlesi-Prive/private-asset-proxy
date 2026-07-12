# Privé Proxy-Asset engine — container image (multi-stage).
#
# Stage 1 builds the React/Vite SPA. Stage 2 is a small Python runtime that
# serves both the built SPA and the JSON API from one process on port 5530.

# ---- Stage 1: build the frontend -------------------------------------------
FROM node:22-slim AS frontend
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build            # -> /web/dist

# ---- Stage 2: python runtime -----------------------------------------------
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=5530 \
    HOST=0.0.0.0 \
    WEB_DIR=/app/web

WORKDIR /app

# Python deps first (layer caching).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Engine package (build context excludes resource-temp/, docs/, tests via
# .dockerignore — nothing reference-only is baked in).
COPY engine/ ./engine/

# Built SPA from stage 1.
COPY --from=frontend /web/dist ./web

# Unprivileged user; ensure the prototype store dir is writable.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/var \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5530

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import os,sys,urllib.request; \
p=os.environ.get('PORT','5530'); \
sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{p}/healthz').status==200 else 1)"

CMD ["python", "-m", "engine.service"]
