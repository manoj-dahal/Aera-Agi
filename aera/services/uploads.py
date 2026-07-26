# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""User file uploads.

The avatar library had the only upload endpoint, so anything dropped on the
dashboard could not actually reach the backend -- the browser cannot hand out
a filesystem path, and the desktop shell's path is meaningless to a remote
server. Files now land here first, and agents are pointed at the stored copy.

Uploads are content-addressed by SHA-256: re-uploading the same file returns
the existing record instead of a second copy. That keeps the folder honest
when a user drags the same document in twice.
"""

from __future__ import annotations

import hashlib
import re
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.errors import ValidationError
from ..core.logging import get_logger

logger = get_logger("services.uploads")

#: Extensions that route to a specific agent. Anything else is offered to the
#: document agent, which reports honestly when it cannot parse a format.
KIND_BY_EXTENSION: dict[str, str] = {
    **dict.fromkeys(
        (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".avif", ".tiff"),
        "image",
    ),
    **dict.fromkeys((".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"), "video"),
    **dict.fromkeys((".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".opus"), "audio"),
    **dict.fromkeys(
        (".pdf", ".doc", ".docx", ".odt", ".epub", ".rtf", ".xls", ".xlsx", ".ppt", ".pptx"),
        "document",
    ),
    **dict.fromkeys(
        (".txt", ".md", ".rst", ".log", ".csv", ".json", ".yaml", ".yml", ".toml", ".xml"),
        "text",
    ),
    **dict.fromkeys(
        (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".c", ".h",
         ".cpp", ".hpp", ".cs", ".rb", ".php", ".swift", ".kt", ".sh", ".sql"),
        "code",
    ),
    **dict.fromkeys((".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar"), "archive"),
    **dict.fromkeys((".glb", ".gltf", ".obj", ".fbx", ".vrm"), "model"),
}

#: Which agent handles each kind. Vision and audio are capability-gated and
#: will say so themselves rather than inventing a result.
AGENT_BY_KIND: dict[str, str] = {
    "image": "vision",
    "video": "vision",
    "audio": "audio",
    "document": "document",
    "text": "document",
    "code": "code_review",
    "archive": "document",
    "model": "document",
    "unknown": "document",
}

#: Refuse anything larger outright rather than filling the disk.
MAX_UPLOAD_BYTES = 512 * 1024 * 1024
#: Stream in chunks so a large file never lands in memory whole.
CHUNK = 1024 * 1024

#: Characters that have no business in a filename we create.
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def classify(filename: str) -> str:
    """The broad kind of a file, from its extension."""
    return KIND_BY_EXTENSION.get(Path(filename).suffix.lower(), "unknown")


def agent_for(filename: str) -> str:
    """Which agent should be offered a file of this type."""
    return AGENT_BY_KIND.get(classify(filename), "document")


def safe_name(filename: str) -> str:
    """A filename safe to create on any OS.

    Strips directory components (``../``, ``C:\\``), normalises unicode and
    replaces anything outside a conservative set. A name that reduces to
    nothing becomes ``upload``.
    """
    # PurePath handles posix separators; split on backslash for Windows paths
    # arriving from a client that used them.
    base = Path(filename.replace("\\", "/")).name
    base = unicodedata.normalize("NFKD", base)
    base = _UNSAFE.sub("_", base).strip("._")
    if not base or set(base) <= {"_"}:
        return "upload"
    # Leave room for the hash prefix and a long extension.
    return base[:120]


@dataclass
class Upload:
    """A file the user handed to AERA."""

    id: str
    name: str
    path: Path
    size_bytes: int
    kind: str
    sha256: str
    uploaded_at: float = field(default_factory=time.time)

    @property
    def suggested_agent(self) -> str:
        return agent_for(self.name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "path": str(self.path),
            "size_bytes": self.size_bytes,
            "size_mb": round(self.size_bytes / 1_048_576, 3),
            "kind": self.kind,
            "sha256": self.sha256,
            "uploaded_at": self.uploaded_at,
            "suggested_agent": self.suggested_agent,
        }


class UploadStore:
    """Keeps uploaded files on disk and indexes them by id."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._uploads: dict[str, Upload] = {}

    # ------------------------------------------------------------------ #
    # writing
    # ------------------------------------------------------------------ #
    def begin(self, filename: str) -> tuple[Path, str]:
        """Reserve a temporary path for a streaming write."""
        self.root.mkdir(parents=True, exist_ok=True)
        name = safe_name(filename)
        # A monotonic suffix avoids two concurrent uploads of the same name
        # writing over each other before either is content-addressed.
        temp = self.root / f".incoming-{time.time_ns()}-{name}"
        return temp, name

    def commit(self, temp: Path, name: str, digest: str, size: int) -> Upload:
        """Move a completed temp file into place, keyed by its digest."""
        upload_id = digest[:16]
        final = self.root / f"{upload_id}-{name}"

        if final.exists():
            # Same bytes, same name: the earlier copy is authoritative.
            temp.unlink(missing_ok=True)
        else:
            temp.replace(final)

        record = Upload(
            id=upload_id,
            name=name,
            path=final,
            size_bytes=size,
            kind=classify(name),
            sha256=digest,
        )
        self._uploads[upload_id] = record
        logger.info("stored upload %s (%s, %d bytes)", name, record.kind, size)
        return record

    def store_bytes(self, filename: str, data: bytes) -> Upload:
        """Write a small file that is already in memory."""
        if len(data) > MAX_UPLOAD_BYTES:
            raise ValidationError(
                f"{filename} exceeds the {MAX_UPLOAD_BYTES // 1_048_576} MB upload limit"
            )
        temp, name = self.begin(filename)
        temp.write_bytes(data)
        return self.commit(temp, name, hashlib.sha256(data).hexdigest(), len(data))

    def adopt(self, source: Path) -> Upload:
        """Register a file already on disk without copying it.

        The desktop shell has a real path, so a local file does not need to be
        duplicated into the upload folder to be usable.
        """
        source = Path(source).expanduser()
        if not source.is_file():
            raise ValidationError(f"file not found: {source}")

        digest = hashlib.sha256()
        size = 0
        with source.open("rb") as handle:
            while chunk := handle.read(CHUNK):
                digest.update(chunk)
                size += len(chunk)

        upload_id = digest.hexdigest()[:16]
        record = Upload(
            id=upload_id,
            name=source.name,
            path=source,
            size_bytes=size,
            kind=classify(source.name),
            sha256=digest.hexdigest(),
        )
        self._uploads[upload_id] = record
        return record

    # ------------------------------------------------------------------ #
    # reading
    # ------------------------------------------------------------------ #
    def get(self, upload_id: str) -> Upload:
        record = self._uploads.get(upload_id)
        if record is None:
            raise ValidationError(f"no such upload: {upload_id}")
        if not record.path.is_file():
            # Deleted underneath us; do not hand back a dangling path.
            self._uploads.pop(upload_id, None)
            raise ValidationError(f"upload {upload_id} is no longer on disk")
        return record

    def all(self) -> list[Upload]:
        return sorted(self._uploads.values(), key=lambda u: u.uploaded_at, reverse=True)

    def remove(self, upload_id: str) -> None:
        record = self._uploads.pop(upload_id, None)
        if record is None:
            raise ValidationError(f"no such upload: {upload_id}")
        # Only delete files we own; adopted paths belong to the user.
        if record.path.parent == self.root:
            record.path.unlink(missing_ok=True)

    def scan(self) -> list[Upload]:
        """Rebuild the index from disk, so uploads survive a restart."""
        self.root.mkdir(parents=True, exist_ok=True)
        self._uploads.clear()
        for path in sorted(self.root.iterdir()):
            if not path.is_file() or path.name.startswith(".incoming-"):
                continue
            upload_id, _, name = path.name.partition("-")
            if not name:
                continue
            self._uploads[upload_id] = Upload(
                id=upload_id,
                name=name,
                path=path,
                size_bytes=path.stat().st_size,
                kind=classify(name),
                # Recomputing every digest on boot would be slow; the id is
                # the prefix, which is what lookups use.
                sha256=upload_id,
                uploaded_at=path.stat().st_mtime,
            )
        return self.all()

    def stats(self) -> dict[str, Any]:
        uploads = self.all()
        by_kind: dict[str, int] = {}
        for upload in uploads:
            by_kind[upload.kind] = by_kind.get(upload.kind, 0) + 1
        return {
            "count": len(uploads),
            "total_bytes": sum(u.size_bytes for u in uploads),
            "by_kind": by_kind,
            "max_upload_mb": MAX_UPLOAD_BYTES // 1_048_576,
        }
