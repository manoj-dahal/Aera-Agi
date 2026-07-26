# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Writing systems, and the mouth shapes each one implies.

Visemes were derived from Latin letters only. Every other script fell through
to a single ``"neutral"``: a Devanagari, Cyrillic, Arabic, Han, Kana, Hangul
or Thai word produced one shape for the whole word, so the avatar's mouth sat
still while AERA spoke. With one language that was a corner case. With
thirty-five it is most of them.

The approach here is per-script, because scripts differ in what a character
*is*:

alphabets (Latin, Cyrillic, Greek)
    One letter, roughly one sound. Map letters to articulation.

abjads (Arabic, Hebrew)
    Consonants written, short vowels usually not -- but a speaker says them,
    so an unwritten vowel is voiced between consonants. Reading only what is
    on the page gave "שלום" a track with no open mouth at all.

abugidas (Devanagari, Bengali, Gurmukhi, Gujarati, Tamil, Telugu, Kannada,
    Malayalam, Odia, Sinhala)
    A consonant carries an inherent /a/ unless a vowel sign or a virama says
    otherwise. Nine of the ten blocks inherit the same layout from ISCII, so
    one offset table serves them; Sinhala does not and carries its own.

syllabaries (Hiragana, Katakana)
    One character, one mora. The vowel dominates the shape.

Hangul
    Algorithmically composed; decompose to onset, nucleus and coda.

logographs (Han)
    A character is a syllable, but its *reading* is not recoverable from the
    codepoint without a dictionary, and none is bundled. So Han yields jaw
    timing only -- one opening per syllable -- and that limit is stated
    rather than papered over with a plausible-looking guess.

Georgian, Armenian, Ethiopic, Lao, Khmer and Myanmar are recognised but have
no table yet, so they get the same timing-only treatment. ``ALPHABETIC`` and
``TIMING_ONLY`` say which is which, and ``_check_tables`` asserts at import
that the claim matches the implementation.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import Enum

from ..core.logging import get_logger

logger = get_logger("voice.scripts")

#: The five mouth positions the avatar rig exposes, plus a rest pose.
OPEN = "open"
NARROW = "narrow"
CLOSED = "closed"
TEETH = "teeth"
TONGUE = "tongue"
NEUTRAL = "neutral"


class Script(str, Enum):
    """A writing system, as far as lip-sync is concerned."""

    LATIN = "latin"
    CYRILLIC = "cyrillic"
    GREEK = "greek"
    ARABIC = "arabic"
    HEBREW = "hebrew"
    DEVANAGARI = "devanagari"
    BENGALI = "bengali"
    GURMUKHI = "gurmukhi"
    GUJARATI = "gujarati"
    ODIA = "odia"
    TAMIL = "tamil"
    TELUGU = "telugu"
    KANNADA = "kannada"
    MALAYALAM = "malayalam"
    SINHALA = "sinhala"
    THAI = "thai"
    LAO = "lao"
    KHMER = "khmer"
    MYANMAR = "myanmar"
    GEORGIAN = "georgian"
    ARMENIAN = "armenian"
    ETHIOPIC = "ethiopic"
    KANA = "kana"
    HANGUL = "hangul"
    HAN = "han"
    OTHER = "other"


#: Scripts written right to left. The UI needs this; lip-sync does not.
RTL_SCRIPTS = frozenset({Script.ARABIC, Script.HEBREW})

#: Scripts with a real reader: their characters are mapped to articulation
#: individually. Membership is asserted against ``_READERS`` at import, so
#: this cannot drift from what is actually implemented -- it previously
#: claimed Georgian, Armenian, Ethiopic, Lao, Khmer and Myanmar, all of
#: which fell through to jaw timing.
ALPHABETIC = frozenset(
    {
        Script.LATIN, Script.CYRILLIC, Script.GREEK, Script.ARABIC,
        Script.HEBREW, Script.DEVANAGARI, Script.BENGALI, Script.GURMUKHI,
        Script.GUJARATI, Script.ODIA, Script.TAMIL, Script.TELUGU,
        Script.KANNADA, Script.MALAYALAM, Script.SINHALA, Script.THAI,
        Script.HANGUL, Script.KANA,
    }
)

#: Scripts recognised but read as syllable timing only -- one jaw opening per
#: character, no articulation. Han needs a reading dictionary; the others
#: simply have no table yet. Named so a caller can tell the difference
#: instead of discovering it from a flat-looking mouth.
TIMING_ONLY = frozenset(
    {
        Script.HAN, Script.GEORGIAN, Script.ARMENIAN, Script.ETHIOPIC,
        Script.LAO, Script.KHMER, Script.MYANMAR, Script.OTHER,
    }
)

#: Unicode blocks, sorted low to high and asserted non-overlapping at import.
#: Each entry is (first, last, script).
_BLOCKS: tuple[tuple[int, int, Script], ...] = (
    (0x0041, 0x005A, Script.LATIN),
    (0x0061, 0x007A, Script.LATIN),
    (0x00C0, 0x024F, Script.LATIN),   # Latin-1 supplement + extended A/B
    (0x0370, 0x03FF, Script.GREEK),
    (0x0400, 0x052F, Script.CYRILLIC),
    (0x0530, 0x058F, Script.ARMENIAN),
    (0x0590, 0x05FF, Script.HEBREW),
    (0x0600, 0x06FF, Script.ARABIC),
    (0x0750, 0x077F, Script.ARABIC),  # Arabic supplement
    (0x08A0, 0x08FF, Script.ARABIC),  # Arabic extended-A
    (0x0900, 0x097F, Script.DEVANAGARI),
    (0x0980, 0x09FF, Script.BENGALI),
    (0x0A00, 0x0A7F, Script.GURMUKHI),
    (0x0A80, 0x0AFF, Script.GUJARATI),
    (0x0B00, 0x0B7F, Script.ODIA),
    (0x0B80, 0x0BFF, Script.TAMIL),
    (0x0C00, 0x0C7F, Script.TELUGU),
    (0x0C80, 0x0CFF, Script.KANNADA),
    (0x0D00, 0x0D7F, Script.MALAYALAM),
    (0x0D80, 0x0DFF, Script.SINHALA),
    (0x0E00, 0x0E7F, Script.THAI),
    (0x0E80, 0x0EFF, Script.LAO),
    (0x1000, 0x109F, Script.MYANMAR),
    (0x10A0, 0x10FF, Script.GEORGIAN),
    (0x1100, 0x11FF, Script.HANGUL),  # jamo
    (0x1200, 0x139F, Script.ETHIOPIC),
    (0x1780, 0x17FF, Script.KHMER),
    (0x1F00, 0x1FFF, Script.GREEK),   # Greek extended (polytonic)
    (0x3040, 0x30FF, Script.KANA),
    (0x3130, 0x318F, Script.HANGUL),  # compatibility jamo
    (0x31F0, 0x31FF, Script.KANA),    # katakana phonetic extensions
    (0x3400, 0x4DBF, Script.HAN),     # extension A
    (0x4E00, 0x9FFF, Script.HAN),
    (0xA8E0, 0xA8FF, Script.DEVANAGARI),  # Devanagari extended
    (0xAC00, 0xD7AF, Script.HANGUL),  # syllables
    (0xF900, 0xFAFF, Script.HAN),     # compatibility ideographs
    (0xFB50, 0xFDFF, Script.ARABIC),  # presentation forms
)


def script_of(char: str) -> Script | None:
    """The script one character belongs to, or None if it carries no sound.

    Punctuation, digits and whitespace return None so a caller can skip them
    without a second test.
    """
    if not char:
        return None
    code = ord(char)
    for first, last, script in _BLOCKS:
        if first <= code <= last:
            return script
    return None


def detect_script(text: str) -> Script:
    """The dominant script in a string.

    Ties go to the first seen, which keeps the result stable for a given
    input rather than depending on dict ordering.
    """
    counts: dict[Script, int] = {}
    for char in text:
        script = script_of(char)
        if script is not None:
            counts[script] = counts.get(script, 0) + 1
    if not counts:
        return Script.OTHER
    return max(counts, key=lambda s: counts[s])


def runs(text: str) -> list[tuple[Script, str]]:
    """Split into maximal same-script runs, dropping soundless characters.

    Mixed text is normal -- a Hindi sentence quoting an English product name,
    a Japanese line with a Latin acronym -- and each run has to be read by
    its own rules.
    """
    out: list[tuple[Script, str]] = []
    current: Script | None = None
    buffer: list[str] = []
    for char in text:
        script = script_of(char)
        if script is None:
            continue
        if script != current:
            if buffer and current is not None:
                out.append((current, "".join(buffer)))
            current, buffer = script, [char]
        else:
            buffer.append(char)
    if buffer and current is not None:
        out.append((current, "".join(buffer)))
    return out


# --------------------------------------------------------------------------- #
# Latin
# --------------------------------------------------------------------------- #
#: Multi-letter clusters that make one sound. Longest first so "tch" wins
#: over "ch", and checked before single letters.
_LATIN_CLUSTERS: tuple[tuple[str, str], ...] = (
    ("tch", TONGUE), ("sch", NARROW),
    ("th", TONGUE), ("sh", NARROW), ("ch", NARROW), ("ph", TEETH),
    ("wh", NARROW), ("ck", TONGUE), ("ng", TONGUE), ("qu", NARROW),
    ("ee", NARROW), ("ea", OPEN), ("oo", NARROW), ("ou", OPEN),
    ("ow", OPEN), ("ai", OPEN), ("ay", OPEN), ("oa", OPEN),
    ("ie", NARROW), ("ei", NARROW), ("au", OPEN), ("aw", OPEN),
)

_LATIN_SINGLE: dict[str, str] = {
    **dict.fromkeys("aeiou", OPEN),
    **dict.fromkeys("bmp", CLOSED),
    **dict.fromkeys("fv", TEETH),
    **dict.fromkeys("dlnrt", TONGUE),
    **dict.fromkeys("csxz", NARROW),
    **dict.fromkeys("gjk", TONGUE),
    **dict.fromkeys("wy", NARROW),
    "h": OPEN,
    "q": NARROW,
}


def _fold(text: str) -> str:
    """Strip diacritics so "é" reads as "e" rather than falling to neutral.

    Every Latin-script language beyond English needs this: without it
    "français" and "está" lost a sound each.
    """
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _latin(run: str) -> list[str]:
    lowered = _fold(run.lower())
    lowered = "".join(c for c in lowered if c.isalpha())
    if not lowered:
        return []

    # Silent final e: "make", "site", "close" -- but not "the" or "be",
    # where the e is the only vowel sound.
    if len(lowered) > 3 and lowered.endswith("e") and lowered[-2] not in "aeiou":
        lowered = lowered[:-1]

    shapes: list[str] = []
    index = 0
    while index < len(lowered):
        for cluster, shape in _LATIN_CLUSTERS:
            if lowered.startswith(cluster, index):
                shapes.append(shape)
                index += len(cluster)
                break
        else:
            shapes.append(_LATIN_SINGLE.get(lowered[index], NEUTRAL))
            index += 1
    return shapes


# --------------------------------------------------------------------------- #
# Cyrillic and Greek
# --------------------------------------------------------------------------- #
_CYRILLIC: dict[str, str] = {
    "а": OPEN, "я": OPEN, "о": OPEN, "э": OPEN, "е": OPEN, "ё": OPEN,
    "и": NARROW, "ы": NARROW, "у": NARROW, "ю": NARROW, "і": NARROW,
    "ї": NARROW, "й": NARROW, "є": OPEN,
    "б": CLOSED, "м": CLOSED, "п": CLOSED,
    "в": TEETH, "ф": TEETH,
    "д": TONGUE, "л": TONGUE, "н": TONGUE, "р": TONGUE, "т": TONGUE,
    "г": TONGUE, "к": TONGUE, "х": TONGUE, "ґ": TONGUE,
    "ж": NARROW, "з": NARROW, "с": NARROW, "ц": NARROW, "ч": NARROW,
    "ш": NARROW, "щ": NARROW,
    # Hard and soft signs modify the letter before them; they are not sounds.
    "ъ": "", "ь": "",
}

_GREEK: dict[str, str] = {
    "α": OPEN, "ε": OPEN, "ο": OPEN, "ω": OPEN,
    "η": NARROW, "ι": NARROW, "υ": NARROW,
    "β": TEETH, "φ": TEETH,
    "γ": TONGUE, "δ": TONGUE, "θ": TONGUE, "κ": TONGUE, "λ": TONGUE,
    "ν": TONGUE, "ρ": TONGUE, "τ": TONGUE, "χ": TONGUE,
    "μ": CLOSED, "π": CLOSED,
    "ζ": NARROW, "ξ": NARROW, "σ": NARROW, "ς": NARROW, "ψ": NARROW,
}


def _table_reader(table: dict[str, str]):
    def read(run: str) -> list[str]:
        shapes: list[str] = []
        for char in _fold(run.lower()):
            shape = table.get(char)
            if shape:
                shapes.append(shape)
            elif shape == "":
                continue
            elif char.isalpha():
                shapes.append(NEUTRAL)
        return shapes

    return read


# --------------------------------------------------------------------------- #
# Arabic and Hebrew: consonants written, short vowels usually not
# --------------------------------------------------------------------------- #
_ARABIC: dict[str, str] = {
    "ا": OPEN, "أ": OPEN, "إ": OPEN, "آ": OPEN, "ء": OPEN, "ٱ": OPEN,
    "ح": OPEN, "ع": OPEN, "ه": OPEN, "ة": OPEN,
    "ب": CLOSED, "م": CLOSED,
    "ف": TEETH,
    "و": NARROW, "ي": NARROW, "ى": NARROW, "ئ": NARROW, "ؤ": NARROW,
    "ج": NARROW, "ز": NARROW, "س": NARROW, "ش": NARROW, "ص": NARROW,
    "ت": TONGUE, "ث": TONGUE, "خ": TONGUE, "د": TONGUE, "ذ": TONGUE,
    "ر": TONGUE, "ض": TONGUE, "ط": TONGUE, "ظ": TONGUE, "غ": TONGUE,
    "ق": TONGUE, "ك": TONGUE, "ل": TONGUE, "ن": TONGUE,
    # Persian and Urdu additions.
    "پ": CLOSED, "چ": NARROW, "ژ": NARROW, "گ": TONGUE, "ک": TONGUE,
    "ٹ": TONGUE, "ڈ": TONGUE, "ڑ": TONGUE, "ں": TONGUE, "ھ": OPEN,
    "ی": NARROW, "ے": NARROW,
}

#: Arabic short-vowel and gemination marks. Written only in the Qur'an,
#: textbooks and poetry; they are diacritics, not separate mouth positions.
_ARABIC_MARKS = frozenset(chr(c) for c in range(0x064B, 0x0653)) | {"\u0670", "\u0640"}

_HEBREW: dict[str, str] = {
    "א": OPEN, "ה": OPEN, "ע": OPEN,
    "ב": CLOSED, "מ": CLOSED, "ם": CLOSED, "פ": CLOSED, "ף": CLOSED,
    "ו": NARROW, "י": NARROW,
    "ז": NARROW, "ס": NARROW, "צ": NARROW, "ץ": NARROW, "ש": NARROW,
    "ג": TONGUE, "ד": TONGUE, "ח": TONGUE, "ט": TONGUE, "כ": TONGUE,
    "ך": TONGUE, "ל": TONGUE, "נ": TONGUE, "ן": TONGUE, "ק": TONGUE,
    "ר": TONGUE, "ת": TONGUE,
}


#: Letters that already carry a vowel, so no unwritten one is implied after
#: the consonant before them.
_ARABIC_VOWELS = frozenset("اأإآءٱويىئؤےه")
_HEBREW_VOWELS = frozenset("אהועי")


def _abjad(table: dict[str, str], vowels: frozenset[str], skip: frozenset[str]):
    """Read a consonantal script, voicing the vowels it does not write.

    Arabic and Hebrew omit short vowels, but a speaker still says them --
    "שלום" is shalom, two vowels, and reading only the consonants gave a
    track with no open mouth at all. So an unwritten vowel is inserted
    between consonants, the same principle as the Indic inherent vowel.
    """

    def read(run: str) -> list[str]:
        letters = [c for c in run if c not in skip and (c in table or c.isalpha())]
        shapes: list[str] = []
        for index, char in enumerate(letters):
            shapes.append(table.get(char, NEUTRAL))
            if char in vowels:
                continue
            nxt = letters[index + 1] if index + 1 < len(letters) else None
            if nxt is None or nxt in vowels:
                continue
            shapes.append(OPEN)
        return shapes

    return read


_arabic = _abjad(_ARABIC, _ARABIC_VOWELS, _ARABIC_MARKS)
_hebrew = _abjad(_HEBREW, _HEBREW_VOWELS, frozenset())


# --------------------------------------------------------------------------- #
# Indic abugidas: one offset table for nine scripts
# --------------------------------------------------------------------------- #
#: Offsets within an Indic Unicode block. The blocks are laid out in the same
#: order -- vowels at 0x05, consonants from 0x15, vowel signs from 0x3E,
#: virama at 0x4D -- so Devanagari's table reads Bengali, Gujarati, Tamil and
#: the rest without change.
_INDIC_OFFSETS: dict[int, str] = {
    # Independent vowels.
    0x05: OPEN, 0x06: OPEN, 0x07: NARROW, 0x08: NARROW, 0x09: NARROW,
    0x0A: NARROW, 0x0B: TONGUE, 0x0C: TONGUE, 0x0D: OPEN, 0x0E: OPEN,
    0x0F: NARROW, 0x10: OPEN, 0x11: OPEN, 0x12: OPEN, 0x13: OPEN, 0x14: OPEN,
    # Velars and palatals.
    0x15: TONGUE, 0x16: TONGUE, 0x17: TONGUE, 0x18: TONGUE, 0x19: TONGUE,
    0x1A: NARROW, 0x1B: NARROW, 0x1C: NARROW, 0x1D: NARROW, 0x1E: TONGUE,
    # Retroflex and dental.
    0x1F: TONGUE, 0x20: TONGUE, 0x21: TONGUE, 0x22: TONGUE, 0x23: TONGUE,
    0x24: TONGUE, 0x25: TONGUE, 0x26: TONGUE, 0x27: TONGUE, 0x28: TONGUE,
    0x29: TONGUE,
    # Labials.
    0x2A: CLOSED, 0x2B: CLOSED, 0x2C: CLOSED, 0x2D: CLOSED, 0x2E: CLOSED,
    # Approximants and sibilants.
    0x2F: NARROW, 0x30: TONGUE, 0x31: TONGUE, 0x32: TONGUE, 0x33: TONGUE,
    0x34: TONGUE, 0x35: TEETH,
    0x36: NARROW, 0x37: NARROW, 0x38: NARROW, 0x39: OPEN,
    # Dependent vowel signs.
    0x3E: OPEN, 0x3F: NARROW, 0x40: NARROW, 0x41: NARROW, 0x42: NARROW,
    0x43: TONGUE, 0x44: TONGUE, 0x45: OPEN, 0x46: OPEN, 0x47: NARROW,
    0x48: OPEN, 0x49: OPEN, 0x4A: OPEN, 0x4B: OPEN, 0x4C: OPEN,
}

@dataclass(frozen=True)
class _IndicLayout:
    """Where the pieces sit inside one Indic block.

    Nine of the ten blocks share a layout inherited from ISCII, so one table
    serves them. Sinhala does not -- its consonants start at +0x1A and run to
    +0x46, and its vowel signs sit at +0x4F and above, well past where the
    others end. Treating it as isomorphic put every Sinhala consonant outside
    the consonant range, so "සිංහල" produced no vowels at all.
    """

    base: int
    consonants: range
    signs: range
    virama: int
    anusvara: int = 0x02
    #: Whether a word-final inherent vowel is dropped. Indo-Aryan does this
    #: -- Hindi राम is "raam", not "raama" -- but Dravidian and Sinhala do
    #: not: Tamil தமிழ் keeps its final vowel and Sinhala සිංහල ends in "la".
    final_schwa_deletion: bool = True


_STANDARD = dict(consonants=range(0x15, 0x3A), signs=range(0x3E, 0x4D), virama=0x4D)

_INDIC_LAYOUTS: dict[Script, _IndicLayout] = {
    Script.DEVANAGARI: _IndicLayout(0x0900, **_STANDARD),
    Script.BENGALI: _IndicLayout(0x0980, **_STANDARD),
    Script.GURMUKHI: _IndicLayout(0x0A00, **_STANDARD),
    Script.GUJARATI: _IndicLayout(0x0A80, **_STANDARD),
    Script.ODIA: _IndicLayout(0x0B00, **_STANDARD),
    Script.TAMIL: _IndicLayout(0x0B80, **_STANDARD, final_schwa_deletion=False),
    Script.TELUGU: _IndicLayout(0x0C00, **_STANDARD, final_schwa_deletion=False),
    Script.KANNADA: _IndicLayout(0x0C80, **_STANDARD, final_schwa_deletion=False),
    Script.MALAYALAM: _IndicLayout(0x0D00, **_STANDARD, final_schwa_deletion=False),
    Script.SINHALA: _IndicLayout(
        0x0D80,
        consonants=range(0x1A, 0x47),
        signs=range(0x4F, 0x60),
        virama=0x4A,
        final_schwa_deletion=False,
    ),
}


def _indic_reader(layout: _IndicLayout):
    """Read an abugida: a consonant keeps its inherent /a/ unless told not to.

    That inherent vowel is the whole point of the family and the reason a
    letter-per-shape reading is wrong here -- "नमस्ते" is six sounds written
    with four consonants.
    """

    def read(run: str) -> list[str]:
        offsets = [ord(c) - layout.base for c in run]
        shapes: list[str] = []
        consonants_seen = 0
        for index, offset in enumerate(offsets):
            shape = _INDIC_OFFSETS.get(offset)
            if offset in layout.consonants:
                shapes.append(shape or TONGUE)
                consonants_seen += 1
                nxt = offsets[index + 1] if index + 1 < len(offsets) else None
                # A vowel sign or a virama overrides the inherent vowel.
                if (nxt is not None and nxt in layout.signs) or nxt == layout.virama:
                    continue
                if nxt == layout.anusvara:
                    continue
                # Word-final schwa deletion is real in Hindi -- राम is "raam",
                # not "raama" -- but only in a word of more than one
                # syllable. A lone consonant letter is still "ka", so
                # dropping it there made क and क् identical.
                if (
                    index == len(offsets) - 1
                    and consonants_seen > 1
                    and layout.final_schwa_deletion
                ):
                    continue
                shapes.append(OPEN)
            elif offset == layout.anusvara:
                shapes.append(CLOSED)
            elif shape:
                shapes.append(shape)
        return shapes

    return read


# --------------------------------------------------------------------------- #
# Thai
# --------------------------------------------------------------------------- #
_THAI: dict[str, str] = {
    **dict.fromkeys("กขฃคฅฆงจฉชซฌญฎฏฐฑฒณดตถทธนฐ", TONGUE),
    **dict.fromkeys("บปผฝพฟภม", CLOSED),
    **dict.fromkeys("ฝฟ", TEETH),
    **dict.fromkeys("ยรลวฬ", TONGUE),
    **dict.fromkeys("ศษสหฮอ", NARROW),
    **dict.fromkeys("ะัาำ", OPEN),
    **dict.fromkeys("ิีึืุู", NARROW),
    **dict.fromkeys("เแโใไ", OPEN),
}

#: Tone marks and the silencer sit above the letter and change pitch, not
#: mouth shape.
_THAI_MARKS = frozenset("่้๊๋์็ํ")


def _thai(run: str) -> list[str]:
    return [_THAI.get(c, NEUTRAL) for c in run if c not in _THAI_MARKS]


# --------------------------------------------------------------------------- #
# Kana: one character, one mora, vowel dominant
# --------------------------------------------------------------------------- #
_KANA_A = "あかさたなはまやらわがざだばぱアカサタナハマヤラワガザダバパ"
_KANA_I = "いきしちにひみりゐぎじぢびぴイキシチニヒミリヰギジヂビピ"
_KANA_U = "うくすつぬふむゆるぐずづぶぷウクスツヌフムユルグズヅブプ"
_KANA_E = "えけせてねへめれゑげぜでべぺエケセテネヘメレヱゲゼデベペ"
_KANA_O = "おこそとのほもよろをごぞどぼぽオコソトノホモヨロヲゴゾドボポ"
_KANA_LABIAL = "まみむめもばびぶべぼぱぴぷぺぽマミムメモバビブベボパピプペポ"

_KANA: dict[str, str] = {
    **dict.fromkeys(_KANA_A, OPEN),
    **dict.fromkeys(_KANA_I, NARROW),
    **dict.fromkeys(_KANA_U, NARROW),
    **dict.fromkeys(_KANA_E, OPEN),
    **dict.fromkeys(_KANA_O, OPEN),
    # Small kana glide onto the mora before them rather than standing alone.
    **dict.fromkeys("ゃゅょャュョ", NARROW),
    **dict.fromkeys("ぁぃぅぇぉァィゥェォ", NARROW),
    "ん": CLOSED, "ン": CLOSED,
    "っ": NEUTRAL, "ッ": NEUTRAL,
    "ふ": TEETH, "フ": TEETH,
    "ー": OPEN,
}


def _kana(run: str) -> list[str]:
    shapes: list[str] = []
    for char in run:
        if char in _KANA_LABIAL:
            # The lips close for the onset, then open for the vowel.
            shapes.append(CLOSED)
            shapes.append(_KANA.get(char, OPEN))
        else:
            shapes.append(_KANA.get(char, NEUTRAL))
    return shapes


# --------------------------------------------------------------------------- #
# Hangul: composed algorithmically, so decompose it
# --------------------------------------------------------------------------- #
_HANGUL_ONSET = (
    TONGUE, TONGUE, TONGUE, TONGUE, TONGUE, TONGUE, CLOSED, CLOSED, CLOSED,
    NARROW, NARROW, OPEN, NARROW, NARROW, NARROW, TONGUE, TONGUE, CLOSED, OPEN,
)
_HANGUL_NUCLEUS = (
    OPEN, OPEN, OPEN, OPEN, OPEN, OPEN, OPEN, OPEN, OPEN, OPEN, OPEN,
    NARROW, OPEN, NARROW, OPEN, OPEN, NARROW, NARROW, NARROW, NARROW, NARROW,
)
_HANGUL_CODA = (
    "", TONGUE, TONGUE, TONGUE, TONGUE, TONGUE, TONGUE, TONGUE, TONGUE,
    TONGUE, TONGUE, TONGUE, TONGUE, TONGUE, TONGUE, TONGUE, CLOSED, CLOSED,
    CLOSED, NARROW, NARROW, OPEN, NARROW, NARROW, TONGUE, TONGUE, CLOSED, OPEN,
)


def _hangul(run: str) -> list[str]:
    shapes: list[str] = []
    for char in run:
        code = ord(char)
        if not 0xAC00 <= code <= 0xD7A3:
            shapes.append(NEUTRAL)
            continue
        index = code - 0xAC00
        onset, rest = divmod(index, 588)
        nucleus, coda = divmod(rest, 28)
        # ㅇ is silent in the onset; it is a placeholder, not a sound.
        if onset != 11:
            shapes.append(_HANGUL_ONSET[onset])
        shapes.append(_HANGUL_NUCLEUS[nucleus])
        if coda:
            shapes.append(_HANGUL_CODA[coda])
    return shapes


# --------------------------------------------------------------------------- #
# Han: syllable timing only
# --------------------------------------------------------------------------- #
def _han(run: str) -> list[str]:
    """One jaw opening per character, and nothing finer.

    A Han character is reliably one syllable, and every Mandarin syllable has
    a vowel nucleus, so opening the mouth once per character is true. Which
    vowel it is needs a reading dictionary, and none ships with AERA -- so
    this stops at timing instead of guessing a shape that would be wrong most
    of the time.
    """
    shapes: list[str] = []
    for _ in run:
        shapes.append(NEUTRAL)
        shapes.append(OPEN)
    return shapes


def _generic(run: str) -> list[str]:
    """Unknown script: alternate rest and open, one pair per character.

    Says only "a mouth moved here", which is the honest amount to claim.
    """
    return _han(run)


_READERS = {
    Script.LATIN: _latin,
    Script.CYRILLIC: _table_reader(_CYRILLIC),
    Script.GREEK: _table_reader(_GREEK),
    Script.ARABIC: _arabic,
    Script.HEBREW: _hebrew,
    Script.THAI: _thai,
    Script.KANA: _kana,
    Script.HANGUL: _hangul,
    Script.HAN: _han,
    **{script: _indic_reader(layout) for script, layout in _INDIC_LAYOUTS.items()},
}


def _check_tables() -> None:
    """Assert the declared sets match what is implemented.

    ``ALPHABETIC`` claimed Georgian, Armenian, Ethiopic, Lao, Khmer and
    Myanmar had letter-level readers when they fell through to jaw timing.
    Nothing caught it because nothing compared the two. Now it cannot drift.
    """
    for script in ALPHABETIC:
        if script not in _READERS:
            raise RuntimeError(
                f"{script.value} is declared ALPHABETIC but has no reader; "
                f"it would silently fall back to syllable timing"
            )
    overlap = ALPHABETIC & TIMING_ONLY
    if overlap:
        raise RuntimeError(f"scripts in both ALPHABETIC and TIMING_ONLY: {overlap}")
    covered = ALPHABETIC | TIMING_ONLY
    uncovered = {s for s in Script if s not in covered}
    if uncovered:
        raise RuntimeError(
            f"scripts classified as neither alphabetic nor timing-only: "
            f"{sorted(s.value for s in uncovered)}"
        )
    ordered = sorted(_BLOCKS)
    if list(_BLOCKS) != ordered:
        raise RuntimeError("_BLOCKS must be sorted low to high")
    for (_, end, _), (start, _, _) in zip(ordered, ordered[1:], strict=False):
        if end >= start:
            raise RuntimeError(f"_BLOCKS overlap at {hex(start)}")


_check_tables()


def reads_articulation(script: Script) -> bool:
    """Whether this script gets real mouth shapes or only jaw timing.

    A caller rendering an avatar should know which it is getting: timing
    alone still moves the mouth, but it is not lip-sync.
    """
    return script in ALPHABETIC


def shapes_for(text: str) -> list[str]:
    """Mouth shapes for a string in any supported script.

    Mixed-script text is handled run by run, so a Latin acronym inside a
    Devanagari sentence is read as Latin.
    """
    shapes: list[str] = []
    for script, run in runs(text):
        shapes.extend(_READERS.get(script, _generic)(run))
    return shapes
