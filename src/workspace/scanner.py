"""Project Scanner + Analysis (docs/14-WORKSPACE.md "AI Project Understanding").

"When a project is opened AERA automatically:
 - Detects project type        - Finds dependencies
 - Reads folder structure      - Indexes documentation
 - Identifies programming language
 - Links project to Memory Graph"
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.workspace.models import FileEntry, ProjectAnalysis, ProjectType

#: Default ignore patterns (documented configuration: Ignore Patterns).
IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "target", ".next", "site",
    ".idea", ".vscode", "coverage",
}

#: Marker files → project type (docs/14 "Project Types").
_TYPE_MARKERS: list[tuple[str, ProjectType]] = [
    ("pubspec.yaml", ProjectType.FLUTTER),
    ("Cargo.toml", ProjectType.RUST),
    ("go.mod", ProjectType.GO),
    ("pom.xml", ProjectType.JAVA),
    ("build.gradle", ProjectType.JAVA),
    ("CMakeLists.txt", ProjectType.CPP),
    ("pyproject.toml", ProjectType.PYTHON),
    ("requirements.txt", ProjectType.PYTHON),
    ("setup.py", ProjectType.PYTHON),
    ("package.json", ProjectType.NODEJS),
]

_EXT_LANGUAGE: dict[str, str] = {
    ".py": "python", ".ts": "typescript", ".tsx": "typescript", ".js": "javascript",
    ".jsx": "javascript", ".dart": "dart", ".rs": "rust", ".go": "go",
    ".java": "java", ".kt": "kotlin", ".cs": "csharp", ".cpp": "cpp",
    ".cc": "cpp", ".c": "c", ".h": "c", ".rb": "ruby", ".php": "php",
    ".swift": "swift", ".md": "markdown", ".html": "html", ".css": "css",
    ".yaml": "yaml", ".yml": "yaml", ".json": "json", ".sql": "sql",
    ".sh": "shell",
}

_DOC_EXTENSIONS = {".md", ".rst", ".txt", ".pdf"}
_CREATIVE_EXT = {
    ".blend": ProjectType.BLENDER,
    ".psd": ProjectType.PHOTOSHOP,
    ".prproj": ProjectType.PREMIERE,
    ".drp": ProjectType.DAVINCI,
}

MAX_FILES = 20_000  # documented performance: incremental/lazy indexing


class ProjectScanner:
    """Workspace Scanner → Project Analysis (documented workflow)."""

    def scan(self, root: str | Path) -> tuple[ProjectAnalysis, list[FileEntry]]:
        root = Path(root).resolve()
        if not root.is_dir():
            raise NotADirectoryError(str(root))

        entries: list[FileEntry] = []
        languages: dict[str, int] = {}
        docs_indexed = 0
        dir_count = 0
        total_size = 0
        creative_hits: dict[ProjectType, int] = {}

        for path in self._walk(root):
            rel = path.relative_to(root)
            if path.is_dir():
                dir_count += 1
                entries.append(
                    FileEntry(path=str(rel), name=path.name, extension="",
                              size_bytes=0, is_dir=True)
                )
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            ext = path.suffix.lower()
            total_size += size
            entries.append(
                FileEntry(path=str(rel), name=path.name, extension=ext, size_bytes=size)
            )
            if lang := _EXT_LANGUAGE.get(ext):
                languages[lang] = languages.get(lang, 0) + 1
            if ext in _DOC_EXTENSIONS:
                docs_indexed += 1
            if ctype := _CREATIVE_EXT.get(ext):
                creative_hits[ctype] = creative_hits.get(ctype, 0) + 1
            if len(entries) >= MAX_FILES:
                break

        project_type = self._detect_type(root, languages, creative_hits)
        analysis = ProjectAnalysis(
            name=root.name,
            root=str(root),
            type=project_type,
            languages=dict(sorted(languages.items(), key=lambda kv: -kv[1])),
            dependencies=self._find_dependencies(root, project_type),
            file_count=sum(1 for e in entries if not e.is_dir),
            dir_count=dir_count,
            total_size_bytes=total_size,
            docs_indexed=docs_indexed,
            opened_at=datetime.now(timezone.utc),
        )
        return analysis, entries

    def _walk(self, root: Path):
        stack = [root]
        while stack:
            current = stack.pop()
            try:
                children = sorted(current.iterdir())
            except (PermissionError, OSError):
                continue
            for child in children:
                if child.is_dir():
                    if child.name in IGNORE_DIRS or child.name.startswith("."):
                        continue
                    stack.append(child)
                    yield child
                else:
                    yield child

    def _detect_type(
        self,
        root: Path,
        languages: dict[str, int],
        creative: dict[ProjectType, int],
    ) -> ProjectType:
        """Documented: detect project type from markers, then content."""
        for marker, ptype in _TYPE_MARKERS:
            if (root / marker).exists():
                return ptype
        if creative:
            return max(creative, key=creative.get)  # type: ignore[arg-type]
        if languages:
            top = max(languages, key=languages.get)  # type: ignore[arg-type]
            return {
                "python": ProjectType.PYTHON, "typescript": ProjectType.NODEJS,
                "javascript": ProjectType.NODEJS, "dart": ProjectType.FLUTTER,
                "rust": ProjectType.RUST, "go": ProjectType.GO,
                "java": ProjectType.JAVA, "csharp": ProjectType.CSHARP,
                "cpp": ProjectType.CPP, "markdown": ProjectType.MARKDOWN,
            }.get(top, ProjectType.GENERAL)
        return ProjectType.GENERAL

    def _find_dependencies(self, root: Path, ptype: ProjectType) -> list[str]:
        """Documented: finds dependencies (top-level, capped)."""
        deps: list[str] = []
        try:
            if ptype in (ProjectType.PYTHON,):
                req = root / "requirements.txt"
                if req.exists():
                    for line in req.read_text(errors="ignore").splitlines():
                        line = line.split("#")[0].strip()
                        if line and not line.startswith("-"):
                            deps.append(line.split("==")[0].split(">=")[0].strip())
            if ptype in (ProjectType.NODEJS, ProjectType.FLUTTER) or (root / "package.json").exists():
                pkg = root / "package.json"
                if pkg.exists():
                    import json

                    data = json.loads(pkg.read_text(errors="ignore"))
                    deps.extend(data.get("dependencies", {}).keys())
                    deps.extend(data.get("devDependencies", {}).keys())
            if ptype == ProjectType.RUST:
                cargo = root / "Cargo.toml"
                if cargo.exists():
                    in_deps = False
                    for line in cargo.read_text(errors="ignore").splitlines():
                        if line.strip().startswith("[dependencies"):
                            in_deps = True
                        elif line.strip().startswith("["):
                            in_deps = False
                        elif in_deps and "=" in line:
                            deps.append(line.split("=")[0].strip())
        except (OSError, ValueError):
            pass
        return sorted(set(deps))[:50]
