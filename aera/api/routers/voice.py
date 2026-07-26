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


# --------------------------------------------------------------------------- #
# personas
# --------------------------------------------------------------------------- #
@voice_router.get("/personas")
async def list_personas(kernel=Depends(get_kernel_dep)):
    """Available voices, and which one is speaking.

    Reports the bundled synthesiser's limitation alongside them, so a caller
    knows what the audio will and will not contain.
    """
    from ...voice.personas import FORMANT_NOTE, PERSONAS, PersonaTTS

    backend = getattr(kernel.voice, "tts", None)
    active = backend.persona.id if isinstance(backend, PersonaTTS) else None

    return ok(
        {
            "personas": [p.to_dict() for p in PERSONAS.values()],
            "active": active,
            "engine": getattr(backend, "name", "unknown"),
            "synthesises_speech": False,
            "note": FORMANT_NOTE,
        }
    )


@voice_router.post("/personas/{persona_id}")
async def set_persona(persona_id: str, kernel=Depends(get_kernel_dep)):
    """Choose the speaking voice, e.g. anime-g or anime-b."""
    from ...core.errors import ValidationError
    from ...voice.personas import PERSONAS

    key = persona_id.strip().lower()
    if key not in PERSONAS:
        raise ValidationError(
            f"unknown persona '{persona_id}'",
            details={"available": sorted(PERSONAS)},
        )

    persona = kernel.use_voice_persona(key)
    return ok(persona, f"Voice set to {persona['label']}")


@voice_router.post("/preview")
async def preview_persona(
    persona_id: str,
    text: str = "Hello, I am AERA. How can I help you today?",
    emotion: str | None = None,
    kernel=Depends(get_kernel_dep),
):
    """Render a sample line in one persona without changing the active voice.

    Lets the settings UI audition a voice before committing to it.
    """
    from ...core.errors import ValidationError
    from ...voice.engine import Emotion
    from ...voice.personas import FORMANT_NOTE, PERSONAS, get_persona, synthesize_wav

    if persona_id.strip().lower() not in PERSONAS:
        raise ValidationError(
            f"unknown persona '{persona_id}'", details={"available": sorted(PERSONAS)}
        )

    persona = get_persona(persona_id)
    mood = Emotion(emotion) if emotion else Emotion.NEUTRAL
    directory = kernel.config.storage_dir / "speech"
    path, duration_ms, visemes = synthesize_wav(
        text, persona, emotion=mood, path=directory / f"preview-{persona.id}.wav"
    )

    return ok(
        {
            "persona": persona.to_dict(),
            "emotion": mood.value,
            "pitch_hz": round(persona.pitch_for(mood), 1),
            "speed": round(persona.speed_for(mood), 3),
            "duration_ms": duration_ms,
            "visemes": len(visemes),
            "audio_path": str(path) if path else None,
            "note": FORMANT_NOTE,
        }
    )


# --------------------------------------------------------------------------- #
# expression: mood and prosody
# --------------------------------------------------------------------------- #
@voice_router.get("/mood")
async def get_mood(voice=Depends(get_voice)):
    """The current emotional baseline.

    Mood persists between utterances and decays toward neutral, so a run of
    failures leaves AERA subdued for a while rather than resetting instantly.
    """
    return ok(
        {
            **voice.expression.mood.to_dict(),
            "enabled": voice.config.emotion,
        }
    )


@voice_router.post("/mood/reset")
async def reset_mood(voice=Depends(get_voice)):
    """Clear the baseline back to neutral."""
    voice.expression.mood.reset()
    return ok(voice.expression.mood.to_dict(), "Mood reset to neutral")


@voice_router.post("/mood/enabled")
async def set_mood_enabled(enabled: bool, voice=Depends(get_voice)):
    """Turn expression off entirely.

    With this off AERA speaks flatly: no emotion detection, no mood, no
    contour. Some users want an assistant that does not perform.
    """
    voice.config.emotion = enabled
    if not enabled:
        voice.expression.mood.reset()
    return ok(
        {"enabled": enabled, **voice.expression.mood.to_dict()},
        "Expression enabled" if enabled else "Expression off - flat delivery",
    )


@voice_router.post("/analyse")
async def analyse_expression(text: str, voice=Depends(get_voice)):
    """Explain how a line would be delivered, without speaking it.

    Returns the detected emotion with the cues that produced it, plus the
    per-word prosody and the SSML a real engine would receive.
    """
    # A dry run must not move the standing mood.
    from ...voice.expression import ExpressionAnalyser, Mood, prosody_for, to_ssml
    from ...voice.personas import PersonaTTS

    scratch = ExpressionAnalyser(Mood(valence=voice.expression.mood.decayed()))
    reading = scratch.analyse(text)

    backend = getattr(voice, "tts", None)
    pitch = None
    if isinstance(backend, PersonaTTS):
        pitch = backend.persona.pitch_for(reading.emotion)

    # Show the form the engine will actually speak, not the raw input, so
    # the preview matches what /voice/speak produces.
    from ...voice.phonetics import normalise_for_speech

    spoken = normalise_for_speech(text) or text
    words = prosody_for(spoken, emotion=reading.emotion, intensity=reading.intensity)
    return ok(
        {
            "text": text,
            "spoken": spoken,
            **reading.to_dict(),
            "pitch_hz": round(pitch, 1) if pitch else None,
            "words": [w.to_dict() for w in words],
            "total_ms": round(sum(w.duration_ms + w.pause_after_ms for w in words), 1),
            "ssml": to_ssml(spoken, reading, persona_pitch_hz=pitch),
        }
    )
