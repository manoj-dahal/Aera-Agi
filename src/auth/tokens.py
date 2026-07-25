"""Token service — JWT access/refresh tokens (docs/api/Authentication.md).

Documented login flow:
    User → Credentials → Authentication Server → JWT → Access Granted

Documented tokens: Access Token, Refresh Token, Session Token.
Documented session management: Login, Logout, Refresh, Expiration, Revocation.

Implementation uses stdlib-only HS256 JWTs and PBKDF2 password hashing so the
security layer has zero external dependencies ("Sensitive information is
never stored as plain text" — docs/21).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass, field


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


# ── Password hashing (docs/api/Authentication.md "Password Policy: Hashing") ──

PASSWORD_MIN_LENGTH = 8  # documented: Minimum Length


def hash_password(password: str, *, iterations: int = 200_000) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2${iterations}${_b64url(salt)}${_b64url(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt_b64, digest_b64 = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), _b64url_decode(salt_b64), int(iterations)
        )
        return hmac.compare_digest(digest, _b64url_decode(digest_b64))
    except (ValueError, TypeError):
        return False


def validate_password_policy(password: str) -> list[str]:
    """Documented policy: minimum length + complexity."""
    problems = []
    if len(password) < PASSWORD_MIN_LENGTH:
        problems.append(f"password must be at least {PASSWORD_MIN_LENGTH} characters")
    if password.isalpha() or password.isdigit():
        problems.append("password must mix letters with digits or symbols")
    return problems


# ── JWT (HS256) ───────────────────────────────────────────────


class TokenError(Exception):
    """Raised when a token is invalid, expired, or revoked."""


@dataclass
class TokenService:
    secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET", "change-me-too"))
    access_ttl: int = field(
        default_factory=lambda: int(os.getenv("JWT_EXPIRES_IN", "86400"))
    )
    refresh_ttl: int = 30 * 86_400

    def _sign(self, header_payload: str) -> str:
        sig = hmac.new(self.secret.encode(), header_payload.encode(), hashlib.sha256)
        return _b64url(sig.digest())

    def issue(self, subject: str, kind: str = "access", session_id: str | None = None) -> str:
        ttl = self.access_ttl if kind == "access" else self.refresh_ttl
        header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        payload = _b64url(
            json.dumps(
                {
                    "sub": subject,
                    "kind": kind,
                    "sid": session_id or secrets.token_hex(8),
                    "iat": int(time.time()),
                    "exp": int(time.time()) + ttl,
                }
            ).encode()
        )
        head = f"{header}.{payload}"
        return f"{head}.{self._sign(head)}"

    def verify(self, token: str, kind: str = "access") -> dict:
        try:
            header, payload, signature = token.split(".")
        except ValueError:
            raise TokenError("malformed token") from None
        if not hmac.compare_digest(self._sign(f"{header}.{payload}"), signature):
            raise TokenError("invalid signature")
        claims = json.loads(_b64url_decode(payload))
        if claims.get("kind") != kind:
            raise TokenError(f"expected {kind} token")
        if claims.get("exp", 0) < time.time():
            raise TokenError("token expired")
        return claims
