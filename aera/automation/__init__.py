# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Automation subsystem: workflows, triggers and actions."""

from .engine import (
    Action,
    ActionType,
    AutomationEngine,
    RunStatus,
    StepResult,
    Trigger,
    TriggerType,
    Workflow,
    WorkflowRun,
)

__all__ = [
    "Action",
    "ActionType",
    "AutomationEngine",
    "RunStatus",
    "StepResult",
    "Trigger",
    "TriggerType",
    "Workflow",
    "WorkflowRun",
]
