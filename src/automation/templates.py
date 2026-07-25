"""Built-in workflow templates (docs/20-AUTOMATION.md "Workflow Templates").

The doc lists ten built-ins; these are the ones implementable with the
actions available today. The rest (Build Project, Git Release, Media
Organization, ...) activate as their subsystems land.
"""

from __future__ import annotations

from src.automation.models import (
    ActionSpec,
    ActionType,
    ScheduleKind,
    TriggerSpec,
    TriggerType,
    WorkflowCreate,
)

TEMPLATES: dict[str, WorkflowCreate] = {
    "system-health-check": WorkflowCreate(
        name="System Health Check",
        description="Documented template: periodic health snapshot into memory.",
        trigger=TriggerSpec(
            type=TriggerType.SCHEDULE,
            schedule=ScheduleKind.INTERVAL,
            interval_seconds=3600,
        ),
        actions=[
            ActionSpec(
                type=ActionType.MEMORY_UPDATE,
                params={
                    "node_type": "fact",
                    "content": "system health check completed",
                    "importance": 0.2,
                },
            ),
            ActionSpec(
                type=ActionType.NOTIFY,
                params={"message": "System health check completed", "level": "info"},
            ),
        ],
        enabled=False,  # user opts in
    ),
    "ai-research": WorkflowCreate(
        name="AI Research",
        description="Documented template: research a topic and store findings.",
        actions=[
            ActionSpec(
                type=ActionType.AI_GENERATE,
                params={"prompt": "Research this topic: {{topic}}", "agent": "research"},
                save_as="findings",
            ),
            ActionSpec(
                type=ActionType.MEMORY_UPDATE,
                params={
                    "node_type": "fact",
                    "content": "research findings on {{topic}}: {{findings}}",
                    "importance": 0.7,
                },
                condition=None,
            ),
        ],
        variables={"topic": "artificial intelligence"},
    ),
    "generate-documentation": WorkflowCreate(
        name="Generate Documentation",
        description="Documented template: draft docs from memory context.",
        actions=[
            ActionSpec(
                type=ActionType.MEMORY_SEARCH,
                params={"query": "{{subject}}", "limit": 5},
                save_as="context",
            ),
            ActionSpec(
                type=ActionType.AI_GENERATE,
                params={
                    "prompt": "Write documentation about {{subject}}. Context: {{context}}",
                    "agent": "writing",
                },
                save_as="draft",
            ),
        ],
        variables={"subject": "the current project"},
    ),
}
