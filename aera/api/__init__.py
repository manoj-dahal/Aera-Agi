# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""AERA API layer: REST endpoints, WebSocket gateway and middleware."""

from .app import create_app

__all__ = ["create_app"]
