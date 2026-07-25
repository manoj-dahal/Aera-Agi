"""Authentication routes (docs/api/Authentication.md).

Session management endpoints: register, login, refresh, logout, me.
Auth enforcement is off by default for local-first single-user use;
set AERA_AUTH_REQUIRED=true to protect the API (Zero Trust mode).
"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from src.auth.service import AuthError
from src.auth.tokens import TokenError

router = APIRouter(prefix="/auth", tags=["auth"])


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class RefreshBody(BaseModel):
    refresh_token: str


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    return authorization.split(" ", 1)[1]


@router.post("/register", status_code=201)
async def register(creds: Credentials, request: Request) -> dict[str, str]:
    auth = request.app.state.system.auth
    audit = request.app.state.system.audit
    try:
        user = auth.register(creds.username, creds.password)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    audit.record("user.registered", subject=user.username)
    return {"username": user.username, "role": user.role}


@router.post("/login")
async def login(creds: Credentials, request: Request) -> dict[str, str]:
    auth = request.app.state.system.auth
    audit = request.app.state.system.audit
    try:
        tokens = auth.login(creds.username, creds.password)
    except AuthError as exc:
        audit.record("login.failed", subject=creds.username)
        raise HTTPException(status_code=401, detail=str(exc)) from None
    audit.record("login", subject=creds.username)  # documented audit event
    return tokens


@router.post("/refresh")
async def refresh(body: RefreshBody, request: Request) -> dict[str, str]:
    try:
        return request.app.state.system.auth.refresh(body.refresh_token)
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from None


@router.post("/logout", status_code=204)
async def logout(request: Request, authorization: str | None = Header(default=None)) -> None:
    auth = request.app.state.system.auth
    try:
        token = _bearer(authorization)
        claims = auth.tokens.verify(token, "access")
        auth.logout(token)
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from None
    request.app.state.system.audit.record("logout", subject=claims["sub"])


@router.get("/me")
async def me(request: Request, authorization: str | None = Header(default=None)) -> dict:
    auth = request.app.state.system.auth
    try:
        session = auth.verify_access(_bearer(authorization))
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from None
    perms = request.app.state.system.permissions.grants_for("owner")
    return {"username": session.username, "session_id": session.id, "permissions": perms}
