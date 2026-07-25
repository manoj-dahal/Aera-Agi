"""Automation Engine — workflows, triggers, and actions (docs/20-AUTOMATION.md)."""

from src.automation.manager import AutomationManager
from src.automation.models import ActionSpec, ActionType, TriggerType, Workflow, WorkflowCreate

__all__ = [
    "ActionSpec",
    "ActionType",
    "AutomationManager",
    "TriggerType",
    "Workflow",
    "WorkflowCreate",
]
