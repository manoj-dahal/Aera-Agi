"""Auth middleware — Zero Trust enforcement (docs/21-SECURITY.md).

"Every request ... is verified before access is granted."

Local-first default: enforcement is disabled (single-user desktop). Set
AERA_AUTH_REQUIRED=true to require a bearer token on every /api route
except the public allowlist (health, login, register, refresh, docs).
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.auth.tokens import TokenError

PUBLIC_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/refresh",
    "/docs",
    "/openapi.json",
    "/redoc",
}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        system = getattr(request.app.state, "system", None)
        if system is None or not system.auth_required:
            return await call_next(request)
        if request.url.path in PUBLIC_PATHS or not request.url.path.startswith("/api"):
            return await call_next(request)

        authorization = request.headers.get("authorization", "")
        if not authorization.lower().startswith("bearer "):
            return JSONResponse({"detail": "authentication required"}, status_code=401)
        try:
            session = system.auth.verify_access(authorization.split(" ", 1)[1])
        except TokenError as exc:
            return JSONResponse({"detail": str(exc)}, status_code=401)
        request.state.session = session
        return await call_next(request)
