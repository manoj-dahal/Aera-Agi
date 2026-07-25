"""Workspace routes (docs/14-WORKSPACE.md)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.workspace.models import (
    AIAssistRequest,
    ContextPanel,
    FileEntry,
    ProjectAnalysis,
    SearchResult,
)

router = APIRouter(prefix="/workspace", tags=["workspace"])


class OpenProjectBody(BaseModel):
    path: str = Field(min_length=1)


@router.post("/open", response_model=ProjectAnalysis)
async def open_project(body: OpenProjectBody, request: Request) -> ProjectAnalysis:
    """Open Project → Scanner → Analysis → Memory Graph → Ready."""
    try:
        return await request.app.state.system.workspace.open_project(body.path)
    except NotADirectoryError:
        raise HTTPException(status_code=404, detail="directory not found") from None


@router.post("/close", status_code=204)
async def close_project(request: Request) -> None:
    request.app.state.system.workspace.close_project()


@router.get("/project", response_model=ProjectAnalysis)
async def current_project(request: Request) -> ProjectAnalysis:
    project = request.app.state.system.workspace.project
    if project is None:
        raise HTTPException(status_code=404, detail="no project open")
    return project


@router.get("/files", response_model=list[FileEntry])
async def project_files(request: Request, limit: int = 500) -> list[FileEntry]:
    """Project Explorer tree data."""
    ws = request.app.state.system.workspace
    if ws.project is None:
        raise HTTPException(status_code=404, detail="no project open")
    return ws.files[: min(limit, 5000)]


@router.get("/file")
async def read_file(request: Request, path: str) -> dict[str, str]:
    """File Viewer content (safe, root-restricted)."""
    ws = request.app.state.system.workspace
    try:
        return {"path": path, "content": ws.read_file(path)}
    except RuntimeError:
        raise HTTPException(status_code=404, detail="no project open") from None
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="file not found") from None
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None


@router.get("/search", response_model=list[SearchResult])
async def search(
    request: Request, q: str, content: bool = False, limit: int = 20
) -> list[SearchResult]:
    """Workspace Search: files, folders, and text content."""
    ws = request.app.state.system.workspace
    try:
        return ws.search(q, content=content, limit=min(limit, 100))
    except RuntimeError:
        raise HTTPException(status_code=404, detail="no project open") from None


@router.post("/assist")
async def assist(body: AIAssistRequest, request: Request) -> dict[str, str]:
    """Documented AI Assistance: explain/generate/debug/refactor/document/
    find_bugs/summarize/dependencies."""
    ws = request.app.state.system.workspace
    try:
        return await ws.assist(body)
    except RuntimeError:
        raise HTTPException(status_code=404, detail="no project open") from None
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="file not found") from None


@router.get("/context", response_model=ContextPanel)
async def context_panel(request: Request) -> ContextPanel:
    """AI Context Panel (documented: updates automatically)."""
    return request.app.state.system.workspace.context_panel()
