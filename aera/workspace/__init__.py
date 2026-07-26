# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Workspace subsystem: project scanning, indexing and search."""

from .indexer import (
    EXTENSION_LANGUAGES,
    PROJECT_MARKERS,
    IndexedFile,
    Project,
    WorkspaceIndexer,
)

__all__ = [
    "EXTENSION_LANGUAGES",
    "PROJECT_MARKERS",
    "IndexedFile",
    "Project",
    "WorkspaceIndexer",
]
