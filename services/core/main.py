"""AERA Core — FastAPI application entry point.

Run in development:
    uvicorn services.core.main:app --reload

This is the API Gateway described in docs/26-API.md. It will grow to host
the Agent Manager, Memory Engine, and Model Router (docs/02-SYSTEM-ARCHITECTURE.md).
"""

from __future__ import annotations

import os

from fastapi import FastAPI

__version__ = "0.1.0"

app = FastAPI(
    title="AERA Core API",
    description="API Gateway for the AERA AI Operating System",
    version=__version__,
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Liveness probe used by Docker healthchecks and the dashboard."""
    return {
        "status": "ok",
        "version": __version__,
        "env": os.getenv("AERA_ENV", "development"),
    }


@app.get("/api/system/info")
async def system_info() -> dict[str, object]:
    """Basic system information for the dashboard status panel."""
    return {
        "name": "AERA",
        "version": __version__,
        "modules": {
            "memory_graph": "planned",
            "agents": "planned",
            "voice": "planned",
            "hologram": "planned",
            "automation": "planned",
        },
    }


def main() -> None:
    """Run the development server (used by `make dev`)."""
    import uvicorn

    uvicorn.run(
        "services.core.main:app",
        host=os.getenv("AERA_HOST", "0.0.0.0"),
        port=int(os.getenv("AERA_PORT", "8000")),
        reload=os.getenv("AERA_ENV", "development") == "development",
    )


if __name__ == "__main__":
    main()
