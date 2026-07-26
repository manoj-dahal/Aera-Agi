# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Plugin endpoints (docs/17-PLUGIN-SYSTEM.md).

Discovery, manifest validation and the approval lifecycle. Execution is
deliberately not offered: see aera/services/plugins.py for why, and
``/plugins/{id}/load`` for the message a caller gets if they try.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends

from ...core.errors import ValidationError
from ...services.plugins import PERMISSIONS, PLUGIN_TYPES
from ..deps import get_kernel_dep
from ..schemas import ok

router = APIRouter(prefix="/plugins", tags=["plugins"])


def _registry(kernel):
    registry = getattr(kernel, "plugins", None)
    if registry is None:
        raise ValidationError("the plugin registry is unavailable")
    return registry


@router.get("")
async def list_plugins(state: str | None = None, kernel=Depends(get_kernel_dep)):
    """Every discovered plugin, optionally filtered by lifecycle state."""
    registry = _registry(kernel)
    plugins = registry.all()
    if state:
        plugins = [p for p in plugins if p.state.value == state]
    return ok(
        {
            "plugins": [p.to_dict() for p in plugins],
            "count": len(plugins),
            "stats": registry.stats(),
        }
    )


@router.post("/scan")
async def scan_plugins(kernel=Depends(get_kernel_dep)):
    """Re-read the plugins directory, picking up newly added folders."""
    plugins = _registry(kernel).scan()
    return ok(
        {"plugins": [p.to_dict() for p in plugins], "count": len(plugins)},
        f"Found {len(plugins)} plugin(s)",
    )


@router.get("/capabilities")
async def plugin_capabilities():
    """What a manifest may declare, and what the runtime can actually do."""
    return ok(
        {
            "types": sorted(PLUGIN_TYPES),
            "permissions": sorted(PERMISSIONS),
            "manifest_names": ["manifest.yaml", "manifest.yml", "plugin.json"],
            # Stated plainly so a caller does not build against a capability
            # that is not there.
            "execution_supported": False,
            "execution_note": (
                "Plugins are discovered, validated and permission-gated. Executing "
                "plugin code needs process isolation, which is not built yet."
            ),
        }
    )


@router.get("/{plugin_id}")
async def get_plugin(plugin_id: str, kernel=Depends(get_kernel_dep)):
    return ok(_registry(kernel).get(plugin_id).to_dict())


@router.post("/{plugin_id}/approve")
async def approve_plugin(
    plugin_id: str,
    permissions: list[str] | None = Body(default=None, embed=True),
    kernel=Depends(get_kernel_dep),
):
    """Grant the permissions the user agreed to.

    Passing a subset is allowed -- a user may approve `workspace` but refuse
    `terminal`. Granting something the manifest never asked for is refused.
    """
    plugin = _registry(kernel).approve(plugin_id, permissions)
    return ok(plugin.to_dict(), f"Approved {plugin.name}")


@router.post("/{plugin_id}/enable")
async def enable_plugin(plugin_id: str, kernel=Depends(get_kernel_dep)):
    plugin = _registry(kernel).enable(plugin_id)
    return ok(plugin.to_dict(), f"Enabled {plugin.name}")


@router.post("/{plugin_id}/disable")
async def disable_plugin(plugin_id: str, kernel=Depends(get_kernel_dep)):
    plugin = _registry(kernel).disable(plugin_id)
    return ok(plugin.to_dict(), f"Disabled {plugin.name}")


@router.post("/{plugin_id}/revoke")
async def revoke_plugin(plugin_id: str, kernel=Depends(get_kernel_dep)):
    """Withdraw approval; the plugin returns to pending."""
    plugin = _registry(kernel).revoke(plugin_id)
    return ok(plugin.to_dict(), f"Revoked permissions for {plugin.name}")


@router.post("/{plugin_id}/load")
async def load_plugin(plugin_id: str, kernel=Depends(get_kernel_dep)):
    """Attempt to run a plugin.

    Always refuses, with the reason. This exists so the limitation surfaces
    when a caller tries to use it, rather than the endpoint simply not being
    there and looking like an oversight.
    """
    registry = _registry(kernel)
    registry.get(plugin_id)
    raise ValidationError(
        registry.load_error(plugin_id),
        details={"plugin": plugin_id, "execution_supported": False},
    )
