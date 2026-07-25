"""Agent Manager — routes tasks to specialized agents through shared memory.

Implements the architecture in docs/07-AGENTS.md:

    User → AI Core Manager → [Agents] ↔ Memory Graph ↔ Model Router

Each agent is defined by a name, description, capability keywords, and a
system prompt. The Core Agent handles anything unmatched. Real per-agent
logic (tools, workflows) will grow on top of this routing layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from services.ai.router import ModelRouter
from services.memory.graph import MemoryGraph
from shared.schemas import AgentInfo, AgentStatus, TaskRequest, TaskResponse

_PROMPTS = Path(__file__).resolve().parents[2] / "prompts"


@dataclass
class Agent:
    name: str
    description: str
    capabilities: list[str] = field(default_factory=list)
    priority: str = "normal"
    system_prompt: str = ""

    def matches(self, message: str) -> int:
        text = message.lower()
        return sum(1 for cap in self.capabilities if cap in text)

    def info(self) -> AgentInfo:
        return AgentInfo(
            name=self.name,
            description=self.description,
            capabilities=self.capabilities,
            status=AgentStatus.IDLE,
            priority=self.priority,
        )


def _default_agents() -> list[Agent]:
    core_prompt = ""
    core_file = _PROMPTS / "core-agent.md"
    if core_file.exists():
        core_prompt = core_file.read_text()
    return [
        Agent(
            "core",
            "Central orchestrator — conversation, routing, and general help",
            [],
            "critical",
            core_prompt,
        ),
        Agent(
            "coding",
            "Writes, reviews, debugs, and explains code",
            ["code", "bug", "function", "debug", "refactor", "script", "error"],
            "high",
            "You are AERA's Coding Agent. Write clean, tested, well-explained code.",
        ),
        Agent(
            "research",
            "Finds, summarizes, and synthesizes information",
            ["research", "find", "search", "summarize", "compare", "explain"],
            "normal",
            "You are AERA's Research Agent. Provide accurate, sourced information.",
        ),
        Agent(
            "writing",
            "Drafts and edits documents, emails, and content",
            ["write", "draft", "email", "essay", "blog", "document", "letter"],
            "normal",
            "You are AERA's Writing Agent. Produce clear, well-structured prose.",
        ),
        Agent(
            "planning",
            "Breaks goals into steps, schedules, and task plans",
            ["plan", "schedule", "roadmap", "steps", "organize", "todo"],
            "normal",
            "You are AERA's Planning Agent. Create actionable, prioritized plans.",
        ),
        Agent(
            "memory",
            "Stores, recalls, and organizes long-term memory",
            ["remember", "recall", "forget", "memory", "note"],
            "high",
            "You are AERA's Memory Agent. Manage the user's knowledge carefully.",
        ),
    ]


class AgentManager:
    def __init__(self, memory: MemoryGraph, router: ModelRouter) -> None:
        self.memory = memory
        self.router = router
        self.agents: dict[str, Agent] = {a.name: a for a in _default_agents()}

    def list_agents(self) -> list[AgentInfo]:
        return [a.info() for a in self.agents.values()]

    def route(self, message: str) -> Agent:
        """Pick the best agent by capability keyword score; Core by default."""
        best = self.agents["core"]
        best_score = 0
        for agent in self.agents.values():
            score = agent.matches(message)
            if score > best_score:
                best, best_score = agent, score
        return best

    async def execute(self, task: TaskRequest) -> TaskResponse:
        agent = (
            self.agents.get(task.agent) if task.agent else None
        ) or self.route(task.message)

        # Recall relevant context from the shared Memory Graph
        context_nodes = self.memory.recall(task.message, limit=5)
        context = "\n".join(f"- {n.content}" for n in context_nodes)
        system = agent.system_prompt
        if context:
            system += f"\n\nRelevant memory:\n{context}"

        response, model = await self.router.complete(task.message, system=system)

        # Persist the exchange back into memory
        self.memory.remember_conversation(task.message, response)

        return TaskResponse(
            agent=agent.name,
            response=response,
            model=model,
            memory_nodes_used=len(context_nodes),
        )
