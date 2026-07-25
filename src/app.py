"""AERA Core — FastAPI application (docs/26-API.md).

Run with:
    uvicorn src.app:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src import __version__
from src.bootstrap import boot
from src.routes import api_router
from src.websocket.chat import ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    system = boot()
    app.state.system = system
    app.state.memory = system.memory
    app.state.router = system.router
    app.state.agents = system.agents
    yield
    system.shutdown()


app = FastAPI(
    title="AERA Core API",
    description="API Gateway for the AERA AI Operating System",
    version=__version__,
    lifespan=lifespan,
)

app.include_router(api_router)
app.include_router(ws_router)
