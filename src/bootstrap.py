"""Bootstrap — initialize every AERA subsystem in dependency order.

    Memory Graph ──► Model Router ──► Agent Manager
         │                                  │
         └────────── shared context ────────┘

See docs/02-SYSTEM-ARCHITECTURE.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.agents.manager import AgentManager
from src.ai.router import ModelRouter
from src.logging.logger import get_logger
from src.memory.graph import MemoryGraph

log = get_logger("bootstrap")


@dataclass
class AeraSystem:
    """Handle to all running AERA subsystems."""

    memory: MemoryGraph
    router: ModelRouter
    agents: AgentManager

    def shutdown(self) -> None:
        log.info("shutting down AERA subsystems")
        self.memory.close()


def boot() -> AeraSystem:
    """Initialize and wire together the core subsystems."""
    log.info("booting AERA core")
    memory = MemoryGraph()
    router = ModelRouter()
    agents = AgentManager(memory, router)
    log.info("AERA online — %d agents registered", len(agents.agents))
    return AeraSystem(memory=memory, router=router, agents=agents)
