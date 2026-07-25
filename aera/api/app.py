"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .. import __version__
from ..core.config import AeraConfig, get_config
from ..core.errors import AeraError
from ..core.kernel import Kernel, set_kernel
from ..core.logging import get_logger
from .middleware import (
    AuthMiddleware,
    ErrorEnvelopeMiddleware,
    RateLimitMiddleware,
    RequestContextMiddleware,
)
from .routers import (
    agents,
    automation,
    chat,
    memory,
    skills,
    system,
    voice,
    websocket,
    workspace,
)

logger = get_logger("api.app")

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

DESCRIPTION = """
**AERA** - Artificial Enhanced Reasoning Assistant.

A modular AI Operating System combining a persistent Memory Graph, multi-agent
orchestration, local/cloud model routing, workflow automation, voice interaction
and workspace intelligence.

* `POST /api/v1/chat` - main conversational entry point
* `POST /api/v1/memory/search` - hybrid semantic + graph recall
* `GET  /api/v1/agents` - agent roster and capabilities
* `WS   /ws` - live token streaming and system events
"""


def create_app(config: AeraConfig | None = None, *, kernel: Kernel | None = None) -> FastAPI:
    """Build the ASGI application."""
    cfg = config or get_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        active = kernel or Kernel(cfg)
        set_kernel(active)
        app.state.kernel = active
        if not active.ready:
            await active.start()
        try:
            yield
        finally:
            await active.stop()

    app = FastAPI(
        title="AERA API",
        description=DESCRIPTION,
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.config = cfg

    # -- middleware (outermost first) --------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time"],
    )
    app.add_middleware(AuthMiddleware, config=cfg.api)
    app.add_middleware(RateLimitMiddleware, limit_per_minute=cfg.api.rate_limit_per_minute)
    app.add_middleware(ErrorEnvelopeMiddleware)
    app.add_middleware(RequestContextMiddleware)

    # -- exception handlers -------------------------------------------------
    @app.exception_handler(AeraError)
    async def aera_error_handler(_: Request, exc: AeraError):
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "code": 400,
                "error": "Validation failed",
                "type": "validation_error",
                "details": {"errors": exc.errors()[:10]},
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(_: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "code": exc.status_code,
                "error": str(exc.detail),
            },
        )

    # -- routes -------------------------------------------------------------
    prefix = cfg.api.prefix
    app.include_router(system.health_router)
    app.include_router(chat.router, prefix=prefix)
    app.include_router(agents.router, prefix=prefix)
    app.include_router(memory.router, prefix=prefix)
    app.include_router(workspace.router, prefix=prefix)
    app.include_router(voice.voice_router, prefix=prefix)
    app.include_router(voice.avatar_router, prefix=prefix)
    app.include_router(automation.router, prefix=prefix)
    app.include_router(skills.router, prefix=prefix)
    app.include_router(system.router, prefix=prefix)
    app.include_router(websocket.router)

    # -- dashboard ----------------------------------------------------------
    if WEB_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

        @app.get("/", include_in_schema=False)
        async def dashboard():
            index = WEB_DIR / "index.html"
            if index.is_file():
                return FileResponse(index)
            return JSONResponse({"success": True, "message": "AERA API", "version": __version__})

    logger.debug("application created with prefix %s", prefix)
    return app


app = create_app
