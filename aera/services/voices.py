# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Custom voices: user-supplied Piper models registered as personas.

AERA ships exactly two voices, Girl and Boy. That is a deliberate default --
a list of three where one is an unnamed "AERA" is a choice nobody can make
meaningfully -- but two is also not enough for everyone, and the answer to
that is not to guess at a third.

So a user can add their own. A Piper voice is an ``.onnx`` file plus an
``.onnx.json`` config beside it, downloaded from
``huggingface.co/rhasspy/piper-voices`` or trained locally. Registering one
here makes it selectable in Settings exactly like the built-in two, and
unlike them it produces real articulated speech.

Three things this refuses to do, each because the alternative would be a
quiet lie:

*It does not accept an audio recording as a "voice".* Cloning a voice from a
sample needs a training pipeline that is not bundled. A dropped MP3 is
rejected by name rather than stored and silently ignored.

*It does not validate by extension alone.* An ``.onnx`` file that is not an
ONNX model, or a config missing its sample rate, fails at registration where
the user is watching -- not at the first attempt to speak.

*It does not copy the model into the store.* Voice models run to tens of
megabytes and users keep them deliberately. The registry records a path and
verifies the file is still there on load, reporting it as unavailable rather
than pretending.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.errors import ValidationError
from ..core.logging import get_logger
from ..voice.personas import VoicePersona

logger = get_logger("services.voices")

#: Where the registry lives, relative to the storage root.
REGISTRY_FILE = "voices.json"

#: The smallest plausible Piper model. Anything under this is a truncated
#: download, which otherwise fails much later with an opaque ONNX error.
MIN_MODEL_BYTES = 1_000_000

#: An ONNX file begins with a protobuf field header. Not a full parse, but
#: enough to reject a renamed MP3 or an HTML error page saved as .onnx --
#: both of which happen when a download goes wrong.
_ONNX_MAGIC = b"\x08"

#: Audio formats a user might reasonably but wrongly drop here.
_AUDIO_SUFFIXES = frozenset({".mp3", ".wav", ".m4a", ".flac", ".ogg", ".opus", ".aac"})


@dataclass
class CustomVoice:
    """A user-registered voice model."""

    id: str
    label: str
    model_path: str
    config_path: str
    #: feminine, masculine or unspecified. Chosen by the user; nothing here
    #: can infer it from the model.
    variant: str = "unspecified"
    #: Reported by the model config, not guessed.
    sample_rate: int = 22_050
    language: str = "en"
    speakers: int = 1
    notes: str = ""

    @property
    def exists(self) -> bool:
        """Whether the model file is still where it was registered."""
        return Path(self.model_path).is_file() and Path(self.config_path).is_file()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "variant": self.variant,
            "model_path": self.model_path,
            "config_path": self.config_path,
            "sample_rate": self.sample_rate,
            "language": self.language,
            "speakers": self.speakers,
            "notes": self.notes,
            "available": self.exists,
            "custom": True,
            # Unlike the two bundled personas, a real model does speak words.
            "synthesises_speech": self.exists,
        }

    def to_persona(self) -> VoicePersona:
        """Expose it as a persona so the rest of the engine is unchanged.

        Pitch and brightness are the built-in defaults: a neural model
        carries its own timbre and there is nothing useful to invent here.
        The emotion machinery still applies -- speed and length scale are
        honoured by Piper.
        """
        return VoicePersona(
            id=self.id,
            label=self.label,
            description=self.notes or f"Custom voice ({Path(self.model_path).name})",
            variant=self.variant,
            base_pitch_hz=190.0,
            speed=1.0,
            pitch_range=0.15,
            brightness=1.0,
            vibrato=0.008,
            engine_hints={"piper": {"model": self.model_path, "config": self.config_path}},
        )


def _slug(value: str) -> str:
    """A stable, filesystem-safe id from a label."""
    cleaned = "".join(c.lower() if c.isalnum() else "-" for c in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "voice"


def inspect_model(model: Path, config: Path | None = None) -> dict[str, Any]:
    """Read what a Piper model declares about itself.

    Validates before registering, so a bad file fails while the user is
    looking at the screen rather than at the first attempt to speak.
    """
    model = Path(model).expanduser()

    if model.suffix.lower() in _AUDIO_SUFFIXES:
        raise ValidationError(
            f"{model.name} is an audio recording, not a voice model",
            details={
                "remedy": (
                    "AERA cannot clone a voice from a recording -- that needs a "
                    "training pipeline which is not bundled. Supply a Piper "
                    ".onnx model instead, from huggingface.co/rhasspy/piper-voices"
                )
            },
        )

    if model.suffix.lower() != ".onnx":
        raise ValidationError(
            f"expected a .onnx voice model, got '{model.suffix or 'no extension'}'",
            details={"remedy": "Piper voices are .onnx files with a .onnx.json beside them"},
        )

    if not model.is_file():
        raise ValidationError(f"no such model: {model}")

    size = model.stat().st_size
    if size < MIN_MODEL_BYTES:
        raise ValidationError(
            f"{model.name} is only {size // 1024} KB, too small to be a voice model",
            details={"remedy": "the download was probably truncated; fetch it again"},
        )

    with model.open("rb") as handle:
        head = handle.read(1)
    if head != _ONNX_MAGIC:
        raise ValidationError(
            f"{model.name} does not look like an ONNX model",
            details={"remedy": "check the download; an HTML error page is a common cause"},
        )

    # Piper names the config after the model: voice.onnx -> voice.onnx.json.
    resolved = Path(config).expanduser() if config else model.with_suffix(".onnx.json")
    if not resolved.is_file():
        raise ValidationError(
            f"the model config is missing: {resolved.name}",
            details={
                "remedy": (
                    "download the .onnx.json alongside the .onnx; Piper needs both"
                )
            },
        )

    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{resolved.name} is not readable JSON: {exc}") from exc

    audio = data.get("audio") or {}
    rate = audio.get("sample_rate")
    if not rate:
        raise ValidationError(
            f"{resolved.name} declares no sample rate",
            details={"remedy": "this does not look like a Piper voice config"},
        )

    return {
        "model_path": str(model.resolve()),
        "config_path": str(resolved.resolve()),
        "sample_rate": int(rate),
        "language": (data.get("language") or {}).get("code", "en"),
        "speakers": int(data.get("num_speakers") or 1),
        "size_bytes": size,
        "dataset": data.get("dataset", ""),
    }


class VoiceLibrary:
    """The set of user-registered voices, persisted across restarts."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.file = self.root / REGISTRY_FILE
        self._voices: dict[str, CustomVoice] = {}
        self._load()

    def _load(self) -> None:
        if not self.file.is_file():
            return
        try:
            entries = json.loads(self.file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            # A corrupt registry must not stop the voice engine starting.
            logger.warning("could not read %s: %s", self.file, exc)
            return
        for entry in entries:
            try:
                voice = CustomVoice(**entry)
            except TypeError as exc:
                logger.warning("skipping malformed voice entry: %s", exc)
                continue
            self._voices[voice.id] = voice
        missing = [v.id for v in self._voices.values() if not v.exists]
        if missing:
            # Reported, not deleted: a model on an unmounted drive should
            # come back when it is mounted again.
            logger.info("custom voices with a missing model file: %s", ", ".join(missing))

    def _save(self) -> None:
        payload = [
            {
                k: v
                for k, v in voice.__dict__.items()
                if not k.startswith("_")
            }
            for voice in self._voices.values()
        ]
        self.file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # -- registry --------------------------------------------------------- #
    def add(
        self,
        label: str,
        model_path: str | Path,
        *,
        config_path: str | Path | None = None,
        variant: str = "unspecified",
        notes: str = "",
    ) -> CustomVoice:
        """Register a voice model after validating it."""
        from ..voice.personas import PERSONAS

        clean = (label or "").strip()
        if not clean:
            raise ValidationError("a voice needs a name")
        if variant not in ("feminine", "masculine", "unspecified"):
            raise ValidationError(
                f"unknown variant '{variant}'",
                details={"available": ["feminine", "masculine", "unspecified"]},
            )

        details = inspect_model(Path(model_path), Path(config_path) if config_path else None)

        identifier = _slug(clean)
        if identifier in PERSONAS:
            raise ValidationError(
                f"'{identifier}' is a built-in voice; choose another name",
                details={"reserved": sorted(PERSONAS)},
            )
        if identifier in self._voices:
            raise ValidationError(f"a voice called '{identifier}' is already registered")

        voice = CustomVoice(
            id=identifier,
            label=clean,
            model_path=details["model_path"],
            config_path=details["config_path"],
            variant=variant,
            sample_rate=details["sample_rate"],
            language=details["language"],
            speakers=details["speakers"],
            notes=notes,
        )
        self._voices[identifier] = voice
        self._save()
        logger.info("registered custom voice %s (%s)", identifier, details["model_path"])
        return voice

    def remove(self, voice_id: str) -> bool:
        """Forget a voice. The model file on disk is left alone."""
        if voice_id not in self._voices:
            return False
        del self._voices[voice_id]
        self._save()
        return True

    def get(self, voice_id: str) -> CustomVoice | None:
        return self._voices.get(voice_id)

    def all(self) -> list[CustomVoice]:
        return list(self._voices.values())

    def available(self) -> list[CustomVoice]:
        """Only the ones whose model file is actually present."""
        return [v for v in self._voices.values() if v.exists]

    def import_file(self, source: Path, label: str, **kwargs: Any) -> CustomVoice:
        """Copy a model into the store, then register it.

        Used when a file arrives by upload rather than already living
        somewhere the user chose.
        """
        source = Path(source)
        target_dir = self.root / "models"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / source.name
        shutil.copy2(source, target)

        config_source = source.with_suffix(".onnx.json")
        if config_source.is_file():
            shutil.copy2(config_source, target.with_suffix(".onnx.json"))

        try:
            return self.add(label, target, **kwargs)
        except ValidationError:
            # Do not leave a rejected model sitting in the store.
            target.unlink(missing_ok=True)
            target.with_suffix(".onnx.json").unlink(missing_ok=True)
            raise

    def to_dict(self) -> dict[str, Any]:
        voices = self.all()
        return {
            "voices": [v.to_dict() for v in voices],
            "count": len(voices),
            "available": sum(1 for v in voices if v.exists),
            "store": str(self.root),
        }
