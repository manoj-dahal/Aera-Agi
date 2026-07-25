"""Tests for the Workspace engine (docs/14-WORKSPACE.md).

Covers: the documented project workflow (open → scan → analyze → memory →
ready), project type detection, dependency discovery, search, safe file
access, AI assistance, and the AI Context Panel.
"""

from pathlib import Path

import pytest

from src.workspace.models import ProjectType
from src.workspace.scanner import ProjectScanner

# ── Fixtures ─────────────────────────────────────────────────


def make_python_project(tmp_path: Path) -> Path:
    root = tmp_path / "myapp"
    (root / "src").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "requirements.txt").write_text("fastapi>=0.111\nhttpx==0.27\n# comment\n")
    (root / "src" / "main.py").write_text("def hello():\n    return 'world'\n")
    (root / "src" / "util.py").write_text("PI = 3.14159\n")
    (root / "docs" / "README.md").write_text("# MyApp\nDocumentation here.\n")
    # ignored dirs must be skipped
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "junk.pyc").write_text("x")
    (root / "node_modules").mkdir()
    (root / "node_modules" / "big.js").write_text("y" * 100)
    return root


def make_node_project(tmp_path: Path) -> Path:
    root = tmp_path / "webapp"
    root.mkdir()
    (root / "package.json").write_text(
        '{"dependencies": {"react": "^18.0.0"}, "devDependencies": {"vite": "^5.0.0"}}'
    )
    (root / "index.ts").write_text("export const x = 1;\n")
    return root


# ── Scanner (documented AI Project Understanding) ────────────


def test_scan_detects_python_project(tmp_path) -> None:
    analysis, entries = ProjectScanner().scan(make_python_project(tmp_path))
    assert analysis.type == ProjectType.PYTHON
    assert analysis.name == "myapp"
    assert analysis.languages.get("python") == 2
    assert analysis.docs_indexed == 2  # README.md + requirements.txt (.md/.txt)
    assert "fastapi" in analysis.dependencies
    assert "httpx" in analysis.dependencies
    # ignore patterns respected
    paths = {e.path for e in entries}
    assert not any("__pycache__" in p or "node_modules" in p for p in paths)


def test_scan_detects_node_project(tmp_path) -> None:
    analysis, _ = ProjectScanner().scan(make_node_project(tmp_path))
    assert analysis.type == ProjectType.NODEJS
    assert "react" in analysis.dependencies
    assert "vite" in analysis.dependencies


def test_scan_rejects_missing_dir(tmp_path) -> None:
    with pytest.raises(NotADirectoryError):
        ProjectScanner().scan(tmp_path / "nope")


# ── Documented workflow via API ──────────────────────────────


def _open(client, tmp_path) -> dict:
    root = make_python_project(tmp_path)
    res = client.post("/api/workspace/open", json={"path": str(root)})
    assert res.status_code == 200
    return res.json()


def test_open_project_links_memory_graph(client, tmp_path) -> None:
    """Docs/14: 'Links project to Memory Graph.'"""
    body = _open(client, tmp_path)
    assert body["type"] == "python"

    recall = client.get("/api/memory/recall", params={"q": "project myapp"}).json()
    assert any("myapp" in n["content"] for n in recall)
    deps = client.get("/api/memory/recall", params={"q": "myapp dependencies"}).json()
    assert any("fastapi" in n["content"] for n in deps)


def test_open_project_publishes_event(client, tmp_path) -> None:
    """Docs/17 plugins + docs/14: 'Project Opened' event."""
    _open(client, tmp_path)
    events = client.get(
        "/api/services/events", params={"pattern": "workspace.project.opened"}
    ).json()
    assert events and events[-1]["data"]["name"] == "myapp"


def test_project_files_and_viewer(client, tmp_path) -> None:
    _open(client, tmp_path)
    files = client.get("/api/workspace/files").json()
    assert any(f["path"] == "src/main.py" for f in files)

    res = client.get("/api/workspace/file", params={"path": "src/main.py"})
    assert "def hello" in res.json()["content"]

    # Secure Project Access: no path escape
    res = client.get("/api/workspace/file", params={"path": "../../etc/passwd"})
    assert res.status_code in (403, 404)


def test_workspace_search(client, tmp_path) -> None:
    _open(client, tmp_path)
    # file name search
    hits = client.get("/api/workspace/search", params={"q": "main"}).json()
    assert any(h["path"] == "src/main.py" for h in hits)
    # content search
    hits = client.get(
        "/api/workspace/search", params={"q": "3.14159", "content": "true"}
    ).json()
    assert any(h["path"] == "src/util.py" and h["line"] == 1 for h in hits)


def test_ai_assist_explain(client, tmp_path) -> None:
    """Documented AI Assistance routed to the Coding Agent."""
    _open(client, tmp_path)
    res = client.post(
        "/api/workspace/assist", json={"action": "explain", "file": "src/main.py"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["agent"] == "coding"
    assert body["response"]


def test_ai_assist_summarize_uses_research_agent(client, tmp_path) -> None:
    _open(client, tmp_path)
    body = client.post("/api/workspace/assist", json={"action": "summarize"}).json()
    assert body["agent"] == "research"


def test_context_panel(client, tmp_path) -> None:
    """Documented AI Context Panel fields."""
    # without a project
    panel = client.get("/api/workspace/context").json()
    assert panel["current_project"] is None
    assert panel["suggestions"] == ["Open a project to begin"]

    _open(client, tmp_path)
    client.post("/api/workspace/assist", json={"action": "summarize"})
    panel = client.get("/api/workspace/context").json()
    assert panel["current_project"] == "myapp"
    assert panel["project_type"] == "python"
    assert "core" in panel["running_agents"]
    assert panel["active_memory"]
    assert panel["recent_tasks"][0].startswith("summarize")


def test_no_project_errors(client) -> None:
    assert client.get("/api/workspace/project").status_code == 404
    assert client.get("/api/workspace/search", params={"q": "x"}).status_code == 404
    assert (
        client.post("/api/workspace/assist", json={"action": "explain"}).status_code == 404
    )
    assert client.post("/api/workspace/open", json={"path": "/nonexistent"}).status_code == 404
