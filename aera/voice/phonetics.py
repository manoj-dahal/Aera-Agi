"""Text normalisation and phoneme-based visemes.

Two problems this solves.

**Spoken form.** A voice engine reads what it is given. "87%" becomes "eighty
seven percent" only if something converts it; otherwise Piper says "eighty
seven percent sign" or spells the symbol. URLs, currency, times and
abbreviations all need expanding before synthesis.

**Mouth shapes.** The original viseme track was one shape per *letter*, so
"make" produced four mouth movements for three sounds and animated the silent
e. Grapheme clusters are matched here instead -- "th", "sh", "ch", silent
finals, vowel digraphs -- which is not a full phonemiser but is markedly
closer to how a mouth actually moves.
"""

from __future__ import annotations

import re
from typing import Any

from ..core.logging import get_logger

logger = get_logger("voice.phonetics")

def say_number(value: int) -> str:
    """Spell an integer in English, the way it is read aloud.

    A thin wrapper over the English language pack. This used to be a second,
    independent implementation, and the two had already drifted: it said
    "three hundred and forty two" while the pack said "three hundred forty
    two" for the same input, and the pack is the one the pipeline actually
    calls. One reader now, so they cannot disagree again.
    """
    from .languages import ENGLISH, say_number_in

    return say_number_in(value, ENGLISH)


#: Abbreviations whose trailing dot is not a sentence boundary. Without this
#: "Dr. Smith" takes a 380 ms sentence pause in the middle of a name.
ABBREVIATIONS: dict[str, str] = {
    "dr": "doctor", "mr": "mister", "mrs": "missus", "ms": "miz",
    "prof": "professor", "st": "street", "ave": "avenue", "vs": "versus",
    "etc": "etcetera", "e.g": "for example", "i.e": "that is",
    "approx": "approximately", "min": "minutes", "sec": "seconds",
    "hr": "hours", "no": "number", "fig": "figure", "vol": "volume",
}

#: Technical terms a TTS engine mangles when read letter by letter.
PRONUNCIATIONS: dict[str, str] = {
    "sql": "sequel", "sqlite": "sequel light", "nginx": "engine x",
    "kubernetes": "koo ber net eez", "postgres": "post gress",
    "postgresql": "post gress sequel", "json": "jay son", "yaml": "yam ul",
    "jwt": "jot", "oauth": "oh auth", "async": "ay sink", "regex": "reg ex",
    "cli": "C L I", "api": "A P I", "cpu": "C P U", "gpu": "G P U",
    "ram": "ram", "ssd": "S S D", "url": "U R L", "uri": "U R I",
    "http": "H T T P", "https": "H T T P S", "ssh": "S S H", "tls": "T L S",
    "ui": "U I", "ux": "U X", "css": "C S S", "html": "H T M L",
    "ci": "C I", "cd": "C D", "aera": "air uh",
}

_UNITS: dict[str, tuple[str, str]] = {
    "%": ("percent", "percent"),
    "ms": ("millisecond", "milliseconds"),
    "kb": ("kilobyte", "kilobytes"),
    "mb": ("megabyte", "megabytes"),
    "gb": ("gigabyte", "gigabytes"),
    "tb": ("terabyte", "terabytes"),
    "hz": ("hertz", "hertz"),
    "khz": ("kilohertz", "kilohertz"),
}

_CURRENCY = {"$": "dollars", "£": "pounds", "€": "euros", "¥": "yen"}


def normalise_for_speech(text: str, language: str = "en") -> str:
    """Rewrite text into the form it should be read aloud in.

    Runs before synthesis so the engine receives words, not symbols. Order
    matters: URLs first, because they contain dots and slashes that the
    later rules would otherwise mangle.

    Numbers and units are spoken in ``language``. A pack without number words
    leaves digits alone, which is deliberate -- an English "eighty seven"
    inside a Japanese sentence is worse than the numeral.
    """
    if not text or not text.strip():
        return ""

    from .languages import get_pack, say_number_in

    pack = get_pack(language)

    def _spell(value: int) -> str:
        return say_number_in(value, pack)

    def _decimal(raw: str) -> str:
        whole, _, fraction = raw.partition(".")
        spoken = _spell(int(whole or 0))
        if fraction and pack.ones:
            digits = " ".join(pack.ones[int(d)] for d in fraction if d.isdigit())
            return f"{spoken} {pack.point} {digits}"
        return spoken

    out = text

    # URLs and emails, before anything touches their punctuation.
    out = re.sub(
        r"https?://(?:www\.)?([^\s/]+)(/\S*)?",
        lambda m: f"the site {m.group(1).replace('.', ' dot ')}",
        out,
    )
    out = re.sub(
        r"\b([\w.+-]+)@([\w-]+)\.(\w+)\b",
        lambda m: f"{m.group(1)} at {m.group(2)} dot {m.group(3)}",
        out,
    )

    # File paths read as a stream of slashes otherwise.
    out = re.sub(r"(?<!\w)/(\w[\w./-]*)", lambda m: " slash ".join(m.group(1).split("/")), out)

    # Currency: "$1,200" -> "one thousand two hundred dollars".
    def _currency(match: re.Match[str]) -> str:
        amount = match.group(2).replace(",", "")
        word = _CURRENCY.get(match.group(1), "")
        return f"{_decimal(amount)} {word}"

    out = re.sub(r"([$£€¥])\s?([\d,]+(?:\.\d+)?)", _currency, out)

    # Times: "3:30" -> "three thirty", "14:05" -> "fourteen oh five".
    def _time(match: re.Match[str]) -> str:
        hour, minute = int(match.group(1)), int(match.group(2))
        if minute == 0:
            spoken = f"{_spell(hour)} o'clock"
        elif minute < 10:
            spoken = f"{_spell(hour)} oh {_spell(minute)}"
        else:
            spoken = f"{_spell(hour)} {_spell(minute)}"
        suffix = match.group(3)
        return f"{spoken} {suffix.upper().replace('M', ' M')}" if suffix else spoken

    # Times and abbreviations are English-specific; other languages keep the
    # numeral, which a real engine reads correctly in its own convention.
    if pack.code == "en":
        out = re.sub(r"\b(\d{1,2}):(\d{2})\s?([ap]m)?\b", _time, out, flags=re.IGNORECASE)

    # Version strings stay as digits but gain spoken dots.
    out = re.sub(
        r"\bv?(\d+)\.(\d+)(?:\.(\d+))?\b",
        lambda m: f" {pack.point} ".join(_spell(int(g)) for g in m.groups() if g),
        out,
    )

    def _unit_percent(match: re.Match[str], pack: Any) -> str:
        amount = match.group(1).replace(",", "")
        singular, plural = pack.units.get("%", _UNITS["%"])
        value = float(amount)
        word = singular if value == 1 else plural
        if "%" in pack.units_before:
            # Chinese puts the unit first: 百分之八十七.
            return f"{word}{_decimal(amount)}"
        return f"{_decimal(amount)} {word}"

    # Numbers with units: "87%" -> "eighty seven percent".
    def _unit(match: re.Match[str]) -> str:
        amount = match.group(1).replace(",", "")
        unit = match.group(2).lower()
        # Falling back to the English word would put "percent" inside a
        # Japanese sentence; leave the symbol for the engine instead.
        if unit not in pack.units and pack.code != "en":
            return match.group(0)
        singular, plural = pack.units.get(unit, _UNITS[unit])
        value = float(amount)
        word = singular if value == 1 else plural
        if unit in pack.units_before:
            return f"{word}{_decimal(amount)}"
        return f"{_decimal(amount)} {word}"

    # Two patterns: "%" is not a word character, so a trailing \b after it
    # can never assert and the alternation silently skipped every percentage.
    # Arabic and Persian write the percent sign as ٪ (U+066A) and Chinese
    # text sometimes uses the full-width ％. Matching only "%" left those
    # unspoken -- "٨٧٪" came out as "sab'a wa thamanun" then a bare symbol.
    out = re.sub(r"([\d,]+(?:\.\d+)?)\s?[٪％%]", lambda m: _unit_percent(m, pack), out)
    out = re.sub(
        r"([\d,]+(?:\.\d+)?)\s?(ms|kb|mb|gb|tb|khz|hz)\b",
        _unit,
        out,
        flags=re.IGNORECASE,
    )

    # Abbreviations, whose dot is not a sentence end.
    def _abbrev(match: re.Match[str]) -> str:
        return ABBREVIATIONS[match.group(1).lower()]

    if pack.code == "en":
        out = re.sub(
            r"\b(" + "|".join(re.escape(a) for a in ABBREVIATIONS) + r")\.",
            _abbrev,
            out,
            flags=re.IGNORECASE,
        )

    # Bare numbers left over.
    out = re.sub(
        r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)(?![\w.])",
        lambda m: _decimal(m.group(1).replace(",", "")),
        out,
    )

    # Technical words, matched whole so "api" does not corrupt "rapid".
    def _pronounce(match: re.Match[str]) -> str:
        return PRONUNCIATIONS[match.group(0).lower()]

    out = re.sub(
        r"\b(" + "|".join(re.escape(w) for w in PRONUNCIATIONS) + r")\b",
        _pronounce,
        out,
        flags=re.IGNORECASE,
    )

    return re.sub(r"\s{2,}", " ", out).strip()


# --------------------------------------------------------------------------- #
# graphemes -> visemes
# --------------------------------------------------------------------------- #
def word_to_visemes(word: str) -> list[str]:
    """Mouth shapes for one word, one per sound rather than per letter.

    Delegates to ``scripts`` so this works outside the Latin alphabet. It
    previously matched Latin letters only and returned a single ``neutral``
    for anything else, which meant the avatar's mouth held one position for
    a whole Devanagari, Cyrillic, Arabic, Kana, Hangul or Han word. With
    thirty-five languages that was most of them.
    """
    from .scripts import shapes_for

    shapes = shapes_for(word)
    if not shapes:
        return []

    # Collapse repeats: "gg" in "trigger" is one mouth position, not two.
    collapsed: list[str] = []
    for shape in shapes:
        if not collapsed or collapsed[-1] != shape:
            collapsed.append(shape)
    return collapsed


def visemes_for_words(
    words: list[dict[str, Any]],
    *,
    closed_gap_ms: float = 60.0,
) -> list[dict[str, Any]]:
    """Build a viseme track from prosody, so the mouth follows the timing.

    The previous track spread shapes evenly over the utterance and ignored
    pauses, which left the mouth moving during silence. Here each word's
    shapes fill that word's own duration and the mouth closes in the gaps.
    """
    track: list[dict[str, Any]] = []

    for word in words:
        shapes = word_to_visemes(str(word.get("text", "")))
        if not shapes:
            continue
        start = float(word.get("start_ms", 0.0))
        duration = float(word.get("duration_ms", 0.0))
        if duration <= 0:
            continue
        step = duration / len(shapes)
        for position, shape in enumerate(shapes):
            track.append({"t": round(start + position * step, 1), "shape": shape})

        # A pause means a closed or resting mouth, not a held vowel.
        pause = float(word.get("pause_after_ms", 0.0))
        if pause >= closed_gap_ms:
            track.append({"t": round(start + duration, 1), "shape": "closed"})

    return track
