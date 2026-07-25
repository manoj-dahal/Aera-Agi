"""AERA API layer: REST endpoints, WebSocket gateway and middleware."""

from .app import create_app

__all__ = ["create_app"]
