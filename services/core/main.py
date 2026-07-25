"""AERA Core — FastAPI application entry point.

Run in development:
    uvicorn services.core.main:app --reload

This is the API Gateway described in docs/26-API.md, hosting the
Agent Manager (docs/07), Memory Graph (docs/06), and Model Router
(docs/18, 19) per docs/02-SYSTEM-ARCHITECTURE.md.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from services.agents.manager import AgentManager
from services.ai.router import ModelRouter
from services.memory.graph import MemoryGraph
from shared.schemas import (
    AgentInfo,
    MemoryEdge,
    MemoryEdgeCreate,
    MemoryGraphStats,
    MemoryNode,
    MemoryNodeCreate,
    ModelInfo,
    TaskRequest,
    TaskResponse,
)

__version__ = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.memory = MemoryGraph()
    app.state.router = ModelRouter()
    app.state.agents = AgentManager(app.state.memory, app.state.router)
    yield
    app.state.memory.close()


app = FastAPI(
    title="AERA Core API",
    description="API Gateway for the AERA AI Operating System",
    version=__version__,
    lifespan=lifespan,
)


# ── System ────────────────────────────────────────────────────


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
    """System information for the dashboard status panel."""
    local_ai = await app.state.router.ollama_available()
    return {
        "name": "AERA",
        "version": __version__,
        "modules": {
            "memory_graph": "active",
            "agents": "active",
            "model_router": "active",
            "local_ai": "online" if local_ai else "offline",
            "voice": "planned",
            "hologram": "planned",
            "automation": "planned",
        },
    }


# ── AI Chat (Core Agent entry point) ──────────────────────────


@app.post("/api/chat", response_model=TaskResponse)
async def chat(task: TaskRequest) -> TaskResponse:
    """Send a message to AERA. The Agent Manager routes it automatically."""
    return await app.state.agents.execute(task)


# ── Agents ────────────────────────────────────────────────────


@app.get("/api/agents", response_model=list[AgentInfo])
async def list_agents() -> list[AgentInfo]:
    return app.state.agents.list_agents()


# ── Models ────────────────────────────────────────────────────


@app.get("/api/models", response_model=list[ModelInfo])
async def list_models() -> list[ModelInfo]:
    return await app.state.router.list_models()


# ── Memory Graph ──────────────────────────────────────────────


@app.get("/api/memory/stats", response_model=MemoryGraphStats)
async def memory_stats() -> MemoryGraphStats:
    return app.state.memory.stats()


@app.post("/api/memory/nodes", response_model=MemoryNode, status_code=201)
async def create_node(node: MemoryNodeCreate) -> MemoryNode:
    return app.state.memory.add_node(node)


@app.get("/api/memory/nodes/{node_id}", response_model=MemoryNode)
async def get_node(node_id: int) -> MemoryNode:
    try:
        return app.state.memory.get_node(node_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="memory node not found") from None


@app.delete("/api/memory/nodes/{node_id}", status_code=204)
async def delete_node(node_id: int) -> None:
    try:
        app.state.memory.delete_node(node_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="memory node not found") from None


@app.get("/api/memory/nodes/{node_id}/neighbors", response_model=list[MemoryNode])
async def node_neighbors(node_id: int) -> list[MemoryNode]:
    try:
        app.state.memory.get_node(node_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="memory node not found") from None
    return app.state.memory.neighbors(node_id)


@app.post("/api/memory/edges", response_model=MemoryEdge, status_code=201)
async def create_edge(edge: MemoryEdgeCreate) -> MemoryEdge:
    try:
        return app.state.memory.add_edge(edge)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@app.get("/api/memory/recall", response_model=list[MemoryNode])
async def recall(q: str, limit: int = 10) -> list[MemoryNode]:
    return app.state.memory.recall(q, limit=min(limit, 50))


# ── WebSocket (streaming conversation) ────────────────────────


@app.websocket("/ws")
async def websocket_chat(ws: WebSocket) -> None:
    """Bidirectional chat channel (docs/api/WebSocket.md)."""
    await ws.accept()
    try:
        while True:
            message = await ws.receive_text()
            result = await app.state.agents.execute(TaskRequest(message=message))
            await ws.send_json(result.model_dump())
    except WebSocketDisconnect:
        pass


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
