"""Tests for the Automation Engine (docs/20-AUTOMATION.md).

Covers the documented lifecycle, trigger types, conditions, variables,
retries, sensitive-action approval, memory updates, and templates.
"""

import pytest

from src.automation.actions import check_condition
from src.automation.models import Condition

# ── Conditions (docs/20: If, Exists, Empty, Equals, Contains, Gt, Lt) ──


@pytest.mark.parametrize(
    ("cond", "variables", "expected"),
    [
        (None, {}, True),
        (Condition(variable="x", operator="exists"), {"x": 1}, True),
        (Condition(variable="x", operator="exists"), {}, False),
        (Condition(variable="x", operator="empty"), {"x": ""}, True),
        (Condition(variable="x", operator="equals", value=5), {"x": 5}, True),
        (Condition(variable="x", operator="contains", value="err"), {"x": "an error"}, True),
        (Condition(variable="x", operator="gt", value=3), {"x": 10}, True),
        (Condition(variable="x", operator="lt", value=3), {"x": 10}, False),
    ],
)
def test_conditions(cond, variables, expected) -> None:
    assert check_condition(cond, variables) is expected


# ── Workflow lifecycle via API ───────────────────────────────


def _make(client, **overrides) -> int:
    spec = {
        "name": "test workflow",
        "actions": [
            {
                "type": "memory.update",
                "params": {"node_type": "fact", "content": "workflow says {{greeting}}"},
            }
        ],
        "variables": {"greeting": "hello"},
        **overrides,
    }
    res = client.post("/api/automation/workflows", json=spec)
    assert res.status_code == 201
    return res.json()["id"]


def test_create_run_and_learn(client) -> None:
    wf_id = _make(client)
    res = client.post(f"/api/automation/workflows/{wf_id}/run")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert body["trigger"] == "api_request"
    assert body["results"][0]["status"] == "success"

    # Learning Engine: runs and duration tracked
    wf = client.get(f"/api/automation/workflows/{wf_id}").json()
    assert wf["runs"] == 1
    assert wf["avg_duration_ms"] >= 0

    # Variables rendered into memory content
    recall = client.get("/api/memory/recall", params={"q": "workflow says hello"}).json()
    assert len(recall) >= 1


def test_execution_updates_memory_graph(client) -> None:
    """Docs/20: every workflow execution updates the Memory Graph."""
    wf_id = _make(client, name="memory-audit-wf")
    client.post(f"/api/automation/workflows/{wf_id}/run")
    recall = client.get("/api/memory/recall", params={"q": "memory-audit-wf"}).json()
    assert any("success" in n["content"] for n in recall)


def test_sensitive_action_blocked_without_approval(client) -> None:
    """Docs/20 Security: destructive actions require explicit confirmation."""
    wf_id = _make(
        client,
        name="dangerous",
        actions=[{"type": "execute.command", "params": {"command": "echo hi"}}],
        approved=False,
    )
    body = client.post(f"/api/automation/workflows/{wf_id}/run").json()
    assert body["status"] == "blocked"
    assert body["results"][0]["status"] == "blocked"


def test_sensitive_action_runs_when_approved(client) -> None:
    wf_id = _make(
        client,
        name="approved-cmd",
        actions=[
            {
                "type": "execute.command",
                "params": {"command": "echo approved-output"},
                "save_as": "out",
            }
        ],
        approved=True,
    )
    body = client.post(f"/api/automation/workflows/{wf_id}/run").json()
    assert body["status"] == "success"
    assert "approved-output" in body["results"][0]["output"]


def test_condition_skips_action(client) -> None:
    wf_id = _make(
        client,
        name="conditional",
        actions=[
            {
                "type": "notify",
                "params": {"message": "never"},
                "condition": {"variable": "missing", "operator": "exists"},
            }
        ],
    )
    body = client.post(f"/api/automation/workflows/{wf_id}/run").json()
    assert body["results"][0]["status"] == "skipped"
    assert body["status"] == "success"  # skipped != failed


def test_event_trigger_fires_workflow(client) -> None:
    """Docs/20 trigger types: event-driven workflows via the bus."""
    _make(
        client,
        name="on-emotion",
        trigger={"type": "event", "topic": "voice.emotion.changed"},
        actions=[
            {
                "type": "memory.update",
                "params": {"node_type": "fact", "content": "emotion event workflow fired"},
            }
        ],
    )
    # Publish the event through the voice system
    client.post("/api/voice/emotion/happy")
    recall = client.get("/api/memory/recall", params={"q": "emotion event workflow fired"}).json()
    assert len(recall) >= 1


def test_ai_action_and_variable_chaining(client) -> None:
    """AI Generate → save_as → next action uses {{result}} (Workflow Variables)."""
    wf_id = _make(
        client,
        name="chain",
        actions=[
            {"type": "ai.generate", "params": {"prompt": "say hi", "agent": "core"}, "save_as": "reply"},
            {
                "type": "memory.update",
                "params": {"node_type": "fact", "content": "chained: {{reply}}"},
            },
        ],
    )
    body = client.post(f"/api/automation/workflows/{wf_id}/run").json()
    assert body["status"] == "success"
    assert body["variables"]["reply"]


def test_templates_and_install(client) -> None:
    """Docs/20 built-in templates exist and are installable."""
    templates = client.get("/api/automation/templates").json()
    assert {"system-health-check", "ai-research", "generate-documentation"} <= set(templates)

    res = client.post("/api/automation/templates/ai-research/install")
    assert res.status_code == 201
    wf_id = res.json()["id"]
    body = client.post(
        f"/api/automation/workflows/{wf_id}/run", json={"topic": "memory graphs"}
    ).json()
    assert body["status"] == "success"
    assert body["variables"]["topic"] == "memory graphs"


def test_history_and_delete(client) -> None:
    wf_id = _make(client, name="short-lived")
    client.post(f"/api/automation/workflows/{wf_id}/run")
    history = client.get("/api/automation/history").json()
    assert any(h["workflow_name"] == "short-lived" for h in history)

    assert client.delete(f"/api/automation/workflows/{wf_id}").status_code == 204
    assert client.get(f"/api/automation/workflows/{wf_id}").status_code == 404
