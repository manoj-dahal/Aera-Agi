# ──────────────────────────────────────────────────
# AERA AGI — multi-stage Dockerfile
# Stage 1: build frontend | Stage 2: backend runtime
# ──────────────────────────────────────────────────

# ---- Stage 1: Frontend build ----
FROM node:20-alpine AS frontend
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci || npm install
COPY tsconfig.json vite.config.ts ./
COPY public ./public
COPY shared ./shared
COPY src ./src
RUN npm run build

# ---- Stage 2: Backend runtime ----
FROM python:3.12-slim AS runtime
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    AERA_ENV=production

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY services ./services
COPY shared ./shared
COPY config ./config
COPY prompts ./prompts
COPY database ./database
COPY --from=frontend /app/dist ./public

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["uvicorn", "services.core.main:app", "--host", "0.0.0.0", "--port", "8000"]
