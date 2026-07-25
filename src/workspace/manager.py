"""Workspace Manager (docs/14-WORKSPACE.md).

Documented workflow:

    Open Project → Workspace Scanner → Project Analysis → Context Builder
                 → Memory Graph → Agent Selection → Ready

Memory Integration (documented): the workspace continuously updates the
Memory Graph — project structure, type, dependencies and documentation
are linked as nodes for future recall.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.common.schemas import (
    EdgeRelation,
    MemoryEdgeCreate,
    MemoryNodeCreate,
    NodeType,
    TaskRequest,
)
from src.logging.logger import get_logger
from src.workspace.models import (
    AIAssistRequest,
    ContextPanel,
    FileEntry,
    ProjectAnalysis,
    SearchResult,
)
from src.workspace.scanner import ProjectScanner

if TYPE_CHECKING:
    from src.agents.manager import AgentManager
    from src.events.bus import EventBus
    from src.memory.graph import MemoryGraph

log = get_logger("workspace")

_ASSIST_PROMPTS: dict[str, tuple[str, str]] = {
    # action -> (agent, prompt template)
    "explain": ("coding", "Explain this code:\n{content}"),
    "generate": ("coding", "Generate code for: {detail}\nProject context: {project}"),
    "debug": ("coding", "Debug this code and find the problem:\n{content}"),
    "refactor": ("coding", "Refactor this code and explain improvements:\n{content}"),
    "document": ("writing", "Write documentation for:\n{content}"),
    "find_bugs": ("coding", "Find potential bugs in this code:\n{content}"),
    "summarize": ("research", "Summarize this project: {project}"),
    "dependencies": ("research", "Analyze these dependencies: {detail}"),
}

_MAX_READ = 100_000  # bytes for AI assistance file reads
_TEXT_EXT = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".dart", ".rs", ".go", ".java", ".kt",
    ".cs", ".cpp", ".cc", ".c", ".h", ".rb", ".php", ".swift", ".md", ".rst",
    ".txt", ".html", ".css", ".yaml", ".yml", ".json", ".toml", ".sql", ".sh",
    ".cfg", ".ini", ".env",
}


class WorkspaceManager:
    """Project-centric intelligence hub."""

    def __init__(self, memory: MemoryGraph, agents: AgentManager, bus: EventBus) -> None:
        self.memory = memory
        self.agents = agents
        self.bus = bus
        self.scanner = ProjectScanner()
        self.project: ProjectAnalysis | None = None
        self.files: list[FileEntry] = []
        self._project_node_id: int | None = None
        self._recent_tasks: list[str] = []

    # ── Open Project (documented workflow) ───────────────

    async def open_project(self, root: str | Path) -> ProjectAnalysis:
        # Workspace Scanner → Project Analysis
        analysis, files = self.scanner.scan(root)
        self.project = analysis
        self.files = files

        # Context Builder → Memory Graph (documented linking)
        project_node = self.memory.add_node(
            MemoryNodeCreate(
                type=NodeType.PROJECT,
                content=(
                    f"project '{analysis.name}' ({analysis.type.value}): "
                    f"{analysis.file_count} files, "
                    f"languages: {', '.join(list(analysis.languages)[:5]) or 'none'}"
                ),
                importance=0.8,
            )
        )
        self._project_node_id = project_node.id
        if analysis.dependencies:
            dep_node = self.memory.add_node(
                MemoryNodeCreate(
                    type=NodeType.FACT,
                    content=(
                        f"'{analysis.name}' dependencies: "
                        + ", ".join(analysis.dependencies[:20])
                    ),
                    importance=0.6,
                )
            )
            self.memory.add_edge(
                MemoryEdgeCreate(
                    source_id=dep_node.id,
                    target_id=project_node.id,
                    relation=EdgeRelation.BELONGS_TO,
                )
            )

        # Ready — announce to agents/plugins/hologram (documented event).
        await self.bus.publish(
            "workspace.project.opened",
            {"name": analysis.name, "type": analysis.type.value,
             "files": analysis.file_count},
        )
        log.info("project '%s' opened (%s, %d files)",
                 analysis.name, analysis.type.value, analysis.file_count)
        return analysis

    def close_project(self) -> None:
        self.project = None
        self.files = []
        self._project_node_id = None

    # ── Search (documented: file/folder/content search) ──

    def search(self, query: str, content: bool = False, limit: int = 20) -> list[SearchResult]:
        self._require_project()
        q = query.lower()
        results: list[SearchResult] = []

        # File/folder name search
        for entry in self.files:
            if q in entry.name.lower() or q in entry.path.lower():
                results.append(SearchResult(path=entry.path, score=2.0 if q in entry.name.lower() else 1.0))
                if len(results) >= limit:
                    return sorted(results, key=lambda r: -r.score)

        # Content search (grep-style) in text files
        if content:
            root = Path(self.project.root)  # type: ignore[union-attr]
            for entry in self.files:
                if entry.is_dir or entry.extension not in _TEXT_EXT:
                    continue
                try:
                    text = (root / entry.path).read_text(errors="ignore")
                except OSError:
                    continue
                for lineno, line in enumerate(text.splitlines(), 1):
                    if q in line.lower():
                        results.append(
                            SearchResult(path=entry.path, line=lineno,
                                         snippet=line.strip()[:160], score=1.5)
                        )
                        break  # first hit per file
                if len(results) >= limit:
                    break
        return sorted(results, key=lambda r: -r.score)[:limit]

    # ── File reading (documented File Viewer, safe operations) ──

    def read_file(self, rel_path: str, max_bytes: int = _MAX_READ) -> str:
        self._require_project()
        root = Path(self.project.root).resolve()  # type: ignore[union-attr]
        target = (root / rel_path).resolve()
        # Secure Project Access: never escape the project root.
        if not str(target).startswith(str(root)):
            raise PermissionError("path escapes the project root")
        if not target.is_file():
            raise FileNotFoundError(rel_path)
        return target.read_text(errors="ignore")[:max_bytes]

    # ── AI Assistance (documented features) ─────────────

    async def assist(self, req: AIAssistRequest) -> dict[str, str]:
        self._require_project()
        agent, template = _ASSIST_PROMPTS[req.action]
        content = ""
        if req.file:
            content = self.read_file(req.file, max_bytes=20_000)
        project_desc = (
            f"{self.project.name} ({self.project.type.value}), "  # type: ignore[union-attr]
            f"languages: {', '.join(list(self.project.languages)[:3])}"  # type: ignore[union-attr]
        )
        prompt = template.format(content=content, detail=req.detail, project=project_desc)
        result = await self.agents.execute(TaskRequest(message=prompt, agent=agent))
        self._recent_tasks.append(f"{req.action}: {req.file or req.detail or 'project'}")
        self._recent_tasks = self._recent_tasks[-10:]
        return {"agent": result.agent, "response": result.response, "model": result.model}

    # ── AI Context Panel (documented) ─────────────────────

    def context_panel(self) -> ContextPanel:
        memory_items: list[str] = []
        related: list[str] = []
        if self.project is not None:
            memory_items = [
                n.content for n in self.memory.recall(self.project.name, limit=5)
            ]
            related = [e.path for e in self.files if not e.is_dir][:8]
        return ContextPanel(
            current_project=self.project.name if self.project else None,
            project_type=self.project.type.value if self.project else None,
            active_memory=memory_items,
            running_agents=list(self.agents.agents.keys()),
            suggestions=self._suggestions(),
            related_files=related,
            recent_tasks=list(reversed(self._recent_tasks)),
        )

    def _suggestions(self) -> list[str]:
        if self.project is None:
            return ["Open a project to begin"]
        s = []
        if self.project.docs_indexed == 0:
            s.append("No documentation found — ask me to generate some")
        if not self.project.dependencies:
            s.append("No dependencies detected — is this a new project?")
        if self.project.file_count > 500:
            s.append("Large project — semantic search can help navigation")
        return s or ["Project looks healthy — ask me anything about it"]

    def _require_project(self) -> None:
        if self.project is None:
            raise RuntimeError("no project is open")
