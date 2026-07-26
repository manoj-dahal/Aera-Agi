# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Real TTS backends.

Until now the answer to "how do I get actual speech?" was "implement
TTSBackend yourself" -- which meant reading the persona dataclass, working out
how pitch and intensity map onto your engine's parameters, and writing the
adapter. The mapping was documented but never written.

These adapters close that gap. Each takes a :class:`VoicePersona` and an
:class:`EmotionAcoustics` profile and translates them into what the engine
actually accepts, so the same expression analysis drives Piper or a system
binary without the caller doing the arithmetic.

Nothing here bundles a voice model. Every adapter reports precisely what it
needs and where to get it, and refuses to load rather than falling back to
something that sounds wrong without saying so.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.errors import ValidationError
from ..core.logging import get_logger
from .engine import Emotion, SpeechRequest, SpeechResult, TTSBackend, generate_visemes
from .personas import NEUTRAL, VoicePersona, acoustics_for, audio_filename

logger = get_logger("voice.backends")

#: Where Piper voices come from. Stated in the error so a user is not left
#: guessing which of several similarly-named files they need.
PIPER_VOICES_URL = "https://huggingface.co/rhasspy/piper-voices"


@dataclass
class BackendStatus:
    """Whether a backend can run, and what is missing if not."""

    name: str
    available: bool
    detail: str
    #: What to install or download, when that is the blocker.
    remedy: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "available": self.available,
            "detail": self.detail,
            "remedy": self.remedy,
        }


def _length_scale(persona: VoicePersona, emotion: Emotion) -> float:
    """Piper's length scale: above 1.0 is slower.

    The persona expresses pace as a speed multiplier, which is the inverse,
    so this is not simply passed through.
    """
    speed = max(0.3, persona.speed_for(emotion))
    hinted = float(persona.engine_hints.get("piper", {}).get("length_scale", 1.0))
    return max(0.4, min(2.5, hinted / speed))


def _noise_scale(emotion: Emotion) -> float:
    """Map jitter and breath onto Piper's noise parameter.

    Piper has no breathiness control, but its noise scale governs how much
    variation the vocoder introduces, which is the closest available proxy.
    """
    voice = acoustics_for(emotion)
    # Piper's default is 0.667; move around it rather than replacing it.
    return max(0.2, min(1.2, 0.667 + voice.jitter * 8.0 + voice.breathiness * 0.5))


class PiperTTS(TTSBackend):
    """Neural speech via Piper.

    Piper is local, fast and CPU-only, which suits a desktop assistant. It
    needs a voice model: a ``.onnx`` file and its ``.onnx.json`` config,
    downloaded once from the Rhasspy voice collection.

    Persona and emotion drive length scale, noise scale and volume. Piper
    exposes no direct pitch control, so the persona's fundamental is carried
    by the choice of voice model rather than by transposition -- pitch-shifting
    a neural voice after the fact sounds artificial.
    """

    name = "piper"

    def __init__(
        self,
        model_path: str | Path,
        *,
        persona: VoicePersona | None = None,
        output_dir: Path | None = None,
        config_path: str | Path | None = None,
    ) -> None:
        self.model_path = Path(model_path).expanduser()
        self.config_path = Path(config_path).expanduser() if config_path else None
        self.persona = persona or NEUTRAL
        self.output_dir = Path(output_dir) if output_dir else None
        self._voice: Any = None

    # ------------------------------------------------------------------ #
    # availability
    # ------------------------------------------------------------------ #
    @classmethod
    def probe(cls, model_path: str | Path | None = None) -> BackendStatus:
        """Whether Piper could run, without loading anything."""
        try:
            import piper  # noqa: F401
        except ImportError:
            return BackendStatus(
                cls.name,
                False,
                "the piper-tts package is not installed",
                remedy="pip install piper-tts",
            )

        if model_path is None:
            return BackendStatus(
                cls.name,
                False,
                "piper is installed but no voice model was configured",
                remedy=f"download a .onnx voice from {PIPER_VOICES_URL}",
            )

        path = Path(model_path).expanduser()
        if not path.is_file():
            return BackendStatus(
                cls.name,
                False,
                f"voice model not found at {path}",
                remedy=f"download a .onnx voice from {PIPER_VOICES_URL}",
            )
        if not path.with_suffix(path.suffix + ".json").is_file() and not path.with_suffix(
            ".onnx.json"
        ).is_file():
            return BackendStatus(
                cls.name,
                False,
                f"{path.name} has no .onnx.json config beside it",
                remedy="download the matching .onnx.json alongside the model",
            )

        return BackendStatus(cls.name, True, f"ready with {path.name}")

    def load(self) -> None:
        """Load the model, raising with the reason if it cannot."""
        status = self.probe(self.model_path)
        if not status.available:
            raise ValidationError(
                status.detail, details={"remedy": status.remedy, "backend": self.name}
            )

        from piper import PiperVoice

        self._voice = PiperVoice.load(
            str(self.model_path),
            config_path=str(self.config_path) if self.config_path else None,
        )
        logger.info("piper voice loaded: %s", self.model_path.name)

    def use(self, persona: VoicePersona) -> None:
        self.persona = persona

    # ------------------------------------------------------------------ #
    # synthesis
    # ------------------------------------------------------------------ #
    async def synthesize(self, request: SpeechRequest) -> SpeechResult:
        if self._voice is None:
            self.load()

        target = None
        if self.output_dir is not None:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            target = self.output_dir / audio_filename(
                request.text, self.persona.id, request.emotion
            )

        # Piper is synchronous and CPU-bound; keep it off the event loop.
        duration_ms = await asyncio.to_thread(self._render, request, target)

        return SpeechResult(
            text=request.text,
            emotion=request.emotion,
            duration_ms=round(duration_ms, 2),
            visemes=generate_visemes(request.text, duration_ms),
            audio_path=str(target) if target else None,
            engine=f"{self.name}:{self.persona.id}",
        )

    def _render(self, request: SpeechRequest, target: Path | None) -> float:
        from piper import SynthesisConfig

        config = SynthesisConfig(
            length_scale=_length_scale(self.persona, request.emotion),
            noise_scale=_noise_scale(request.emotion),
            volume=max(0.1, min(1.0, request.volume / 100.0)),
            speaker_id=self.persona.engine_hints.get("piper", {}).get("speaker_id"),
        )

        if target is not None:
            with wave.open(str(target), "wb") as handle:
                self._voice.synthesize_wav(request.text, handle, syn_config=config)
            with wave.open(str(target)) as handle:
                return handle.getnframes() / handle.getframerate() * 1000.0

        # No file wanted: still synthesise, to report a truthful duration.
        frames = sum(len(chunk.audio_int16_bytes) for chunk in
                     self._voice.synthesize(request.text, syn_config=config))
        rate = getattr(self._voice.config, "sample_rate", 22_050)
        return frames / 2 / rate * 1000.0


#: macOS `say` voices by language. Only the ones shipped by default are
#: named; anything else falls back to the system voice, which is better than
#: naming a voice that may not be installed.
_SAY_VOICES: dict[str, str] = {
    "en": "Samantha", "es": "Monica", "fr": "Thomas", "de": "Anna",
    "it": "Alice", "pt": "Luciana", "nl": "Xander", "sv": "Alva",
    "pl": "Zosia", "ru": "Milena", "el": "Melina", "tr": "Yelda",
    "hi": "Lekha", "ar": "Maged", "he": "Carmit", "th": "Kanya",
    "ja": "Kyoko", "zh": "Ting-Ting", "ko": "Yuna", "id": "Damayanti",
}


def espeak_voice(language: str | None) -> str | None:
    """The espeak voice code for a language tag, or None to leave the default.

    espeak uses plain ISO 639-1 codes, so the base subtag is the voice name
    for almost every language the packs cover.
    """
    if not language:
        return None
    base = language.strip().lower().split("-")[0].split("_")[0]
    return base or None


def say_voice(language: str | None) -> str | None:
    """The macOS `say` voice for a language, or None for the system default."""
    if not language:
        return None
    base = language.strip().lower().split("-")[0].split("_")[0]
    return _SAY_VOICES.get(base)


class SystemTTS(TTSBackend):
    """Speech via a system binary: espeak-ng, say (macOS) or spd-say.

    Lower quality than Piper, but present on many machines with no download,
    which makes it a reasonable fallback when nothing else is configured.
    Unlike Piper these accept an explicit pitch, so the persona's fundamental
    is honoured directly.
    """

    name = "system"

    #: Binaries that can write a WAV, in order of preference. spd-say is
    #: excluded: its "-w" means *wait for completion*, not *write to file*,
    #: and it speaks to the sound card with no way to capture the audio. It
    #: was in this list and produced a command that ignored the output path
    #: entirely, so the backend reported success and left no file.
    ENGINES = ("espeak-ng", "espeak", "say")

    def __init__(
        self,
        *,
        persona: VoicePersona | None = None,
        output_dir: Path | None = None,
        binary: str | None = None,
    ) -> None:
        self.persona = persona or NEUTRAL
        self.output_dir = Path(output_dir) if output_dir else None
        self.binary = binary or self._discover()

    @classmethod
    def _discover(cls) -> str | None:
        return next((b for b in cls.ENGINES if shutil.which(b)), None)

    @classmethod
    def probe(cls) -> BackendStatus:
        found = cls._discover()
        if found:
            return BackendStatus(cls.name, True, f"using {found}")
        return BackendStatus(
            cls.name,
            False,
            "no system speech binary found",
            remedy="install espeak-ng (Linux) or use macOS 'say'",
        )

    def use(self, persona: VoicePersona) -> None:
        self.persona = persona

    def _command(self, request: SpeechRequest, target: Path) -> list[str]:
        """Argument list for the discovered binary.

        espeak takes pitch as 0-99 and rate in words per minute; macOS `say`
        takes only a rate. Each is mapped from the persona rather than passed
        a shared value that means different things to different tools.
        """
        pitch_hz = self.persona.pitch_for(request.emotion)
        speed = self.persona.speed_for(request.emotion) * request.speed

        if self.binary in ("espeak-ng", "espeak"):
            # espeak's pitch is a 0-99 scale centred near 50 at ~110 Hz.
            pitch = max(0, min(99, int((pitch_hz / 110.0) * 50)))
            command = [
                self.binary,
                "-p", str(pitch),
                "-s", str(int(175 * speed)),
                "-w", str(target),
            ]
            # Thirty-five language packs, and the engine was never told which
            # one: espeak read every line with English letter-to-sound rules,
            # so Spanish and German came out as an English speaker sounding
            # them out.
            voice = espeak_voice(request.language)
            if voice:
                command += ["-v", voice]
            return [*command, request.text]
        if self.binary == "say":
            command = [
                self.binary,
                "-r", str(int(175 * speed)),
                "-o", str(target),
                "--data-format=LEI16@22050",
            ]
            voice = say_voice(request.language)
            if voice:
                command += ["-v", voice]
            return [*command, request.text]
        raise ValidationError(
            f"{self.binary} cannot write audio to a file",
            details={"backend": self.name, "binary": self.binary},
        )

    async def synthesize(self, request: SpeechRequest) -> SpeechResult:
        if not self.binary:
            status = self.probe()
            raise ValidationError(
                status.detail, details={"remedy": status.remedy, "backend": self.name}
            )

        # tempfile, not a hardcoded "/tmp": on Windows that string resolves
        # to C:\tmp, which does not exist, so mkdir created a stray directory
        # at the root of the system drive on the first line AERA ever spoke.
        directory = self.output_dir or Path(tempfile.gettempdir()) / "aera-voice"
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / audio_filename(
            request.text, self.persona.id, request.emotion
        )

        try:
            await asyncio.to_thread(
                subprocess.run,
                self._command(request, target),
                check=True,
                capture_output=True,
                timeout=60,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            raise ValidationError(f"{self.binary} failed: {exc}") from exc

        duration_ms = 0.0
        if target.is_file():
            try:
                with wave.open(str(target)) as handle:
                    duration_ms = handle.getnframes() / handle.getframerate() * 1000.0
            except wave.Error:
                duration_ms = 0.0

        return SpeechResult(
            text=request.text,
            emotion=request.emotion,
            duration_ms=round(duration_ms, 2),
            visemes=generate_visemes(request.text, duration_ms),
            audio_path=str(target) if target.is_file() else None,
            engine=f"{self.name}:{self.binary}",
        )


def probe_all(piper_model: str | Path | None = None) -> list[BackendStatus]:
    """Every backend and whether it can run here.

    The bundled synthesiser is always available, so the list is never empty;
    it is reported last because it does not produce speech.
    """
    return [
        PiperTTS.probe(piper_model),
        SystemTTS.probe(),
        BackendStatus(
            "persona",
            True,
            "bundled formant synthesiser: pitch, timing and lip-sync only",
            remedy="install piper-tts and a voice model for real speech",
        ),
    ]


def best_available(
    persona: VoicePersona | None = None,
    *,
    piper_model: str | Path | None = None,
    output_dir: Path | None = None,
) -> TTSBackend:
    """The best backend that can actually run, preferring real speech.

    Falls back to the bundled synthesiser, which never fails but does not
    articulate words -- the caller can check ``engine`` on the result, or
    ``probe_all`` beforehand, to know which they got.
    """
    from .personas import PersonaTTS

    if piper_model and PiperTTS.probe(piper_model).available:
        return PiperTTS(piper_model, persona=persona, output_dir=output_dir)
    if SystemTTS.probe().available:
        return SystemTTS(persona=persona, output_dir=output_dir)
    return PersonaTTS(persona, output_dir=output_dir)
