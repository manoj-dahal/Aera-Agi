"""Tests for the Voice System — Conversation Engine, Emotion Engine, routes.

Verifies the documented behavior of docs/08-VOICE-SYSTEM.md,
docs/voice/Conversation-Engine.md, and docs/voice/Emotion-Engine.md.
"""

import pytest

from src.voice.emotion import Emotion, EmotionEngine

# ── Emotion Engine (docs/voice/Emotion-Engine.md) ────────────


def test_all_ten_documented_emotions_exist() -> None:
    documented = {
        "neutral", "happy", "excited", "curious", "calm",
        "confident", "concerned", "thinking", "friendly", "serious",
    }
    assert {e.value for e in Emotion} == documented


def test_emotion_selection_from_sentiment() -> None:
    engine = EmotionEngine()
    assert engine.analyze("there is an error, everything is broken").emotion == Emotion.CONCERNED
    assert engine.analyze("wow this is amazing, awesome work!").emotion == Emotion.EXCITED
    assert engine.analyze("hello, good morning").emotion == Emotion.FRIENDLY
    assert engine.analyze("the weather report").emotion == Emotion.NEUTRAL


def test_emotion_outputs_are_synchronized() -> None:
    """Docs: outputs are Voice Tone, Facial Expression, Speaking Speed, Pitch, Gestures."""
    state = EmotionEngine().analyze("please analyze and think about this complex plan")
    assert state.emotion == Emotion.THINKING
    assert state.voice_tone
    assert state.facial_expression
    assert state.gesture
    assert 0.5 < state.speaking_speed < 1.5
    assert 0.5 < state.pitch < 1.5


def test_explicit_emotion_override() -> None:
    engine = EmotionEngine()
    assert engine.set(Emotion.SERIOUS).emotion == Emotion.SERIOUS
    assert engine.current.emotion == Emotion.SERIOUS


# ── Conversation Engine (docs/voice/Conversation-Engine.md) ──


def test_voice_status(client) -> None:
    res = client.get("/api/voice/status")
    assert res.status_code == 200
    body = res.json()
    assert body["stt"]["engine"] == "whisper"
    assert body["tts"]["engine"] == "piper"
    assert body["conversation_state"] == "waiting"


def test_converse_returns_full_voice_turn(client) -> None:
    res = client.post("/api/voice/converse", json={"transcript": "hello aera, good morning"})
    assert res.status_code == 200
    body = res.json()
    assert body["text"]
    assert body["agent"] == "core"
    assert body["emotion"]["emotion"] == "friendly"
    assert body["emotion"]["facial_expression"] == "soft-smile"
    assert body["state"] == "responding"  # the turn represents the responding phase
    # ...while the engine itself settles back to waiting
    assert client.get("/api/voice/status").json()["conversation_state"] == "waiting"


def test_converse_persists_to_memory(client) -> None:
    """Docs: every spoken sentence is processed through the Memory Graph."""
    client.post("/api/voice/converse", json={"transcript": "my dog is named Kiran"})
    res = client.get("/api/memory/recall", params={"q": "dog Kiran"})
    assert len(res.json()) >= 1


def test_interrupt_workflow(client) -> None:
    """Docs: Stop Speech → Preserve Context → Listen Immediately."""
    res = client.post("/api/voice/interrupt")
    assert res.status_code == 202
    assert res.json()["state"] == "listening"


def test_set_emotion_endpoint(client) -> None:
    res = client.post("/api/voice/emotion/calm")
    assert res.status_code == 200
    assert res.json()["emotion"] == "calm"
    assert client.post("/api/voice/emotion/angry").status_code == 422  # not documented


@pytest.mark.parametrize("state_event", ["conversation.state", "voice.emotion.changed"])
def test_conversation_publishes_events(client, state_event) -> None:
    """Docs/24: subsystems are event-driven — turns must publish events."""
    client.post("/api/voice/converse", json={"transcript": "hi there"})
    res = client.get("/api/services/events", params={"pattern": state_event})
    assert len(res.json()) >= 1
