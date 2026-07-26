# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Memory Graph endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..deps import get_memory
from ..schemas import (
    MemoryConnectRequest,
    MemorySearchRequest,
    MemoryStoreRequest,
    MemoryUpdateRequest,
    ok,
)

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("")
async def list_memory(
    limit: int = Query(50, ge=1, le=500),
    node_type: str | None = None,
    memory_type: str | None = None,
    tag: str | None = None,
    project_id: str | None = None,
    memory=Depends(get_memory),
):
    nodes = memory.graph.find(
        node_type=node_type, memory_type=memory_type,
        tag=tag, project_id=project_id, limit=limit,
    )
    return ok({"memories": [n.to_public() for n in nodes], "count": len(nodes)})


@router.post("")
@router.post("/store")
async def store_memory(payload: MemoryStoreRequest, memory=Depends(get_memory)):
    node = await memory.store(
        title=payload.title,
        content=payload.content,
        node_type=payload.type,
        memory_type=payload.memory_type,
        tags=payload.tags,
        importance=payload.importance,
        creator="api",
        project_id=payload.project_id,
        conversation_id=payload.conversation_id,
        metadata=payload.metadata,
        related_to=payload.related_to,
    )
    return ok(node.to_public(), "Memory stored")


@router.get("/search")
async def search_memory_get(
    q: str = Query("", alias="q"),
    limit: int = Query(10, ge=1, le=100),
    project_id: str | None = None,
    memory=Depends(get_memory),
):
    results = await memory.recall(q, limit=limit, project_id=project_id)
    return ok({"results": [r.to_public() for r in results], "count": len(results)})


@router.post("/search")
async def search_memory(payload: MemorySearchRequest, memory=Depends(get_memory)):
    results = await memory.recall(
        payload.query,
        limit=payload.limit,
        node_types=payload.node_types,
        memory_types=payload.memory_types,
        tags=payload.tags,
        project_id=payload.project_id,
        expand_hops=payload.expand_hops,
    )
    return ok({"results": [r.to_public() for r in results], "count": len(results)})


@router.get("/stats")
async def memory_stats(memory=Depends(get_memory)):
    return ok(memory.stats())


@router.get("/history")
async def memory_history(
    conversation_id: str | None = None,
    limit: int = Query(20, ge=1, le=200),
    memory=Depends(get_memory),
):
    if conversation_id:
        nodes = memory.conversation_history(conversation_id, limit=limit)
    else:
        nodes = memory.recent(limit=limit)
    return ok({"history": [n.to_public() for n in nodes], "count": len(nodes)})


@router.post("/graph")
async def graph_view(
    node_id: str | None = None,
    max_hops: int = Query(2, ge=1, le=4),
    limit: int = Query(50, ge=1, le=300),
    memory=Depends(get_memory),
):
    """Return a node-and-edge slice for graph visualisation."""
    graph = memory.graph
    if node_id:
        centre = graph.get_node(node_id)
        related = graph.traverse(node_id, max_hops=max_hops, limit=limit)
        nodes = [centre, *(n for n, _ in related)]
    else:
        nodes = graph.find(limit=limit)

    ids = {n.id for n in nodes}
    edges = [
        e.model_dump()
        for n in nodes
        for e in graph.edges_of(n.id, direction="out")
        if e.target in ids
    ]
    return ok(
        {
            "nodes": [n.to_public() for n in nodes],
            "edges": edges,
            "stats": graph.stats(),
        }
    )


@router.post("/connect")
async def connect_nodes(payload: MemoryConnectRequest, memory=Depends(get_memory)):
    edge = memory.graph.connect(
        payload.source, payload.target, payload.relation, weight=payload.weight
    )
    return ok(edge.model_dump(), "Nodes connected")


@router.post("/consolidate")
async def consolidate(memory=Depends(get_memory)):
    return ok(await memory.consolidate(), "Memory consolidated")


@router.get("/{node_id}")
async def get_memory_node(node_id: str, memory=Depends(get_memory)):
    node = memory.graph.get_node(node_id, touch=True)
    neighbors = memory.graph.neighbors(node_id)
    return ok(
        {
            "node": node.to_public(),
            "neighbors": [n.to_public() for n in neighbors],
            "edges": [e.model_dump() for e in memory.graph.edges_of(node_id)],
        }
    )


@router.patch("/{node_id}")
async def update_memory(node_id: str, payload: MemoryUpdateRequest, memory=Depends(get_memory)):
    changes = payload.model_dump(exclude_none=True)
    node = await memory.update(node_id, **changes)
    return ok(node.to_public(), "Memory updated")


@router.delete("")
@router.delete("/remove")
async def remove_memory_query(node_id: str = Query(...), memory=Depends(get_memory)):
    await memory.remove(node_id)
    return ok({"id": node_id}, "Memory removed")


@router.delete("/{node_id}")
async def remove_memory(node_id: str, memory=Depends(get_memory)):
    await memory.remove(node_id)
    return ok({"id": node_id}, "Memory removed")
