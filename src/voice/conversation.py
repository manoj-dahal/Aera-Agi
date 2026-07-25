"""Conversation Engine (docs/voice/Conversation-Engine.md).

Documented architecture:

    User → Speech-To-Text → Intent Detection → Memory Recall
         → Reasoning → Response Generation → Text-To-Speech

Documented conversation states:
    Listening, Understanding, Thinking, Responding, Waiting, Interrupted

The engine coordinates the Agent Manager (reasoning/response), Memory Graph
(recall + persistence), and Emotion Engine (voice/avatar tone), and supports
the interrupt workflow from docs/08-VOICE-SYSTEM.md:
    Stop Speech → Preserve Context → Listen Immediately → Continue.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.agents.manager import AgentManager
from src.common.schemas import TaskRequest
from src.events.bus import EventBus
from src.logging.logger import get_logger
from src.voice.emotion import EmotionEngine, EmotionState

log = get_logger("voice")


class ConversationState(str, Enum):
    """The six documented conversation states."""

    LISTENING = "listening"
    UNDERSTANDING = "understanding"
    THINKING = "thinking"
    RESPONDING = "responding"
    WAITING = "waiting"
    INTERRUPTED = "interrupted"


@dataclass
class VoiceTurn:
    """Result of one conversational turn — consumed by TTS and the hologram."""

    text: str
    agent: str
    model: str
    emotion: EmotionState
    memory_nodes_used: int
    state: ConversationState


class ConversationEngine:
    """Manages natural, continuous, multi-turn conversations."""

    def __init__(
        self,
        agents: AgentManager,
        emotions: EmotionEngine,
        bus: EventBus,
    ) -> None:
        self.agents = agents
        self.emotions = emotions
        self.bus = bus
        self.state = ConversationState.WAITING

    async def _set_state(self, state: ConversationState) -> None:
        self.state = state
        # The hologram and dashboard react to these events (docs/09-HOLOGRAM.md).
        await self.bus.publish("conversation.state", {"state": state.value})

    async def process(self, transcript: str, conversation_id: int | None = None) -> VoiceTurn:
        """Run one turn of the documented pipeline (input is already STT text)."""
        # Understanding: intent detection is delegated to Agent Manager routing.
        await self._set_state(ConversationState.UNDERSTANDING)

        # Thinking: memory recall + reasoning + response generation.
        await self._set_state(ConversationState.THINKING)
        result = await self.agents.execute(
            TaskRequest(message=transcript, conversation_id=conversation_id)
        )

        # Emotion Engine: sentiment → emotion → voice style → avatar expression.
        emotion = self.emotions.analyze(transcript, result.response)
        await self.bus.publish(
            "voice.emotion.changed",
            {"emotion": emotion.emotion.value, "expression": emotion.facial_expression},
        )

        # Responding — TTS/hologram consume the returned VoiceTurn.
        await self._set_state(ConversationState.RESPONDING)
        turn = VoiceTurn(
            text=result.response,
            agent=result.agent,
            model=result.model,
            emotion=emotion,
            memory_nodes_used=result.memory_nodes_used,
            state=self.state,
        )
        await self._set_state(ConversationState.WAITING)
        return turn

    async def interrupt(self) -> None:
        """Interrupt workflow: Stop Speech → Preserve Context → Listen Immediately."""
        await self._set_state(ConversationState.INTERRUPTED)
        await self.bus.publish("voice.speech.stop", {})
        # Context is preserved automatically — memory is already persisted.
        await self._set_state(ConversationState.LISTENING)
