"""Authentication service — local login + session management (docs/21, docs/api/Authentication.md).

Documented methods (implemented now: Local Password; PIN/passkeys/OAuth later).
Documented session management: Login, Logout, Refresh, Expiration, Revocation.
Documented security: rate limiting + login monitoring (via audit events).
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field

from src.auth.tokens import (
    TokenError,
    TokenService,
    hash_password,
    validate_password_policy,
    verify_password,
)
from src.logging.logger import get_logger

log = get_logger("auth")

_MAX_ATTEMPTS = 5  # documented: Rate Limiting / Login Monitoring
_LOCKOUT_SECONDS = 300.0


class AuthError(Exception):
    """Authentication failure (bad credentials, locked out, revoked session)."""


@dataclass
class Session:
    """An active login session (docs: Active Sessions on Security Dashboard)."""

    id: str
    username: str
    created_at: float = field(default_factory=time.time)
    revoked: bool = False


@dataclass
class User:
    username: str
    password_hash: str
    role: str = "owner"  # AERA is single-user local-first; multi-user later


class AuthService:
    """Local-first authentication server."""

    def __init__(self, tokens: TokenService | None = None) -> None:
        self.tokens = tokens or TokenService()
        self.users: dict[str, User] = {}
        self.sessions: dict[str, Session] = {}
        self._failed: dict[str, list[float]] = {}  # username -> failure timestamps

    # ── Registration / Login ─────────────────────────────

    def register(self, username: str, password: str) -> User:
        if username in self.users:
            raise AuthError("user already exists")
        problems = validate_password_policy(password)
        if problems:
            raise AuthError("; ".join(problems))
        user = User(username=username, password_hash=hash_password(password))
        self.users[username] = user
        log.info("user %s registered", username)
        return user

    def _check_rate_limit(self, username: str) -> None:
        now = time.time()
        recent = [t for t in self._failed.get(username, []) if now - t < _LOCKOUT_SECONDS]
        self._failed[username] = recent
        if len(recent) >= _MAX_ATTEMPTS:
            raise AuthError("too many failed attempts — try again later")

    def login(self, username: str, password: str) -> dict[str, str]:
        """Documented flow: Credentials → Auth Server → JWT → Access Granted."""
        self._check_rate_limit(username)
        user = self.users.get(username)
        if user is None or not verify_password(password, user.password_hash):
            self._failed.setdefault(username, []).append(time.time())
            log.warning("failed login for %s", username)
            raise AuthError("invalid credentials")

        session = Session(id=secrets.token_hex(16), username=username)
        self.sessions[session.id] = session
        self._failed.pop(username, None)
        return {
            "access_token": self.tokens.issue(username, "access", session.id),
            "refresh_token": self.tokens.issue(username, "refresh", session.id),
            "token_type": "bearer",
        }

    # ── Session management (Login/Logout/Refresh/Expiration/Revocation) ──

    def verify_access(self, token: str) -> Session:
        claims = self.tokens.verify(token, "access")
        session = self.sessions.get(claims["sid"])
        if session is None or session.revoked:
            raise TokenError("session revoked")
        return session

    def refresh(self, refresh_token: str) -> dict[str, str]:
        claims = self.tokens.verify(refresh_token, "refresh")
        session = self.sessions.get(claims["sid"])
        if session is None or session.revoked:
            raise TokenError("session revoked")
        return {
            "access_token": self.tokens.issue(session.username, "access", session.id),
            "token_type": "bearer",
        }

    def logout(self, token: str) -> None:
        claims = self.tokens.verify(token, "access")
        session = self.sessions.get(claims["sid"])
        if session:
            session.revoked = True

    def revoke_session(self, session_id: str) -> None:
        session = self.sessions.get(session_id)
        if session is None:
            raise KeyError("session not found")
        session.revoked = True

    def active_sessions(self) -> list[Session]:
        return [s for s in self.sessions.values() if not s.revoked]
