"""Workspace engine — project intelligence (docs/14-WORKSPACE.md)."""

from src.workspace.manager import WorkspaceManager
from src.workspace.models import ProjectAnalysis, ProjectType
from src.workspace.scanner import ProjectScanner

__all__ = ["ProjectAnalysis", "ProjectScanner", "ProjectType", "WorkspaceManager"]
