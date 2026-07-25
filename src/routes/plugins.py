"""Plugin routes (docs/17-PLUGIN-SYSTEM.md — Plugin Manager surface)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.plugins.manager import PluginError
from src.plugins.models import PluginInfo, PluginPermission

router = APIRouter(prefix="/plugins", tags=["plugins"])


class ApproveBody(BaseModel):
    permissions: list[PluginPermission] | None = None  # None = approve all requested


@router.get("", response_model=list[PluginInfo])
async def list_plugins(request: Request) -> list[PluginInfo]:
    """Plugin Manager list: name, version, author, status, permissions."""
    return request.app.state.system.plugins.list()


@router.post("/discover")
async def discover(request: Request) -> dict[str, list[str]]:
    """Scan the plugins/ directory for installable plugins."""
    return {"installed": request.app.state.system.plugins.discover()}


@router.get("/{name}", response_model=PluginInfo)
async def get_plugin(name: str, request: Request) -> PluginInfo:
    try:
        return request.app.state.system.plugins._get(name).info()
    except KeyError:
        raise HTTPException(status_code=404, detail="plugin not found") from None


@router.post("/{name}/approve", response_model=PluginInfo)
async def approve(name: str, body: ApproveBody, request: Request) -> PluginInfo:
    """Users approve permissions before activation (docs/17)."""
    try:
        return request.app.state.system.plugins.approve_permissions(
            name, body.permissions
        ).info()
    except KeyError:
        raise HTTPException(status_code=404, detail="plugin not found") from None


@router.post("/{name}/enable", response_model=PluginInfo)
async def enable(name: str, request: Request) -> PluginInfo:
    try:
        plugin = await request.app.state.system.plugins.enable(name)
    except KeyError:
        raise HTTPException(status_code=404, detail="plugin not found") from None
    except PluginError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return plugin.info()


@router.post("/{name}/disable", response_model=PluginInfo)
async def disable(name: str, request: Request) -> PluginInfo:
    try:
        return (await request.app.state.system.plugins.disable(name)).info()
    except KeyError:
        raise HTTPException(status_code=404, detail="plugin not found") from None


@router.post("/{name}/reload", response_model=PluginInfo)
async def reload(name: str, request: Request) -> PluginInfo:
    """Hot Reload (documented objective)."""
    try:
        return (await request.app.state.system.plugins.reload(name)).info()
    except KeyError:
        raise HTTPException(status_code=404, detail="plugin not found") from None
    except PluginError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.delete("/{name}", status_code=204)
async def remove(name: str, request: Request) -> None:
    try:
        await request.app.state.system.plugins.remove(name)
    except KeyError:
        raise HTTPException(status_code=404, detail="plugin not found") from None
