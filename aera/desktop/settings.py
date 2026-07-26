# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Per-user desktop preferences.

Window geometry, last workspace and UI choices, stored in the OS-conventional
application data directory rather than inside the repository.
"""

from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from typing import Any

from ..core.logging import get_logger

logger = get_logger("desktop.settings")

DEFAULTS: dict[str, Any] = {
    "window_width": 1360,
    "window_height": 860,
    "window_x": None,
    "window_y": None,
    "maximized": False,
    "last_workspace": None,
    "last_view": "dashboard",
    "theme": "dark",
}


def app_data_dir(app_name: str = "AERA") -> Path:
    """The platform-appropriate per-user data directory."""
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / app_name
    path.mkdir(parents=True, exist_ok=True)
    return path


class DesktopSettings:
    """Small JSON-backed preference store."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else app_data_dir() / "preferences.json"
        self._data: dict[str, Any] = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            stored = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(stored, dict):
                self._data.update(stored)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("could not read preferences: %s", exc)

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
            tmp.replace(self.path)
        except OSError as exc:
            logger.warning("could not save preferences: %s", exc)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def update(self, values: dict[str, Any]) -> None:
        self._data.update(values)
        self.save()

    def all(self) -> dict[str, Any]:
        return dict(self._data)
