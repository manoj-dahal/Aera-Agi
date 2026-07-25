"""Workspace endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..deps import get_kernel_dep, get_workspace
from ..schemas import WorkspaceOpenRequest, WorkspaceSearchRequest, ok

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("")
async def workspace_info(workspace=Depends(get_workspace)):
    return ok(
        {
            "active": workspace.summary(),
            "projects": [p.to_dict() for p in workspace.projects.values()],
        }
    )


@router.post("/open")
async def open_workspace(payload: WorkspaceOpenRequest, kernel=Depends(get_kernel_dep)):
    """Open a folder as the active project and index it."""
    project = kernel.workspace.open(payload.path, index=payload.index)
    if payload.index:
        await kernel.workspace.sync_to_memory()
    await kernel.bus.publish(
        "workspace.opened", {"project": project.name, "root": str(project.root)}
    )
    return ok(project.to_dict(), f"Workspace '{project.name}' opened")


@router.post("/index")
async def index_workspace(kernel=Depends(get_kernel_dep)):
    result = kernel.workspace.index()
    stored = await kernel.workspace.sync_to_memory()
    await kernel.bus.publish("workspace.indexed", {"files": result.get("files", 0)})
    return ok({**result, "memory_nodes": stored}, "Workspace indexed")


@router.get("/search")
async def search_workspace_get(
    q: str = Query(...), limit: int = Query(20, ge=1, le=200), workspace=Depends(get_workspace)
):
    matches = workspace.search(q, limit=limit)
    return ok({"results": matches, "count": len(matches)})


@router.post("/search")
async def search_workspace(payload: WorkspaceSearchRequest, workspace=Depends(get_workspace)):
    matches = workspace.search(payload.query, limit=payload.limit)
    return ok({"results": matches, "count": len(matches)})


@router.get("/tree")
async def workspace_tree(
    limit: int = Query(500, ge=1, le=5000), workspace=Depends(get_workspace)
):
    return ok({"files": workspace.tree(max_entries=limit)})


@router.get("/file")
async def read_workspace_file(path: str = Query(...), workspace=Depends(get_workspace)):
    """Read a file from the active project (sandboxed to the project root)."""
    return ok(workspace.read_file(path))
