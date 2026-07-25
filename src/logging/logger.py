"""Central logger factory — consistent format across every AERA subsystem."""

from __future__ import annotations

import logging
import os
import sys

_FORMAT = "%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s"
_configured = False


def _configure_root() -> None:
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt="%H:%M:%S"))
    root = logging.getLogger("aera")
    root.addHandler(handler)
    root.setLevel(os.getenv("AERA_LOG_LEVEL", "info").upper())
    root.propagate = False
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced AERA logger (e.g. get_logger('memory'))."""
    _configure_root()
    return logging.getLogger("aera").getChild(name)
