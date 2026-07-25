"""Development/production server runner for AERA Core."""

from __future__ import annotations

import uvicorn

from src.config.settings import settings


def run() -> None:
    """Start the AERA Core server using settings from the environment."""
    uvicorn.run(
        "src.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    run()
