# AERA - production image (docs/27-DOCKER.md)
# Multi-stage: build wheels once, ship a slim non-root runtime.

# --------------------------------------------------------------------------- #
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# --------------------------------------------------------------------------- #
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    AERA_CONFIG_DIR=/app/config \
    AERA_SYSTEM__STORAGE=/data \
    AERA_SYSTEM__LOGS=/data/logs \
    AERA_SYSTEM__CACHE=/data/cache \
    AERA_SYSTEM__TEMP=/data/temp \
    AERA_SECURITY__SECRET_KEY_FILE=/data/.secret.key

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl tini \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 aera

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-index --find-links=/wheels -r requirements.txt && rm -rf /wheels

COPY aera/ ./aera/
COPY config/ ./config/
COPY pyproject.toml README.md ./
RUN pip install --no-deps -e .

# Runtime state lives on a volume, owned by the unprivileged user.
RUN mkdir -p /data/logs /data/cache /data/temp && chown -R aera:aera /data /app
VOLUME ["/data"]

USER aera
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:8080/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "aera", "serve", "--host", "0.0.0.0", "--port", "8080"]
