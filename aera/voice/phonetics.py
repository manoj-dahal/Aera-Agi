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

_ONES = (
    "zero one two three four five six seven eight nine ten eleven twelve "
    "thirteen fourteen fifteen sixteen seventeen eighteen nineteen"
).split()
_TENS = (
    "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
)
_SCALES = ((1_000_000_000, "billion"), (1_000_000, "million"), (1_000, "thousand"))


def say_number(value: int) -> str:
    """Spell an integer the way it is read aloud."""
    if value < 0:
        return f"minus {say_number(-value)}"
    if value < 20:
        return _ONES[value]
    if value < 100:
        tens, ones = divmod(value, 10)
        return _TENS[tens] + (f" {_ONES[ones]}" if ones else "")
    if value < 1000:
        hundreds, rest = divmod(value, 100)
        out = f"{_ONES[hundreds]} hundred"
        return f"{out} and {say_number(rest)}" if rest else out
    for size, name in _SCALES:
        if value >= size:
            count, rest = divmod(value, size)
            out = f"{say_number(count)} {name}"
            return f"{out} {say_number(rest)}" if rest else out
    return str(value)


def _say_decimal(text: str) -> str:
    """"3.5" -> "three point five"; digits after the point are read singly."""
    whole, _, fraction = text.partition(".")
    spoken = say_number(int(whole or 0))
    if fraction:
        digits = " ".join(_ONES[int(d)] for d in fraction if d.isdigit())
        return f"{spoken} point {digits}"
    return spoken


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


def normalise_for_speech(text: str) -> str:
    """Rewrite text into the form it should be read aloud in.

    Runs before synthesis so the engine receives words, not symbols. Order
    matters: URLs first, because they contain dots and slashes that the
    later rules would otherwise mangle.
    """
    if not text or not text.strip():
        return ""

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
        return f"{_say_decimal(amount)} {word}"

    out = re.sub(r"([$£€¥])\s?([\d,]+(?:\.\d+)?)", _currency, out)

    # Times: "3:30" -> "three thirty", "14:05" -> "fourteen oh five".
    def _time(match: re.Match[str]) -> str:
        hour, minute = int(match.group(1)), int(match.group(2))
        if minute == 0:
            spoken = f"{say_number(hour)} o'clock"
        elif minute < 10:
            spoken = f"{say_number(hour)} oh {say_number(minute)}"
        else:
            spoken = f"{say_number(hour)} {say_number(minute)}"
        suffix = match.group(3)
        return f"{spoken} {suffix.upper().replace('M', ' M')}" if suffix else spoken

    out = re.sub(r"\b(\d{1,2}):(\d{2})\s?([ap]m)?\b", _time, out, flags=re.IGNORECASE)

    # Version strings stay as digits but gain spoken dots.
    out = re.sub(
        r"\bv?(\d+)\.(\d+)(?:\.(\d+))?\b",
        lambda m: " point ".join(say_number(int(g)) for g in m.groups() if g),
        out,
    )

    # Numbers with units: "87%" -> "eighty seven percent".
    def _unit(match: re.Match[str]) -> str:
        amount = match.group(1).replace(",", "")
        unit = match.group(2).lower()
        singular, plural = _UNITS[unit]
        value = float(amount)
        return f"{_say_decimal(amount)} {singular if value == 1 else plural}"

    # Two patterns: "%" is not a word character, so a trailing \b after it
    # can never assert and the alternation silently skipped every percentage.
    out = re.sub(r"([\d,]+(?:\.\d+)?)\s?(%)", _unit, out)
    out = re.sub(
        r"([\d,]+(?:\.\d+)?)\s?(ms|kb|mb|gb|tb|khz|hz)\b",
        _unit,
        out,
        flags=re.IGNORECASE,
    )

    # Abbreviations, whose dot is not a sentence end.
    def _abbrev(match: re.Match[str]) -> str:
        return ABBREVIATIONS[match.group(1).lower()]

    out = re.sub(
        r"\b(" + "|".join(re.escape(a) for a in ABBREVIATIONS) + r")\.",
        _abbrev,
        out,
        flags=re.IGNORECASE,
    )

    # Bare numbers left over.
    out = re.sub(
        r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)(?![\w.])",
        lambda m: _say_decimal(m.group(1).replace(",", "")),
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
#: Multi-letter clusters that make one sound. Longest first so "tch" wins
#: over "ch", and checked before single letters.
_CLUSTERS: tuple[tuple[str, str], ...] = (
    ("tch", "tongue"), ("sch", "narrow"),
    ("th", "tongue"), ("sh", "narrow"), ("ch", "narrow"), ("ph", "teeth"),
    ("wh", "narrow"), ("ck", "tongue"), ("ng", "tongue"), ("qu", "narrow"),
    ("ee", "narrow"), ("ea", "open"), ("oo", "narrow"), ("ou", "open"),
    ("ow", "open"), ("ai", "open"), ("ay", "open"), ("oa", "open"),
    ("ie", "narrow"), ("ei", "narrow"), ("au", "open"), ("aw", "open"),
)

_SINGLE: dict[str, str] = {
    **dict.fromkeys("aeiou", "open"),
    **dict.fromkeys("bmp", "closed"),
    **dict.fromkeys("fv", "teeth"),
    **dict.fromkeys("dlnrt", "tongue"),
    **dict.fromkeys("csxz", "narrow"),
    **dict.fromkeys("gjk", "tongue"),
    **dict.fromkeys("wy", "narrow"),
    "h": "open",
    "q": "narrow",
}


def word_to_visemes(word: str) -> list[str]:
    """Mouth shapes for one word, one per sound rather than per letter.

    Handles clusters and drops the silent final e, so "make" gives three
    shapes instead of four and does not animate a letter nobody says.
    """
    lowered = "".join(c for c in word.lower() if c.isalpha())
    if not lowered:
        return []

    # Silent final e: "make", "site", "close" -- but not "the" or "be",
    # where the e is the only vowel sound.
    if len(lowered) > 3 and lowered.endswith("e") and lowered[-2] not in "aeiou":
        lowered = lowered[:-1]

    shapes: list[str] = []
    index = 0
    while index < len(lowered):
        for cluster, shape in _CLUSTERS:
            if lowered.startswith(cluster, index):
                shapes.append(shape)
                index += len(cluster)
                break
        else:
            shapes.append(_SINGLE.get(lowered[index], "neutral"))
            index += 1

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
