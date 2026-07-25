"""Memory Graph routes (docs/06-MEMORY-GRAPH.md)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from src.common.schemas import (
    MemoryEdge,
    MemoryEdgeCreate,
    MemoryGraphStats,
    MemoryNode,
    MemoryNodeCreate,
)

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/stats", response_model=MemoryGraphStats)
async def memory_stats(request: Request) -> MemoryGraphStats:
    return request.app.state.memory.stats()


@router.post("/nodes", response_model=MemoryNode, status_code=201)
async def create_node(node: MemoryNodeCreate, request: Request) -> MemoryNode:
    return request.app.state.memory.add_node(node)


@router.get("/nodes/{node_id}", response_model=MemoryNode)
async def get_node(node_id: int, request: Request) -> MemoryNode:
    try:
        return request.app.state.memory.get_node(node_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="memory node not found") from None


@router.delete("/nodes/{node_id}", status_code=204)
async def delete_node(node_id: int, request: Request) -> None:
    try:
        request.app.state.memory.delete_node(node_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="memory node not found") from None


@router.get("/nodes/{node_id}/neighbors", response_model=list[MemoryNode])
async def node_neighbors(node_id: int, request: Request) -> list[MemoryNode]:
    try:
        request.app.state.memory.get_node(node_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="memory node not found") from None
    return request.app.state.memory.neighbors(node_id)


@router.post("/edges", response_model=MemoryEdge, status_code=201)
async def create_edge(edge: MemoryEdgeCreate, request: Request) -> MemoryEdge:
    try:
        return request.app.state.memory.add_edge(edge)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.get("/recall", response_model=list[MemoryNode])
async def recall(q: str, request: Request, limit: int = 10) -> list[MemoryNode]:
    return request.app.state.memory.recall(q, limit=min(limit, 50))
