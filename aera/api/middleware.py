# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""API middleware: request IDs, rate limiting, auth and the error envelope."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.config import ApiSection
from ..core.errors import AeraError
from ..core.logging import get_logger

logger = get_logger("api")

#: Path prefixes reachable without credentials even when auth is enabled.
#: Note: "/" is handled separately as an exact match - using it as a prefix
#: would match every request and silently disable auth and rate limiting.
PUBLIC_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json", "/static")
PUBLIC_EXACT = frozenset({"/", "/favicon.ico"})


def is_public(path: str) -> bool:
    """True when a path may be reached without authentication."""
    return path in PUBLIC_EXACT or path.startswith(PUBLIC_PREFIXES)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request id, time the call and log the outcome."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        started = time.perf_counter()

        response = await call_next(request)

        elapsed = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed:.1f}ms"
        logger.info(
            "%s %s -> %s (%.1fms)",
            request.method, request.url.path, response.status_code, elapsed,
        )
        return response


class ErrorEnvelopeMiddleware(BaseHTTPMiddleware):
    """Convert every uncaught exception into the documented error envelope."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except AeraError as exc:
            logger.warning("%s on %s: %s", type(exc).__name__, request.url.path, exc.message)
            return JSONResponse(status_code=exc.status_code, content=exc.to_dict())
        except Exception as exc:  # noqa: BLE001
            logger.exception("unhandled error on %s", request.url.path)
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "code": 500,
                    "error": "Internal Server Error",
                    "type": type(exc).__name__,
                },
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window-per-client rate limiting (spec default: 100 req/min)."""

    def __init__(self, app, *, limit_per_minute: int = 100) -> None:
        super().__init__(app)
        self.limit = max(1, limit_per_minute)
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if is_public(request.url.path):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        now = time.time()
        window = self._hits[client]
        while window and now - window[0] > 60.0:
            window.popleft()

        if len(window) >= self.limit:
            retry_after = int(60 - (now - window[0])) + 1
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "code": 429,
                    "error": "Too Many Requests",
                    "type": "rate_limited",
                },
                headers={"Retry-After": str(retry_after)},
            )

        window.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.limit - len(window)))
        return response


class AuthMiddleware(BaseHTTPMiddleware):
    """API-key / bearer-token authentication, disabled by default for local use."""

    def __init__(self, app, *, config: ApiSection) -> None:
        super().__init__(app)
        self.config = config
        self._keys = set(config.api_keys or [])

    async def dispatch(self, request: Request, call_next):
        if not self.config.auth_enabled or is_public(request.url.path):
            return await call_next(request)

        token = None
        header = request.headers.get("Authorization", "")
        if header.lower().startswith("bearer "):
            token = header[7:].strip()
        token = token or request.headers.get("X-API-Key")

        if not token or token not in self._keys:
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "code": 401,
                    "error": "Unauthorized",
                    "type": "unauthenticated",
                },
            )

        request.state.principal = f"key:{token[:8]}"
        return await call_next(request)
