"""Automation data models (docs/20-AUTOMATION.md).

Documented trigger types (subset wired now: manual, schedule, event, AI
decision — file/app/device triggers arrive with their subsystems), action
types, conditions, retry policies, and workflow variables.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TriggerType(str, Enum):
    """Trigger types from docs/20 (extensible as subsystems land)."""

    MANUAL = "manual"
    SCHEDULE = "schedule"
    EVENT = "event"  # bus topics: file.*, git.commit, app.opened, ...
    VOICE_COMMAND = "voice_command"
    API_REQUEST = "api_request"
    AI_DECISION = "ai_decision"
    SYSTEM_STARTUP = "system_startup"


class ScheduleKind(str, Enum):
    """Documented scheduler options."""

    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    INTERVAL = "interval"  # custom seconds (cron expressions later)


class ActionType(str, Enum):
    """Documented action types (safe subset implemented server-side)."""

    AI_GENERATE = "ai.generate"  # Generate AI Response / Launch Agent
    MEMORY_SEARCH = "memory.search"  # Search Memory
    MEMORY_UPDATE = "memory.update"  # Update Memory
    NOTIFY = "notify"  # Notification
    WAIT = "wait"  # Wait
    CONDITION = "condition"  # Conditional Logic
    EXECUTE_COMMAND = "execute.command"  # Execute Command (sensitive!)
    HTTP_REQUEST = "http.request"  # Send API Request


#: Actions that require explicit user approval (docs/20 Security:
#: "Potentially destructive actions may require explicit user confirmation.")
SENSITIVE_ACTIONS = {ActionType.EXECUTE_COMMAND}


class Condition(BaseModel):
    """Documented conditions: equals, contains, exists, gt, lt, empty."""

    variable: str
    operator: str = "exists"  # equals|contains|exists|empty|gt|lt
    value: Any = None


class ActionSpec(BaseModel):
    type: ActionType
    params: dict[str, Any] = Field(default_factory=dict)
    condition: Condition | None = None  # run only if condition passes
    save_as: str | None = None  # store result in a workflow variable
    retries: int = Field(default=0, ge=0, le=5)  # documented Retry loop


class TriggerSpec(BaseModel):
    type: TriggerType = TriggerType.MANUAL
    # EVENT triggers: bus topic pattern, e.g. "memory.*", "voice.emotion.changed"
    topic: str | None = None
    # SCHEDULE triggers:
    schedule: ScheduleKind | None = None
    interval_seconds: float | None = Field(default=None, gt=0)


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    trigger: TriggerSpec = Field(default_factory=TriggerSpec)
    actions: list[ActionSpec] = Field(min_length=1)
    variables: dict[str, Any] = Field(default_factory=dict)  # User Variables
    approved: bool = False  # user approval for sensitive actions
    enabled: bool = True


class Workflow(WorkflowCreate):
    id: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    runs: int = 0
    failures: int = 0
    last_run: datetime | None = None
    avg_duration_ms: float = 0.0  # Learning Engine: execution time tracking


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"  # sensitive action without approval


class ActionResult(BaseModel):
    action: ActionType
    status: ExecutionStatus
    output: Any = None
    error: str | None = None
    attempts: int = 1


class ExecutionResult(BaseModel):
    workflow_id: int
    workflow_name: str
    status: ExecutionStatus
    trigger: TriggerType
    results: list[ActionResult]
    variables: dict[str, Any]
    duration_ms: float
    started_at: datetime
