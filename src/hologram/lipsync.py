"""Lip Sync engine (docs/hologram/Lip-Sync.md).

Documented pipeline:

    Text → Text-to-Speech → Phonemes → Lip Animation → Avatar

Maps text to the 9 documented mouth shapes (A, E, I, O, U, Closed, Smile,
Wide, Relaxed) as a viseme timeline. Emotion-aware per the doc: happy
emotions bias open/smile shapes; the timeline speed follows the Emotion
Engine's speaking_speed so voice and mouth stay synchronized.
"""

from __future__ import annotations

from src.hologram.models import MouthShape, Viseme

# Grapheme → viseme mapping (real phoneme extraction plugs in with TTS).
_VOWELS: dict[str, MouthShape] = {
    "a": MouthShape.A,
    "e": MouthShape.E,
    "i": MouthShape.I,
    "o": MouthShape.O,
    "u": MouthShape.U,
    "y": MouthShape.I,
}
_CLOSED = set("mbp")  # bilabials close the mouth
_WIDE = set("szcjx")  # sibilants widen the mouth

_BASE_MS = 70  # per-viseme duration at speaking_speed 1.0


def text_to_visemes(
    text: str,
    speaking_speed: float = 1.0,
    smiling: bool = False,
) -> list[Viseme]:
    """Convert text into a mouth-shape timeline for the renderer."""
    duration = max(20, int(_BASE_MS / max(speaking_speed, 0.1)))
    visemes: list[Viseme] = []
    last: MouthShape | None = None

    for char in text.lower():
        if char in _VOWELS:
            shape = _VOWELS[char]
        elif char in _CLOSED:
            shape = MouthShape.CLOSED
        elif char in _WIDE:
            shape = MouthShape.WIDE
        elif char.isalpha():
            shape = MouthShape.RELAXED
        elif char in ".!?,;:":
            shape = MouthShape.SMILE if smiling else MouthShape.CLOSED
        elif char.isspace():
            shape = MouthShape.RELAXED
        else:
            continue

        if visemes and shape == last:
            # Merge consecutive identical shapes (smooth mouth transitions).
            visemes[-1] = Viseme(
                shape=shape, duration_ms=visemes[-1].duration_ms + duration
            )
        else:
            visemes.append(Viseme(shape=shape, duration_ms=duration))
        last = shape

    # End with the resting mouth (smile if the emotion is happy).
    rest = MouthShape.SMILE if smiling else MouthShape.CLOSED
    if not visemes or visemes[-1].shape != rest:
        visemes.append(Viseme(shape=rest, duration_ms=duration * 2))
    return visemes
