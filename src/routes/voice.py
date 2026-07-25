"""Voice routes (docs/08-VOICE-SYSTEM.md, docs/voice/).

Text-first for now: /voice/converse accepts an STT transcript and returns the
full VoiceTurn (response + emotion + avatar cues). Audio upload endpoints
activate automatically once whisper/piper are installed ('.[voice]' extra).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/voice", tags=["voice"])


class ConverseRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=50_000)
    conversation_id: int | None = None


class EmotionOut(BaseModel):
    emotion: str
    voice_tone: str
    facial_expression: str
    speaking_speed: float
    pitch: float
    gesture: str


class VoiceTurnOut(BaseModel):
    text: str
    agent: str
    model: str
    emotion: EmotionOut
    memory_nodes_used: int
    state: str


@router.get("/status")
async def voice_status(request: Request) -> dict[str, object]:
    """STT/TTS engine availability and conversation state."""
    system = request.app.state.system
    return {
        **system.speech.status(),
        "conversation_state": system.conversation.state.value,
        "emotion": system.emotions.current.emotion.value,
    }


@router.post("/converse", response_model=VoiceTurnOut)
async def converse(body: ConverseRequest, request: Request) -> VoiceTurnOut:
    """One conversational turn through the documented voice pipeline."""
    system = request.app.state.system
    turn = await system.conversation.process(body.transcript, body.conversation_id)
    return VoiceTurnOut(
        text=turn.text,
        agent=turn.agent,
        model=turn.model,
        emotion=EmotionOut(**turn.emotion.__dict__ | {"emotion": turn.emotion.emotion.value}),
        memory_nodes_used=turn.memory_nodes_used,
        state=turn.state.value,
    )


@router.post("/interrupt", status_code=202)
async def interrupt(request: Request) -> dict[str, str]:
    """Interrupt workflow: Stop Speech → Preserve Context → Listen Immediately."""
    system = request.app.state.system
    await system.conversation.interrupt()
    return {"state": system.conversation.state.value}


@router.post("/emotion/{emotion}")
async def set_emotion(emotion: str, request: Request) -> EmotionOut:
    """Explicit emotion override (system events)."""
    from src.voice.emotion import Emotion

    system = request.app.state.system
    try:
        state = system.emotions.set(Emotion(emotion))
    except ValueError:
        valid = ", ".join(e.value for e in Emotion)
        raise HTTPException(status_code=422, detail=f"unknown emotion; valid: {valid}") from None
    await system.bus.publish("voice.emotion.changed", {"emotion": state.emotion.value})
    return EmotionOut(**state.__dict__ | {"emotion": state.emotion.value})
