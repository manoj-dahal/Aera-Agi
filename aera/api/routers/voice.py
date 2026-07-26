# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Voice and hologram endpoints."""

from __future__ import annotations

from dataclasses import replace

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_hologram, get_kernel_dep, get_voice
from ..schemas import (
    AvatarEmotionRequest,
    AvatarGestureRequest,
    ListenRequest,
    SingRequest,
    SpeakRequest,
    ok,
)

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

    from ...voice.personas import acoustics_for

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
            # Steadiness, breath and timbre: what separates one feeling from
            # the same voice merely transposed.
            "acoustics": acoustics_for(mood).to_dict(),
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
            # Expression is not optional. Kept in the payload so a client
            # does not have to infer it from the absence of a field.
            "enabled": True,
        }
    )


@voice_router.post("/mood/reset")
async def reset_mood(voice=Depends(get_voice)):
    """Clear the baseline back to neutral."""
    voice.expression.mood.reset()
    return ok(voice.expression.mood.to_dict(), "Mood reset to neutral")


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

    from ...voice.personas import acoustics_for

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
            "acoustics": acoustics_for(reading.emotion).to_dict(),
            "words": [w.to_dict() for w in words],
            "total_ms": round(sum(w.duration_ms + w.pause_after_ms for w in words), 1),
            "ssml": to_ssml(spoken, reading, persona_pitch_hz=pitch),
        }
    )


@voice_router.get("/backends")
async def list_backends(kernel=Depends(get_kernel_dep)):
    """Which speech engines can run here, and what each one needs.

    The active engine is reported alongside, so a caller can tell whether it
    is getting real speech or the bundled synthesiser without inspecting a
    result.
    """
    from ...voice.backends import probe_all

    backend = getattr(kernel.voice, "tts", None)
    statuses = probe_all(kernel.config.voice.piper_model)
    return ok(
        {
            "backends": [s.to_dict() for s in statuses],
            "active": getattr(backend, "name", type(backend).__name__),
            # True only when the active engine articulates words.
            "synthesises_speech": getattr(backend, "name", "") in ("piper", "system"),
            "configured_model": kernel.config.voice.piper_model,
        }
    )


@voice_router.get("/languages")
async def list_languages(voice=Depends(get_voice)):
    """Languages with a real expression pack, and the active one.

    Anything not listed still works, but falls back to English cue matching,
    which will misread sentiment. ``supported`` says which case you are in.
    """
    from ...voice.languages import get_pack, is_supported, supported

    packs = supported()
    return ok(
        {
            "languages": packs,
            "count": len(packs),
            "active": voice.config.language,
            "supported": is_supported(voice.config.language),
            # Which of them read every number as words. The rest keep
            # numerals where a table would be guessing.
            "spell_numbers": sorted(
                entry["code"] for entry in packs if entry["spells_all_numbers"]
            ),
            "rtl": sorted(entry["code"] for entry in packs if entry["rtl"]),
            "active_pack": get_pack(voice.config.language).to_dict(),
            "fallback": "en",
        }
    )


@voice_router.post("/languages/{code}")
async def set_language(code: str, voice=Depends(get_voice)):
    """Switch language for emotion detection and number reading."""
    from ...voice.languages import get_pack, is_supported

    pack = get_pack(code)
    voice.config.language = code
    voice.expression.language = code

    supported = is_supported(code)
    return ok(
        {"language": code, "pack": pack.to_dict(), "supported": supported},
        f"Language set to {pack.label}"
        if supported
        else f"No pack for '{code}'; falling back to English cues",
    )


@voice_router.get("/music")
async def music_reference():
    """The scales, tempo marks and time signatures the singer knows.

    Exposed so a caller can populate a picker without hardcoding a list that
    then drifts from what the engine actually accepts.
    """
    from ...voice.music import MUSIC_FOR_EMOTION, SCALES, TEMPO_MARKS

    return ok(
        {
            "scales": {name: list(steps) for name, steps in SCALES.items()},
            "tempo_marks": TEMPO_MARKS,
            "time_signatures": ["4/4", "3/4", "2/2", "6/8"],
            "emotion_settings": {
                emotion.value: setting.to_dict()
                for emotion, setting in MUSIC_FOR_EMOTION.items()
            },
        }
    )


@voice_router.post("/music/analyse")
async def analyse_lyrics(payload: SingRequest):
    """Read a lyric: structure, metre, rhyme, syllables and musical setting.

    No audio and no melody -- this is the "what is this song" call.
    """
    from ...voice.music import analyse_song

    return ok(analyse_song(payload.lyrics, language=payload.language))


@voice_router.post("/sing")
async def sing_lyrics(payload: SingRequest, voice=Depends(get_voice)):
    """Set lyrics to a melody: one note per syllable, placed on the beat.

    Returns a note plan, not audio. The melody is derived from the words --
    syllable count, stress, phrase ends -- rather than composed, and the
    accompanying analysis says what was inferred so a caller can judge it.
    """
    from ...voice.engine import Emotion
    from ...voice.music import Tempo, analyse_song, setting_for, sing

    emotion = Emotion(payload.emotion) if payload.emotion else None
    if emotion is None:
        emotion = voice.expression.analyse(payload.lyrics, language=payload.language).emotion

    setting = setting_for(emotion)
    if payload.bpm is not None:
        setting = replace(setting, tempo=Tempo(payload.bpm))
    if payload.scale is not None:
        from ...voice.music import SCALES

        if payload.scale not in SCALES:
            raise HTTPException(
                status_code=422,
                detail=f"unknown scale '{payload.scale}'; known: {sorted(SCALES)}",
            )
        setting = replace(setting, scale=payload.scale)

    try:
        phrases = sing(
            payload.lyrics,
            emotion=emotion,
            tonic=payload.tonic,
            setting=setting,
            language=payload.language,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    total = sum(p.duration_ms + p.breath_after_ms for p in phrases)
    return ok(
        {
            "phrases": [p.to_dict() for p in phrases],
            "notes": sum(len(p.notes) for p in phrases),
            "duration_ms": round(total, 1),
            "emotion": emotion.value,
            "setting": setting.to_dict(),
            "tonic": payload.tonic,
            "analysis": analyse_song(payload.lyrics, language=payload.language),
            # The same limit as elsewhere in the voice stack, stated where a
            # caller will read it rather than buried in a module docstring.
            "audio": None,
            "note": (
                "A note plan, not audio. Rendering needs a real voice model; "
                "the bundled synthesiser is a formant vocoder."
            ),
        },
        f"{sum(len(p.notes) for p in phrases)} notes over {len(phrases)} phrases",
    )


@voice_router.post("/timeline")
async def emotion_timeline(payload: SpeakRequest, voice=Depends(get_voice)):
    """Emotion over the course of a line, with millisecond bounds.

    ``/voice/analyse`` returns one label for the whole utterance. That is
    right for a single statement and wrong for anything that turns partway
    through: "It failed. But I fixed it!" is sad and then happy, and an
    avatar handed only the winner performs neither.

    Each span carries a ``blend_ms`` -- how long to ease in from the previous
    expression. Faces do not snap.
    """
    timeline = voice.expression.timeline(payload.text)
    return ok(
        timeline.to_dict(),
        f"{len(timeline.spans)} span(s), {timeline.changes} change(s)",
    )
