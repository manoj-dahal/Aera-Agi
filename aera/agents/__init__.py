# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""AERA agent system.

``build_default_registry`` wires up every agent enabled in ``config/agents.yaml``.
"""

from __future__ import annotations

from ..core.config import AgentsSection
from .base import Agent, AgentContext, AgentStatus, Capability, Task, TaskResult
from .coding_agent import CodeReviewAgent, CodingAgent, DebugAgent
from .core_agent import CoreAgent
from .extended_agents import (
    AutomationAgent,
    BackupAgent,
    DeviceAgent,
    EthicalHackingAgent,
    LearningAgent,
    MonitoringAgent,
    SchedulerAgent,
    UpdateAgent,
)
from .knowledge_agents import (
    PlanningAgent,
    ReasoningAgent,
    ResearchAgent,
    TranslationAgent,
    WritingAgent,
)
from .media_agents import (
    AudioAgent,
    CollaborationAgent,
    ConversationAgent,
    DocumentAgent,
    NetworkAgent,
    OCRAgent,
    PersonalizationAgent,
    VisionAgent,
    VoiceAgent,
    WebAgent,
)
from .registry import AgentRegistry
from .system_agents import (
    GitAgent,
    MemoryAgent,
    NotificationAgent,
    PerformanceAgent,
    SecurityAgent,
    TerminalAgent,
    WorkspaceAgent,
)

#: config flag -> agent classes it enables
AGENT_CLASSES: dict[str, tuple[type[Agent], ...]] = {
    "core": (CoreAgent,),
    "memory": (MemoryAgent,),
    "coding": (CodingAgent, CodeReviewAgent, DebugAgent),
    "reasoning": (ReasoningAgent,),
    "planning": (PlanningAgent,),
    "research": (ResearchAgent,),
    "writing": (WritingAgent,),
    "translation": (TranslationAgent,),
    "workspace": (WorkspaceAgent,),
    "git": (GitAgent,),
    "terminal": (TerminalAgent,),
    "security": (SecurityAgent,),
    "performance": (PerformanceAgent,),
    "notification": (NotificationAgent,),
    "automation": (AutomationAgent, SchedulerAgent),
    "ethical_hacking": (EthicalHackingAgent,),
    "device": (DeviceAgent,),
    "learning": (LearningAgent,),
    "update": (UpdateAgent, BackupAgent),
    "monitoring": (MonitoringAgent,),
    "document": (DocumentAgent,),
    "vision": (VisionAgent, OCRAgent),
    "audio": (AudioAgent,),
    "network": (NetworkAgent,),
    "web": (WebAgent,),
    "conversation": (ConversationAgent,),
    "personalization": (PersonalizationAgent,),
    "collaboration": (CollaborationAgent,),
    "voice": (VoiceAgent,),
}


def build_default_registry(
    context: AgentContext, config: AgentsSection | None = None
) -> AgentRegistry:
    """Create a registry populated with every enabled agent."""
    cfg = config or AgentsSection()
    registry = AgentRegistry(context, max_concurrency=cfg.max_concurrent_tasks)

    enabled = cfg.enabled_agents()
    for flag, classes in AGENT_CLASSES.items():
        if flag in enabled:
            for cls in classes:
                registry.register_class(cls)

    # The Core Agent is mandatory - it is the entry point for every request.
    if "core" not in registry:
        registry.register_class(CoreAgent)
    return registry


__all__ = [
    "AGENT_CLASSES",
    "Agent",
    "AgentContext",
    "AgentRegistry",
    "AgentStatus",
    "Capability",
    "AudioAgent",
    "AutomationAgent",
    "CollaborationAgent",
    "ConversationAgent",
    "DocumentAgent",
    "NetworkAgent",
    "OCRAgent",
    "PersonalizationAgent",
    "VisionAgent",
    "VoiceAgent",
    "WebAgent",
    "BackupAgent",
    "CodeReviewAgent",
    "DeviceAgent",
    "EthicalHackingAgent",
    "LearningAgent",
    "MonitoringAgent",
    "SchedulerAgent",
    "UpdateAgent",
    "CodingAgent",
    "CoreAgent",
    "DebugAgent",
    "GitAgent",
    "MemoryAgent",
    "NotificationAgent",
    "PerformanceAgent",
    "PlanningAgent",
    "ReasoningAgent",
    "ResearchAgent",
    "SecurityAgent",
    "Task",
    "TaskResult",
    "TerminalAgent",
    "TranslationAgent",
    "WorkspaceAgent",
    "WritingAgent",
    "build_default_registry",
]
