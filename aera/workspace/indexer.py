# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Workspace scanner and project indexer (``docs/14-WORKSPACE.md``).

Walks a project folder, classifies files, extracts lightweight code symbols and
feeds a searchable index plus Memory Graph nodes. All paths are sandboxed to
the opened project root.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from ..core.config import WorkspaceSection
from ..core.errors import NotFoundError, SandboxViolation, ValidationError
from ..core.logging import get_logger
from ..memory.embeddings import tokenize

logger = get_logger("workspace.indexer")

EXTENSION_LANGUAGES = {
    ".py": "python", ".dart": "dart", ".js": "javascript", ".mjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".jsx": "javascript",
    ".go": "go", ".rs": "rust", ".java": "java", ".kt": "kotlin",
    ".swift": "swift", ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp",
    ".cs": "csharp", ".php": "php", ".rb": "ruby", ".sh": "bash",
    ".sql": "sql", ".md": "markdown", ".yaml": "yaml", ".yml": "yaml",
    ".json": "json", ".toml": "toml", ".txt": "text", ".html": "html",
    ".css": "css", ".scss": "css",
}

# Marker file -> project kind, used for auto-detection.
PROJECT_MARKERS = {
    "pyproject.toml": "python", "requirements.txt": "python", "setup.py": "python",
    "package.json": "node", "pubspec.yaml": "flutter", "Cargo.toml": "rust",
    "go.mod": "go", "pom.xml": "java", "build.gradle": "java",
    "Gemfile": "ruby", "composer.json": "php", "CMakeLists.txt": "cpp",
    "Dockerfile": "docker", "docker-compose.yml": "docker",
}

_SYMBOL_PATTERNS = {
    "python": [
        (re.compile(r"^\s*class\s+(\w+)", re.M), "class"),
        (re.compile(r"^\s*(?:async\s+)?def\s+(\w+)", re.M), "function"),
    ],
    "javascript": [
        (re.compile(r"^\s*class\s+(\w+)", re.M), "class"),
        (re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.M), "function"),
        (re.compile(r"^\s*(?:const|let)\s+(\w+)\s*=\s*(?:async\s*)?\(", re.M), "function"),
    ],
    "go": [
        (re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?(\w+)", re.M), "function"),
        (re.compile(r"^\s*type\s+(\w+)\s+struct", re.M), "struct"),
    ],
    "rust": [
        (re.compile(r"^\s*(?:pub\s+)?fn\s+(\w+)", re.M), "function"),
        (re.compile(r"^\s*(?:pub\s+)?struct\s+(\w+)", re.M), "struct"),
    ],
    "dart": [
        (re.compile(r"^\s*class\s+(\w+)", re.M), "class"),
        (re.compile(r"^\s*(?:Future<[^>]*>|void|\w+)\s+(\w+)\s*\(", re.M), "function"),
    ],
}
_SYMBOL_PATTERNS["typescript"] = _SYMBOL_PATTERNS["javascript"]
_SYMBOL_PATTERNS["java"] = _SYMBOL_PATTERNS["dart"]


class IndexedFile:
    """A single indexed source file."""

    __slots__ = ("path", "relative", "language", "size", "lines", "symbols", "tokens", "modified")

    def __init__(self, path: Path, root: Path, language: str, size: int, lines: int,
                 symbols: list[dict], tokens: set[str], modified: float) -> None:
        self.path = path
        self.relative = str(path.relative_to(root))
        self.language = language
        self.size = size
        self.lines = lines
        self.symbols = symbols
        self.tokens = tokens
        self.modified = modified

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.relative,
            "language": self.language,
            "size": self.size,
            "lines": self.lines,
            "symbols": self.symbols[:40],
            "modified": self.modified,
        }


class Project:
    """An opened workspace project."""

    def __init__(self, root: Path, name: str | None = None) -> None:
        self.root = root
        self.name = name or root.name
        self.id = f"proj_{abs(hash(str(root))) % (10**10):010d}"
        self.kinds: list[str] = []
        self.files: dict[str, IndexedFile] = {}
        self.indexed_at: float | None = None
        self.skipped = 0

    @property
    def languages(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.files.values():
            counts[f.language] = counts.get(f.language, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "root": str(self.root),
            "kinds": self.kinds,
            "files": len(self.files),
            "skipped": self.skipped,
            "languages": self.languages,
            "total_lines": sum(f.lines for f in self.files.values()),
            "indexed_at": self.indexed_at,
        }


class WorkspaceIndexer:
    """Opens projects, indexes them and answers structural queries."""

    def __init__(self, config: WorkspaceSection | None = None, *, memory=None, bus=None) -> None:
        self.config = config or WorkspaceSection()
        self.memory = memory
        self.bus = bus
        self.projects: dict[str, Project] = {}
        self.active_project: Project | None = None

    # ------------------------------------------------------------------ #
    # opening & indexing
    # ------------------------------------------------------------------ #
    def open(self, path: str | Path, *, index: bool | None = None) -> Project:
        """Open a folder as the active project."""
        root = Path(path).expanduser().resolve()
        if not root.exists():
            raise NotFoundError(f"workspace path does not exist: {root}")
        if not root.is_dir():
            raise ValidationError(f"workspace path is not a directory: {root}")

        project = self.projects.get(str(root)) or Project(root)
        project.kinds = self._detect_kinds(root)
        self.projects[str(root)] = project
        self.active_project = project

        if index if index is not None else self.config.auto_index:
            self.index(project)
        logger.info("workspace opened: %s (%s)", root, ", ".join(project.kinds) or "generic")
        return project

    def _detect_kinds(self, root: Path) -> list[str]:
        found: list[str] = []
        for marker, kind in PROJECT_MARKERS.items():
            if (root / marker).exists() and kind not in found:
                found.append(kind)
        if (root / ".git").exists():
            found.append("git")
        return found

    def index(self, project: Project | None = None) -> dict[str, Any]:
        """Walk the project tree and (re)build the index."""
        project = project or self.active_project
        if project is None:
            raise ValidationError("no active project to index")

        started = time.perf_counter()
        project.files.clear()
        project.skipped = 0

        allowed = set(self.config.index_extensions)
        ignored = set(self.config.ignore_dirs)

        for path in self._walk(project.root, ignored):
            if path.suffix.lower() not in allowed:
                continue
            try:
                stat = path.stat()
                if stat.st_size > self.config.max_file_size_bytes:
                    project.skipped += 1
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, UnicodeDecodeError):
                project.skipped += 1
                continue

            language = EXTENSION_LANGUAGES.get(path.suffix.lower(), "text")
            entry = IndexedFile(
                path=path,
                root=project.root,
                language=language,
                size=stat.st_size,
                lines=text.count("\n") + 1,
                symbols=self._symbols(text, language),
                tokens=set(tokenize(f"{path.name} {path.stem}")) | set(tokenize(text[:4000])),
                modified=stat.st_mtime,
            )
            project.files[entry.relative] = entry

        project.indexed_at = time.time()
        elapsed = (time.perf_counter() - started) * 1000
        logger.info(
            "indexed %s: %d files in %.0fms", project.name, len(project.files), elapsed
        )
        return {**project.to_dict(), "duration_ms": round(elapsed, 2)}

    def _walk(self, root: Path, ignored: set[str]):
        """Depth-first walk that prunes ignored directories."""
        stack = [root]
        while stack:
            current = stack.pop()
            try:
                entries = list(current.iterdir())
            except (OSError, PermissionError):
                continue
            for entry in entries:
                if entry.name.startswith(".") and entry.name not in (".github",):
                    if entry.is_dir():
                        continue
                if entry.is_dir():
                    if entry.name not in ignored:
                        stack.append(entry)
                elif entry.is_file():
                    yield entry

    def _symbols(self, text: str, language: str) -> list[dict]:
        out: list[dict] = []
        for pattern, kind in _SYMBOL_PATTERNS.get(language, []):
            for match in pattern.finditer(text):
                out.append(
                    {
                        "name": match.group(1),
                        "kind": kind,
                        "line": text.count("\n", 0, match.start()) + 1,
                    }
                )
        return out[:200]

    # ------------------------------------------------------------------ #
    # querying
    # ------------------------------------------------------------------ #
    def search(self, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """Rank indexed files against a free-text query."""
        project = self.active_project
        if project is None or not query.strip():
            return []

        terms = set(tokenize(query))
        if not terms:
            return []

        scored: list[tuple[float, IndexedFile]] = []
        for entry in project.files.values():
            score = 0.0
            name_tokens = set(tokenize(entry.relative))
            score += 3.0 * len(terms & name_tokens)
            score += 1.0 * len(terms & entry.tokens)
            for symbol in entry.symbols:
                if symbol["name"].lower() in terms:
                    score += 2.0
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda pair: (-pair[0], pair[1].relative))
        return [{**e.to_dict(), "score": round(s, 2)} for s, e in scored[:limit]]

    def read_file(self, relative: str, *, max_bytes: int = 200_000) -> dict[str, Any]:
        """Read a file from the active project, refusing to escape the root."""
        project = self.active_project
        if project is None:
            raise ValidationError("no active project")

        target = (project.root / relative).resolve()
        if not str(target).startswith(str(project.root)):
            raise SandboxViolation(f"path escapes the project root: {relative}")
        if not target.is_file():
            raise NotFoundError(f"file not found in workspace: {relative}")

        data = target.read_bytes()[:max_bytes]
        return {
            "path": relative,
            "language": EXTENSION_LANGUAGES.get(target.suffix.lower(), "text"),
            "size": target.stat().st_size,
            "truncated": target.stat().st_size > max_bytes,
            "content": data.decode("utf-8", "replace"),
        }

    def tree(self, *, max_entries: int = 500) -> list[str]:
        project = self.active_project
        if project is None:
            return []
        return sorted(project.files)[:max_entries]

    def summary(self) -> dict[str, Any]:
        if self.active_project is None:
            return {}
        data = self.active_project.to_dict()
        symbols = sum(len(f.symbols) for f in self.active_project.files.values())
        data["symbols"] = symbols
        return data

    async def sync_to_memory(self) -> int:
        """Record the project and its top files in the Memory Graph."""
        project = self.active_project
        if project is None or self.memory is None:
            return 0

        node = await self.memory.store(
            title=f"Project: {project.name}",
            content=(
                f"Project {project.name} at {project.root}. "
                f"Kinds: {', '.join(project.kinds) or 'generic'}. "
                f"{len(project.files)} files. Languages: {', '.join(project.languages)}."
            ),
            node_type="project",
            memory_type="long_term",
            tags=["project", "workspace", *project.kinds],
            importance=0.8,
            creator="workspace",
            project_id=project.id,
            metadata=project.to_dict(),
        )

        stored = 1
        biggest = sorted(project.files.values(), key=lambda f: -len(f.symbols))[:20]
        for entry in biggest:
            if not entry.symbols:
                continue
            file_node = await self.memory.store(
                title=entry.relative,
                content=(
                    f"{entry.language} file with {entry.lines} lines. Symbols: "
                    + ", ".join(s["name"] for s in entry.symbols[:15])
                ),
                node_type="file",
                memory_type="semantic",
                tags=["file", entry.language],
                importance=0.4,
                creator="workspace",
                project_id=project.id,
            )
            self.memory.graph.connect(node.id, file_node.id, "parent")
            stored += 1
        return stored
