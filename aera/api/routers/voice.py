"""Voice and hologram endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_hologram, get_kernel_dep, get_voice
from ..schemas import AvatarEmotionRequest, AvatarGestureRequest, ListenRequest, SpeakRequest, ok

voice_router = APIRouter(prefix="/voice", tags=["voice"])
avatar_router = APIRouter(prefix="/avatar", tags=["hologram"])


@voice_router.get("/status")
async def voice_status(voice=Depends(get_voice)):
    return ok(voice.status())


@voice_router.post("/speak")
async def speak(payload: SpeakRequest, voice=Depends(get_voice)):
    """Synthesise speech with emotion analysis and avatar synchronisation."""
    result = await voice.speak(payload.text, emotion=payload.emotion, speed=payload.speed)
    return ok(result.model_dump(), "Speech generated")


@voice_router.post("/tap")
async def tap_to_memory(conversation_id: str | None = None, kernel=Depends(get_kernel_dep)):
    """Tap-to-memory: recall context, then report readiness for listening."""
    result = await kernel.prime_context(conversation_id=conversation_id)
    return ok(result, result.get("summary", "Context primed"))


@voice_router.post("/listen")
async def listen(payload: ListenRequest, voice=Depends(get_voice)):
    """Transcribe input. Headless deployments pass pre-transcribed text."""
    session = await voice.start_listening()
    transcript = await voice.listen(payload.text.encode("utf-8"), language=payload.language)
    return ok(
        {
            **transcript.model_dump(),
            "session": session,
            "wake_word_detected": voice.detect_wake_word(transcript.text),
        }
    )


@voice_router.post("/stop")
async def stop_listening(voice=Depends(get_voice)):
    await voice.stop_listening()
    return ok(voice.status(), "Voice session stopped")


@voice_router.post("/emotion")
async def analyse_emotion(payload: SpeakRequest):
    from ...voice.engine import detect_emotion

    emotion, confidence = detect_emotion(payload.text)
    return ok({"emotion": emotion.value, "confidence": round(confidence, 2)})


# --------------------------------------------------------------------------- #
# hologram
# --------------------------------------------------------------------------- #
@avatar_router.get("/status")
async def avatar_status(hologram=Depends(get_hologram)):
    return ok(hologram.status())


@avatar_router.post("/show")
async def avatar_show(hologram=Depends(get_hologram)):
    return ok((await hologram.show()).to_public(), "Avatar shown")


@avatar_router.post("/hide")
async def avatar_hide(hologram=Depends(get_hologram)):
    return ok((await hologram.hide()).to_public(), "Avatar hidden")


@avatar_router.post("/emotion")
async def avatar_emotion(payload: AvatarEmotionRequest, hologram=Depends(get_hologram)):
    state = await hologram.set_emotion(payload.emotion, intensity=payload.intensity)
    return ok(state.to_public(), "Emotion applied")


@avatar_router.post("/gesture")
async def avatar_gesture(payload: AvatarGestureRequest, hologram=Depends(get_hologram)):
    state = await hologram.play_gesture(payload.gesture)
    return ok(state.to_public(), "Gesture played")


@avatar_router.post("/animation")
async def avatar_animation(hologram=Depends(get_hologram)):
    return ok(hologram.idle_frame(), "Idle frame")
