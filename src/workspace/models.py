"""Workspace models (docs/14-WORKSPACE.md).

Documented project types: Development (Flutter, Python, Node.js, Java, C#,
C++, Rust, Go), Creative (Blender, Photoshop, Premiere, DaVinci),
Documentation (Markdown, PDF, Word, HTML), General (media/archives).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ProjectType(str, Enum):
    """Documented project types."""

    # Development
    FLUTTER = "flutter"
    PYTHON = "python"
    NODEJS = "nodejs"
    JAVA = "java"
    CSHARP = "csharp"
    CPP = "cpp"
    RUST = "rust"
    GO = "go"
    # Creative
    BLENDER = "blender"
    PHOTOSHOP = "photoshop"
    PREMIERE = "premiere"
    DAVINCI = "davinci"
    # Documentation
    MARKDOWN = "markdown"
    # General / unknown
    GENERAL = "general"


class FileEntry(BaseModel):
    """One indexed file in the project tree."""

    path: str  # relative to project root
    name: str
    extension: str
    size_bytes: int
    is_dir: bool = False


class ProjectAnalysis(BaseModel):
    """Result of the documented AI Project Understanding step."""

    name: str
    root: str
    type: ProjectType
    languages: dict[str, int]  # language -> file count
    dependencies: list[str]
    file_count: int
    dir_count: int
    total_size_bytes: int
    docs_indexed: int
    opened_at: datetime


class SearchResult(BaseModel):
    path: str
    line: int | None = None
    snippet: str = ""
    score: float = 1.0


class ContextPanel(BaseModel):
    """AI Context Panel data (docs/14): current project, active memory,
    running agents, suggestions, related files, recent tasks."""

    current_project: str | None
    project_type: str | None
    active_memory: list[str]
    running_agents: list[str]
    suggestions: list[str]
    related_files: list[str]
    recent_tasks: list[str]


class AIAssistRequest(BaseModel):
    """Documented AI Assistance features."""

    action: str = Field(
        pattern="^(explain|generate|debug|refactor|document|find_bugs|summarize|dependencies)$"
    )
    file: str | None = None
    detail: str = ""
