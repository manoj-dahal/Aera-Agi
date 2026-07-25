"""Security routes — dashboard, permissions, audit (docs/21-SECURITY.md).

Security Dashboard (documented): Security Score, Active Sessions, Running
Plugins, Recent Security Events.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from src.security.permissions import Permission

router = APIRouter(prefix="/security", tags=["security"])


@router.get("/dashboard")
async def dashboard(request: Request) -> dict[str, object]:
    """Documented Security Dashboard data."""
    system = request.app.state.system
    sessions = system.auth.active_sessions()
    denied = len(system.audit.recent(500, "permission.denied"))
    alerts = len(system.audit.recent(500, "security.alert"))
    # Simple documented "Security Score": start at 100, subtract signals.
    score = max(0, 100 - denied * 2 - alerts * 10)
    return {
        "security_score": score,
        "active_sessions": len(sessions),
        "zero_trust_mode": system.auth_required,
        "threat_alerts": alerts,
        "recent_events": [
            {"event": e.event, "subject": e.subject, "detail": e.detail,
             "timestamp": e.timestamp.isoformat()}
            for e in system.audit.recent(10)
        ],
    }


@router.get("/permissions/{subject}")
async def get_permissions(subject: str, request: Request) -> dict[str, object]:
    return {
        "subject": subject,
        "permissions": request.app.state.system.permissions.grants_for(subject),
    }


@router.post("/permissions/{subject}/grant/{permission}")
async def grant_permission(subject: str, permission: str, request: Request) -> dict:
    try:
        perm = Permission(permission)
    except ValueError:
        valid = ", ".join(p.value for p in Permission)
        raise HTTPException(status_code=422, detail=f"unknown permission; valid: {valid}") from None
    request.app.state.system.permissions.grant(subject, perm)
    return {"subject": subject, "granted": perm.value}


@router.post("/permissions/{subject}/revoke/{permission}")
async def revoke_permission(subject: str, permission: str, request: Request) -> dict:
    try:
        perm = Permission(permission)
    except ValueError:
        raise HTTPException(status_code=422, detail="unknown permission") from None
    request.app.state.system.permissions.revoke(subject, perm)
    return {"subject": subject, "revoked": perm.value}


@router.get("/audit")
async def audit_log(request: Request, limit: int = 50, prefix: str = "") -> list[dict]:
    entries = request.app.state.system.audit.recent(min(limit, 200), prefix)
    return [
        {"event": e.event, "subject": e.subject, "detail": e.detail,
         "timestamp": e.timestamp.isoformat()}
        for e in entries
    ]
