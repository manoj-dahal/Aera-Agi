"""Animation Engine (docs/09-HOLOGRAM.md).

Documented architecture:

    AI Core → Emotion Engine → Animation Engine → Face/Body/Gestures
            → Hologram Renderer → Display

Responsibilities per docs/09: motion blending, state transitions, gesture
scheduling, idle animation. This engine is the server-side driver: it
listens to the event bus (conversation states, emotion changes, AI status)
and produces HologramFrame snapshots + hologram.frame events consumed by
the renderer in the dashboard.

Gesture selection (docs/hologram/Gesture-System.md): automatic, based on
conversation context and emotion.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.hologram.lipsync import text_to_visemes
from src.hologram.models import (
    STATE_ANIMATIONS,
    STATE_EYES,
    AvatarState,
    Gesture,
    HologramEmotion,
    HologramFrame,
    Viseme,
)
from src.logging.logger import get_logger

if TYPE_CHECKING:
    from src.events.bus import Event, EventBus

log = get_logger("hologram")

#: Voice Emotion Engine (10 emotions) → hologram emotion (14) mapping.
_VOICE_TO_HOLOGRAM: dict[str, HologramEmotion] = {
    "neutral": HologramEmotion.NEUTRAL,
    "happy": HologramEmotion.HAPPY,
    "excited": HologramEmotion.EXCITED,
    "curious": HologramEmotion.CURIOUS,
    "calm": HologramEmotion.CALM,
    "confident": HologramEmotion.CONFIDENT,
    "concerned": HologramEmotion.EMPATHETIC,
    "thinking": HologramEmotion.THINKING,
    "friendly": HologramEmotion.FRIENDLY,
    "serious": HologramEmotion.SERIOUS,
}

#: Conversation Engine states → avatar states (docs/08 ↔ docs/09 sync).
_CONVERSATION_TO_AVATAR: dict[str, AvatarState] = {
    "listening": AvatarState.LISTENING,
    "understanding": AvatarState.LISTENING,
    "thinking": AvatarState.THINKING,
    "responding": AvatarState.SPEAKING,
    "waiting": AvatarState.IDLE,
    "interrupted": AvatarState.LISTENING,
}

#: Automatic gesture selection: emotion → gesture bias
#: (docs/hologram/Gesture-System.md "Emotion-Based Gestures").
_EMOTION_GESTURES: dict[HologramEmotion, Gesture] = {
    HologramEmotion.HAPPY: Gesture.OPEN_HANDS,
    HologramEmotion.EXCITED: Gesture.CELEBRATE,
    HologramEmotion.FRIENDLY: Gesture.WAVE,
    HologramEmotion.THINKING: Gesture.THINKING_POSE,
    HologramEmotion.CURIOUS: Gesture.HAND_RAISE,
    HologramEmotion.CONFIDENT: Gesture.NOD,
    HologramEmotion.SERIOUS: Gesture.EXPLAIN,
    HologramEmotion.EMPATHETIC: Gesture.NOD,
    HologramEmotion.LAUGHING: Gesture.CLAP,
    HologramEmotion.PLAYFUL: Gesture.WAVE,
}

#: Context keywords → gesture (docs: "Context Awareness").
_CONTEXT_GESTURES: list[tuple[Gesture, tuple[str, ...]]] = [
    (Gesture.WAVE, ("hello", "hi ", "hey", "goodbye", "bye", "welcome")),
    (Gesture.CELEBRATE, ("congratulations", "well done", "success", "completed", "🎉")),
    (Gesture.SHAKE_HEAD, ("no,", "cannot", "can't", "unfortunately", "failed")),
    (Gesture.NOD, ("yes,", "sure", "agreed", "correct", "exactly", "of course")),
    (Gesture.POINT, ("look at", "see the", "notice", "here is", "this is")),
    (Gesture.EXPLAIN, ("because", "therefore", "first,", "step", "means that")),
    (Gesture.THINKING_POSE, ("let me think", "hmm", "considering", "analyzing")),
]


class AnimationEngine:
    """Drives avatar state from system events; produces renderer frames."""

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self.state = AvatarState.IDLE
        self.emotion = HologramEmotion.NEUTRAL
        self.gesture: Gesture | None = None
        self.speaking_speed = 1.0
        # Subscribe to the documented synchronization sources.
        bus.subscribe("conversation.state", self._on_conversation_state)
        bus.subscribe("voice.emotion.changed", self._on_emotion_changed)
        bus.subscribe("voice.speech.stop", self._on_speech_stop)
        bus.subscribe("ai.local.status", self._on_ai_status)
        bus.subscribe("automation.executed", self._on_background_task)

    # ── Event handlers (Voice/Emotion/AI Core synchronization) ──

    async def _on_conversation_state(self, event: Event) -> None:
        state = _CONVERSATION_TO_AVATAR.get(event.data.get("state", ""))
        if state is not None:
            await self.set_state(state)

    async def _on_emotion_changed(self, event: Event) -> None:
        emotion = _VOICE_TO_HOLOGRAM.get(event.data.get("emotion", ""))
        if emotion is not None:
            self.emotion = emotion
            await self._publish_frame()

    async def _on_speech_stop(self, _event: Event) -> None:
        await self.set_state(AvatarState.LISTENING)

    async def _on_ai_status(self, event: Event) -> None:
        # Offline state only while nothing else is happening (docs/09).
        if not event.data.get("online", True) and self.state == AvatarState.IDLE:
            await self.set_state(AvatarState.OFFLINE)
        elif event.data.get("online") and self.state == AvatarState.OFFLINE:
            await self.set_state(AvatarState.IDLE)

    async def _on_background_task(self, _event: Event) -> None:
        # Brief processing pulse when background work completes while idle.
        if self.state == AvatarState.IDLE:
            await self._publish_frame(pulse=True)

    # ── State transitions (docs/09 "Smooth Transitions") ────

    async def set_state(self, state: AvatarState) -> HologramFrame:
        if state != self.state:
            log.debug("avatar %s → %s", self.state.value, state.value)
        self.state = state
        if state == AvatarState.SPEAKING:
            self.gesture = self.select_gesture("")
        elif state in (AvatarState.IDLE, AvatarState.OFFLINE):
            self.gesture = None
        return await self._publish_frame()

    # ── Gesture scheduling ───────────────────────────────

    def select_gesture(self, text: str) -> Gesture | None:
        """Automatic Gesture Selection: context first, then emotion bias."""
        lowered = text.lower()
        for gesture, cues in _CONTEXT_GESTURES:
            if any(cue in lowered for cue in cues):
                return gesture
        return _EMOTION_GESTURES.get(self.emotion)

    # ── Lip sync (docs/hologram/Lip-Sync.md) ─────────────

    def lipsync(self, text: str) -> list[Viseme]:
        smiling = self.emotion in (
            HologramEmotion.HAPPY,
            HologramEmotion.FRIENDLY,
            HologramEmotion.LAUGHING,
            HologramEmotion.PLAYFUL,
        )
        return text_to_visemes(text, self.speaking_speed, smiling)

    # ── Frames ───────────────────────────────────────────

    def frame(self) -> HologramFrame:
        glow = {
            AvatarState.THINKING: 0.8,  # documented soft glow
            AvatarState.PROCESSING: 0.7,
            AvatarState.OFFLINE: 0.2,  # documented dim hologram
        }.get(self.state, 0.5)
        return HologramFrame(
            state=self.state,
            animations=STATE_ANIMATIONS[self.state],
            emotion=self.emotion,
            eye_state=STATE_EYES[self.state],
            gesture=self.gesture,
            glow_intensity=glow,
        )

    async def _publish_frame(self, pulse: bool = False) -> HologramFrame:
        frame = self.frame()
        data = frame.model_dump()
        if pulse:
            data["pulse"] = True
        await self.bus.publish("hologram.frame", data)
        return frame
