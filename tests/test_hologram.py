"""Tests for the Hologram System (docs/09-HOLOGRAM.md, docs/hologram/).

Verifies: the 6 documented avatar states with their documented animation
sets, the 14 documented emotions, voice↔hologram synchronization through
the event bus, automatic gesture selection, lip-sync viseme generation
with the 9 documented mouth shapes, and eye-state mapping.
"""

import pytest

from src.events.bus import EventBus
from src.hologram.animation import AnimationEngine
from src.hologram.lipsync import text_to_visemes
from src.hologram.models import (
    STATE_ANIMATIONS,
    AvatarState,
    EyeState,
    Gesture,
    HologramEmotion,
    MouthShape,
)

# ── Documented enums ─────────────────────────────────────────


def test_six_documented_avatar_states() -> None:
    assert {s.value for s in AvatarState} == {
        "idle", "listening", "thinking", "speaking", "processing", "offline",
    }


def test_fourteen_documented_emotions() -> None:
    assert len(HologramEmotion) == 14
    assert {"surprised", "laughing", "playful", "empathetic"} <= {
        e.value for e in HologramEmotion
    }


def test_documented_state_animations() -> None:
    """Each state carries its documented animation set."""
    assert "breathing" in STATE_ANIMATIONS[AvatarState.IDLE]
    assert "eye-contact" in STATE_ANIMATIONS[AvatarState.LISTENING]
    assert "soft-glow" in STATE_ANIMATIONS[AvatarState.THINKING]
    assert "lip-sync" in STATE_ANIMATIONS[AvatarState.SPEAKING]
    assert "energy-ring" in STATE_ANIMATIONS[AvatarState.PROCESSING]
    assert "dim-hologram" in STATE_ANIMATIONS[AvatarState.OFFLINE]


# ── State machine + event synchronization ────────────────────


@pytest.mark.asyncio
async def test_conversation_events_drive_avatar_state() -> None:
    """Docs/09: hologram synchronized with the Voice System."""
    bus = EventBus()
    engine = AnimationEngine(bus)
    assert engine.state == AvatarState.IDLE

    await bus.publish("conversation.state", {"state": "thinking"})
    assert engine.state == AvatarState.THINKING
    frame = engine.frame()
    assert frame.eye_state == EyeState.THINKING
    assert frame.glow_intensity == 0.8  # documented soft glow

    await bus.publish("conversation.state", {"state": "responding"})
    assert engine.state == AvatarState.SPEAKING
    await bus.publish("conversation.state", {"state": "waiting"})
    assert engine.state == AvatarState.IDLE


@pytest.mark.asyncio
async def test_emotion_events_update_avatar() -> None:
    """Docs/09: emotion synchronization — voice emotion maps to hologram."""
    bus = EventBus()
    engine = AnimationEngine(bus)
    await bus.publish("voice.emotion.changed", {"emotion": "concerned"})
    assert engine.emotion == HologramEmotion.EMPATHETIC
    await bus.publish("voice.emotion.changed", {"emotion": "excited"})
    assert engine.emotion == HologramEmotion.EXCITED


@pytest.mark.asyncio
async def test_offline_state_when_ai_unavailable() -> None:
    bus = EventBus()
    engine = AnimationEngine(bus)
    await bus.publish("ai.local.status", {"online": False})
    assert engine.state == AvatarState.OFFLINE
    assert engine.frame().glow_intensity == 0.2  # documented dim hologram
    await bus.publish("ai.local.status", {"online": True})
    assert engine.state == AvatarState.IDLE


@pytest.mark.asyncio
async def test_frames_published_to_bus() -> None:
    """The renderer receives hologram.frame events."""
    bus = EventBus()
    engine = AnimationEngine(bus)
    await engine.set_state(AvatarState.LISTENING)
    frames = bus.history("hologram.frame")
    assert frames and frames[-1].data["state"] == "listening"


# ── Gesture selection (docs/hologram/Gesture-System.md) ─────


@pytest.mark.asyncio
async def test_context_gesture_selection() -> None:
    engine = AnimationEngine(EventBus())
    assert engine.select_gesture("Hello there, welcome back!") == Gesture.WAVE
    assert engine.select_gesture("Congratulations, the build completed!") == Gesture.CELEBRATE
    assert engine.select_gesture("No, that cannot work unfortunately") == Gesture.SHAKE_HEAD
    assert engine.select_gesture("First, we install it because it means that...") == Gesture.EXPLAIN


@pytest.mark.asyncio
async def test_emotion_gesture_fallback() -> None:
    """No context cue → emotion-based gesture (documented AI feature)."""
    bus = EventBus()
    engine = AnimationEngine(bus)
    await bus.publish("voice.emotion.changed", {"emotion": "thinking"})
    assert engine.select_gesture("the quarterly numbers") == Gesture.THINKING_POSE


# ── Lip sync (docs/hologram/Lip-Sync.md) ────────────────────


def test_visemes_use_documented_mouth_shapes() -> None:
    visemes = text_to_visemes("aeiou szz mbp hello!")
    shapes = {v.shape for v in visemes}
    assert {MouthShape.A, MouthShape.E, MouthShape.I, MouthShape.O, MouthShape.U} <= shapes
    assert MouthShape.WIDE in shapes  # sibilants
    assert MouthShape.CLOSED in shapes  # bilabials + rest


def test_visemes_merge_repeats_and_end_closed() -> None:
    visemes = text_to_visemes("aaa")
    # consecutive identical shapes merged into one longer viseme
    assert [v.shape for v in visemes] == [MouthShape.A, MouthShape.CLOSED]
    assert visemes[0].duration_ms == 3 * 70


def test_visemes_respect_speaking_speed_and_emotion() -> None:
    slow = text_to_visemes("go", speaking_speed=0.5)
    fast = text_to_visemes("go", speaking_speed=2.0)
    assert slow[0].duration_ms > fast[0].duration_ms
    happy = text_to_visemes("hi", smiling=True)
    assert happy[-1].shape == MouthShape.SMILE  # emotion-aware rest shape


# ── REST API ─────────────────────────────────────────────────


def test_hologram_state_api(client) -> None:
    res = client.get("/api/hologram/state")
    assert res.status_code == 200
    body = res.json()
    # Tests run with LOCAL_LLM_ENABLED=false, so the local-llm-monitor may
    # have already pushed the avatar into its documented Offline state.
    assert body["state"] in ("idle", "offline")

    res = client.post("/api/hologram/state/idle")
    assert res.json()["state"] == "idle"
    assert "breathing" in res.json()["animations"]

    res = client.post("/api/hologram/state/processing")
    assert res.json()["animations"] == STATE_ANIMATIONS[AvatarState.PROCESSING]
    assert client.post("/api/hologram/state/dancing").status_code == 422


def test_hologram_lipsync_api(client) -> None:
    res = client.post("/api/hologram/lipsync", json={"text": "hello aera"})
    assert res.status_code == 200
    body = res.json()
    assert body["total_ms"] > 0
    assert all(v["shape"] in {m.value for m in MouthShape} for v in body["visemes"])


def test_voice_turn_drives_hologram(client) -> None:
    """Full integration: /voice/converse → events → avatar reacts."""
    client.post("/api/voice/converse", json={"transcript": "wow this is amazing!"})
    frame = client.get("/api/hologram/state").json()
    assert frame["emotion"] == "excited"  # synced through the bus
    res = client.get("/api/hologram/gesture", params={"text": "congratulations everyone"})
    assert res.json()["gesture"] == "celebrate"
