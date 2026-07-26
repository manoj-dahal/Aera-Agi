"""Singing: the lyrics and the rhythm of a song.

Speech and song are not the same signal, and the prosody layer in
``expression.py`` cannot be reused for one by relabelling the other:

*Speech pitch is a contour; sung pitch is quantised.* A spoken sentence
glides continuously and lands wherever it lands. A sung note sits on a scale
degree and holds there. ``prosody_for`` multiplies a persona's pitch by a
smooth ramp, which is right for speech and wrong for melody.

*Speech timing follows stress; sung timing follows the meter.* In speech a
content word is simply longer than a function word. In song a syllable
occupies a defined fraction of a bar, and the bar does not stretch to
accommodate it -- the syllable is what bends.

*The unit is the syllable, not the word.* "Everything" is one word and four
notes. Nothing else in the voice engine counts syllables, and word-level
timing cannot be subdivided after the fact without knowing where the
boundaries are.

*A syllable can span several notes.* Melisma -- one vowel carried across a
run -- has no equivalent in speech at all.

So this module supplies what singing needs and speech does not: syllable
counting, metrical scansion, rhyme, beats and bars, scales, and the mapping
from a lyric's emotion to a key and a tempo. It leans on ``scripts.py``,
which already knows that a Han character is one syllable, a kana is one mora
and a Hangul block is one syllable -- the same structure lyrics are counted
in.

What this does *not* do is claim to compose. ``sing()`` returns a note plan:
which syllable sounds, at what pitch, starting when, for how long. Rendering
that plan to audio goes through the formant vocoder in ``personas.py``, with
the same limitation stated there -- it produces pitched, articulated tone,
not a human voice.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..core.logging import get_logger
from .engine import Emotion
from .scripts import Script, detect_script

logger = get_logger("voice.music")

#: A word, for lyric purposes. ``\w`` excludes combining marks, so a plain
#: ``[^\W\d_]+`` cuts Devanagari "नमस्ते" into "नमस" and "त" at the virama
#: and Thai at its vowel signs -- the same defect that broke word boundaries
#: in the language packs. Marks are explicitly allowed to continue a word.
_WORD = re.compile(r"[^\W\d_][\w\u0300-\u1AFF\u1DC0-\u1DFF\u20D0-\u20F0]*", re.UNICODE)


def words_in(text: str) -> list[str]:
    """The words of a lyric line, keeping combining marks attached."""
    return [m.group() for m in _WORD.finditer(text or "")]


# --------------------------------------------------------------------------- #
# syllables
# --------------------------------------------------------------------------- #
#: Vowel letters per Latin-script language. English "y" is a vowel in
#: "rhythm" and a consonant in "yes"; treating it as neither loses a
#: syllable, so it counts only when no other vowel is present in the word.
_LATIN_VOWELS = "aeiou"

#: Endings whose "e" is silent in English: "make" is one syllable, "maker"
#: two. Not universal -- French "e" is often silent too but Spanish and
#: Italian always sound it, so this is gated by language.
_SILENT_E_LANGUAGES = frozenset({"en", "fr"})

#: Suffixes that add a syllable despite ending in a silent-looking e.
_SYLLABIC_ENDINGS = ("le", "re", "ble", "cle", "dle", "fle", "gle", "kle", "ple", "tle", "zle")


def _latin_syllables(word: str, language: str) -> int:
    """Count syllables in a Latin-script word by vowel groups.

    A vowel group is one nucleus: "beat" has two vowel letters and one
    syllable. This is the standard heuristic and it is not perfect, but it
    is right far more often than counting letters or vowels individually.

    Three corrections on top of the plain rule, each for a case the plain
    rule gets wrong:

    * "y" is a vowel when no other vowel is adjacent -- "rhythm" is two
      syllables and has no a/e/i/o/u at all, and "everything" is four, not
      three, because of its "y".
    * Some adjacent vowel pairs are two nuclei, not one: "po-et", "cha-os",
      "cre-ate". A short list of hiatus pairs covers the common ones.
    * A final "e" is silent in English and French but sounded in Spanish
      and Italian, so that rule is gated by language.
    """
    from .scripts import _fold

    cleaned = "".join(c for c in _fold(word.lower()) if c.isalpha())
    if not cleaned:
        return 0

    # Treat y as a vowel: it carries the nucleus in "rhythm", "myth",
    # "everything" and "happy". Counting it always is closer than never.
    groups = len(re.findall(rf"[{_LATIN_VOWELS}y]+", cleaned))

    # Hiatus: a written vowel pair that is two spoken syllables. Applied
    # per-group, because "-tion" and "-tial" contain "io"/"ia" inside a
    # single /ʃən/ sound and must not be split -- checking the raw string
    # for "io" turned "nation" into three syllables.
    for match in re.finditer(rf"[{_LATIN_VOWELS}y]{{2,}}", cleaned):
        group = match.group()
        before = cleaned[max(0, match.start() - 1):match.start()]
        if before in ("t", "s", "c") and group.startswith(("io", "ia", "ie")):
            continue  # nation, mission, special, patient
        groups += sum(1 for pair in _HIATUS if pair in group)

    if language in _SILENT_E_LANGUAGES and cleaned.endswith("e") and groups > 1:
        # "make" -> 1, but "little" keeps its final syllable and "the"
        # never had a second one to lose.
        if not cleaned.endswith(_SYLLABIC_ENDINGS):
            groups -= 1

    # A syllabic consonant: "rhythm", "prism", "chasm" end in a consonant
    # cluster whose final m/l/n carries its own beat. A singer gives it a
    # note, so it counts.
    if re.search(r"[bcdfghjklmnpqrstvwxz][lmn]$", cleaned):
        groups += 1

    return max(1, groups)


#: Vowel pairs that are reliably two syllables rather than one glide.
#: "ea" is deliberately absent: it is one sound in "beat" and two in
#: "create", and spelling alone cannot separate those.
_HIATUS = ("oe", "io", "ia", "eo", "ua", "uo", "iu", "yi", "ao", "ii")


#: Kana that attach to the mora before them rather than forming their own.
#: ゃゅょ glide onto the preceding consonant (きゃ is one mora, not two) and
#: ー lengthens it. っ is a mora in strict counting but is silent, so it is
#: excluded: a singer does not give it a note.
_KANA_ATTACHED = frozenset("ゃゅょャュョぁぃぅぇぉァィゥェォーっッ")


_INDIC_SCRIPTS = frozenset(
    {
        Script.DEVANAGARI, Script.BENGALI, Script.GURMUKHI, Script.GUJARATI,
        Script.ODIA, Script.TAMIL, Script.TELUGU, Script.KANNADA,
        Script.MALAYALAM, Script.SINHALA,
    }
)

_VOWEL_PATTERNS = {
    Script.CYRILLIC: r"[аеёиоуыэюяіїєAEЁИОУЫЭЮЯ]+",
    Script.GREEK: r"[αεηιοωυάέήίόώύ]+",
}

#: Where the consonants and the vowel-killer sit in each Indic block, reused
#: from the viseme layer so the two cannot disagree about what a syllable is.
_INDIC_BASES: dict[Script, tuple[int, range, int]] = {}


def _init_indic() -> None:
    from .scripts import _INDIC_LAYOUTS

    for script, layout in _INDIC_LAYOUTS.items():
        _INDIC_BASES[script] = (layout.base, layout.consonants, layout.virama)


_init_indic()


def syllables_in(text: str) -> int:
    """How many syllables a line of lyrics has, in any supported script.

    This is the count a singer needs: one note per syllable is the default,
    and everything about fitting words to a bar depends on getting it right.

    Defined as the number of pieces ``syllabify`` produces, so the count and
    the split cannot disagree. They did, in fourteen of the thirty-five
    languages -- Arabic said seven and split into eight, Malayalam said
    eight and split into twelve -- and it is the split that decides how many
    notes a word gets, so a separate counter was just a second opinion
    nothing consulted.
    """
    return sum(len(syllabify(word)) for word in words_in(text))


def syllabify(word: str) -> list[str]:
    """Split one word into its syllables, for aligning lyrics to notes.

    Latin words are split before the onset consonant of each nucleus, which
    is the rule a singer applies by ear: "won-der-ful", "e-ver-y-thing".
    Non-Latin scripts are split by their own unit -- a Han character, a
    kana mora, a Hangul block, an Indic consonant cluster.
    """
    script = detect_script(word)

    if script is Script.HAN:
        return list(word)
    if script is Script.HANGUL:
        return [c for c in word if 0xAC00 <= ord(c) <= 0xD7A3] or [word]
    if script is Script.KANA:
        out: list[str] = []
        for char in word:
            if char in _KANA_ATTACHED and out:
                out[-1] += char
            else:
                out.append(char)
        return out or [word]
    if script in _INDIC_SCRIPTS:
        return _split_indic(script, word)
    if script in (Script.CYRILLIC, Script.GREEK):
        return _split_by_nucleus(word, _VOWEL_PATTERNS[script])
    if script is Script.THAI:
        return _split_by_nucleus(word, r"[\u0E30-\u0E3A\u0E40-\u0E4C]+")
    if script in (Script.ARABIC, Script.HEBREW):
        return _split_abjad(word)
    if script is not Script.LATIN:
        # No splitter for this script; keep the word whole rather than
        # cutting it somewhere arbitrary.
        return [word] if word else []

    return _split_latin(word)


def _split_by_nucleus(word: str, vowels: str) -> list[str]:
    """Split a word before the consonants leading into each vowel group.

    Used for Cyrillic, Greek and Thai. Without this a Russian word came back
    whole and "утреннем" -- three syllables -- was sung on one note, because
    the counter knew about its vowels and the splitter did not.
    """
    spans = [m.span() for m in re.finditer(vowels, word, re.IGNORECASE)]
    if len(spans) < 2:
        return [word] if word else []

    cuts: list[int] = []
    for (_, end), (next_start, _) in zip(spans, spans[1:], strict=False):
        gap = next_start - end
        cut = next_start if gap <= 0 else end + max(0, gap - 1)
        cuts.append(max(cut, (cuts[-1] + 1) if cuts else 1))

    pieces: list[str] = []
    previous = 0
    for cut in cuts:
        if cut > previous:
            pieces.append(word[previous:cut])
            previous = cut
    pieces.append(word[previous:])
    return [p for p in pieces if p] or [word]


def _split_abjad(word: str) -> list[str]:
    """Split Arabic or Hebrew into consonant-plus-vowel pairs.

    An abjad writes consonants and leaves most short vowels out, so a
    syllable is a consonant and whatever follows it. The counter already
    treats it that way; the splitter has to agree or the note count is
    wrong.
    """
    letters = [c for c in word if c.isalpha()]
    if len(letters) < 2:
        return [word] if word else []
    return ["".join(letters[i:i + 2]) for i in range(0, len(letters), 2)]


def _split_indic(script: Script, word: str) -> list[str]:
    """Break an abugida word at each vowel-bearing consonant."""
    base, consonants, virama = _INDIC_BASES[script]
    chunks: list[str] = []
    current = ""
    pending_virama = False
    for char in word:
        offset = ord(char) - base
        if offset in consonants and current and not pending_virama:
            chunks.append(current)
            current = char
        else:
            current += char
        pending_virama = offset == virama
    if current:
        chunks.append(current)
    return chunks or [word]


def _split_latin(word: str) -> list[str]:
    """Split a Latin word into syllables at consonant onsets.

    The result must have exactly ``_latin_syllables`` pieces: the count and
    the split are two views of one fact, and letting them disagree is how
    a lyric ends up with four notes for a three-note word. They drifted on
    "poet", "radio", "rhythm" and "crying" before this was enforced, so the
    nuclei are found with the same rules the counter uses and the outcome
    is checked against it.
    """
    if not word:
        return []
    expected = _latin_syllables(word, "en")
    if expected <= 1:
        return [word]

    lowered = word.lower()
    nuclei = _nuclei(lowered)
    if len(nuclei) < 2:
        # The count says several syllables but only one nucleus was found:
        # a syllabic consonant, as in "rhythm". Cut before it.
        match = re.search(r"([bcdfghjklmnpqrstvwxz])([lmn])$", lowered)
        if match and expected == 2:
            return [word[: match.start(1)], word[match.start(1):]]
        return [word]

    cuts: list[int] = []
    for (_, end), (next_start, _) in zip(nuclei, nuclei[1:], strict=False):
        gap = next_start - end
        if gap <= 0:
            cut = next_start          # hiatus: "po-et", "cry-ing"
        elif gap == 1:
            cut = end                 # single consonant leads the next one
        else:
            cut = end + gap // 2      # split the cluster
        cuts.append(max(cut, (cuts[-1] + 1) if cuts else 1))

    pieces: list[str] = []
    previous = 0
    for cut in cuts:
        if cut > previous:
            pieces.append(word[previous:cut])
            previous = cut
    pieces.append(word[previous:])
    return [p for p in pieces if p] or [word]


def _nuclei(lowered: str) -> list[tuple[int, int]]:
    """Vowel-group spans, with hiatus pairs split into separate nuclei.

    ``_latin_syllables`` counts "oe" in "poet" and "yi" in "crying" as two
    syllables; the splitter has to see them as two nuclei or it produces
    fewer pieces than the count promised.
    """
    spans: list[tuple[int, int]] = []
    for match in re.finditer(rf"[{_LATIN_VOWELS}y]{{1,}}", lowered):
        start, end = match.span()
        group = match.group()
        before = lowered[max(0, start - 1):start]
        # -tion, -sion, -cial: one sound, never split.
        if before in ("t", "s", "c") and group.startswith(("io", "ia", "ie")):
            spans.append((start, end))
            continue
        split_at = None
        for pair in _HIATUS:
            index = group.find(pair)
            if index >= 0:
                split_at = start + index + 1
                break
        if split_at is not None and start < split_at < end:
            spans.append((start, split_at))
            spans.append((split_at, end))
        else:
            spans.append((start, end))
    return spans


# --------------------------------------------------------------------------- #
# metre and rhyme
# --------------------------------------------------------------------------- #
class Foot(str, Enum):
    """A metrical foot, named for the stress pattern it repeats."""

    IAMB = "iamb"            # da-DUM: "the CLOCK"
    TROCHEE = "trochee"      # DUM-da: "TIger"
    ANAPEST = "anapest"      # da-da-DUM: "in the NIGHT"
    DACTYL = "dactyl"        # DUM-da-da: "MERrily"
    SPONDEE = "spondee"      # DUM-DUM
    FREE = "free"            # no repeating pattern


#: How many syllables each foot spans.
_FOOT_LENGTH = {
    Foot.IAMB: 2, Foot.TROCHEE: 2, Foot.SPONDEE: 2,
    Foot.ANAPEST: 3, Foot.DACTYL: 3, Foot.FREE: 0,
}

#: The stress pattern each foot repeats, as (weak=0, strong=1).
_FOOT_PATTERN = {
    Foot.IAMB: (0, 1),
    Foot.TROCHEE: (1, 0),
    Foot.ANAPEST: (0, 0, 1),
    Foot.DACTYL: (1, 0, 0),
    Foot.SPONDEE: (1, 1),
}

#: Line lengths, by number of feet. The names a reader of poetry expects.
_METRE_NAMES = {
    1: "monometer", 2: "dimeter", 3: "trimeter", 4: "tetrameter",
    5: "pentameter", 6: "hexameter", 7: "heptameter", 8: "octameter",
}


@dataclass(frozen=True)
class Scansion:
    """The metrical reading of one line."""

    syllables: int
    #: 1 for a stressed syllable, 0 for an unstressed one.
    stresses: tuple[int, ...]
    foot: Foot
    feet: int

    @property
    def name(self) -> str:
        """"iambic pentameter", or "free verse" when nothing repeats."""
        if self.foot is Foot.FREE:
            return "free verse"
        adjective = {
            Foot.IAMB: "iambic", Foot.TROCHEE: "trochaic",
            Foot.ANAPEST: "anapestic", Foot.DACTYL: "dactylic",
            Foot.SPONDEE: "spondaic",
        }[self.foot]
        length = _METRE_NAMES.get(self.feet, f"{self.feet}-foot")
        return f"{adjective} {length}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "syllables": self.syllables,
            "stresses": list(self.stresses),
            "foot": self.foot.value,
            "feet": self.feet,
            "name": self.name,
        }


def stress_pattern(line: str) -> tuple[int, ...]:
    """Which syllables of a line are stressed.

    Content words take stress, function words do not -- the same distinction
    ``prosody_for`` uses for speech. Within a polysyllabic word the first
    syllable is stressed, which is right for the large majority of English
    and wrong for a minority it is not worth a dictionary to catch.
    """
    from .expression import _FUNCTION_WORDS

    out: list[int] = []
    for token in words_in(line):
        pieces = syllabify(token)
        content = token.lower() not in _FUNCTION_WORDS
        for index in range(len(pieces)):
            out.append(1 if (content and index == 0) else 0)
    return tuple(out)


def scan(line: str) -> Scansion:
    """Read the metre of one line of verse.

    Tries each foot and keeps the one whose repeating pattern best matches
    the line's actual stresses. A line that matches nothing is free verse,
    reported as such rather than forced into the nearest label.
    """
    stresses = stress_pattern(line)
    if not stresses:
        return Scansion(0, (), Foot.FREE, 0)

    best_foot, best_score = Foot.FREE, 0.0
    for foot, pattern in _FOOT_PATTERN.items():
        matches = sum(
            1
            for index, value in enumerate(stresses)
            if value == pattern[index % len(pattern)]
        )
        score = matches / len(stresses)
        if score > best_score:
            best_foot, best_score = foot, score

    # Below three quarters agreement the "pattern" is coincidence.
    if best_score < 0.75:
        return Scansion(len(stresses), stresses, Foot.FREE, 0)

    feet = len(stresses) // _FOOT_LENGTH[best_foot]
    return Scansion(len(stresses), stresses, best_foot, feet)


def rhyme_key(word: str) -> str:
    """The part of a word that has to match for a rhyme.

    A rhyme is the last stressed vowel and everything after it: "nation"
    and "station" rhyme on "ation". Spelling-based, so it catches the
    ordinary cases and misses eye-rhymes and "love"/"move" -- which is the
    same limit a reader has without a pronunciation dictionary.
    """
    from .scripts import _fold

    cleaned = "".join(c for c in _fold(word.lower()) if c.isalpha())
    if not cleaned:
        return ""

    matches = list(re.finditer(rf"[{_LATIN_VOWELS}y]+", cleaned))
    if not matches:
        return cleaned

    start = matches[-1].start()
    # A final silent "e" is not a rhyme on its own: "fire" and "desire"
    # both reduced to "e", which would rhyme them with "the" and "be" and
    # with each other for the wrong reason. Step back to the vowel that is
    # actually sounded.
    if len(matches) > 1 and cleaned.endswith("e") and start == len(cleaned) - 1:
        start = matches[-2].start()

    key = cleaned[start:]
    # "time" and "rhyme" rhyme; "y" and "i" are the same vowel here and
    # only the spelling differs. Folding y to i catches that pair and the
    # "-ys"/"-ies" plurals without merging anything that does not rhyme.
    key = key.replace("y", "i")
    # A word-final "gh" is silent: "high" rhymes with "sky", not with
    # nothing. Only at the end, so "night" keeps its "ight" and still
    # rhymes with "light" rather than collapsing to "it".
    if key.endswith("gh"):
        key = key[:-2]
    return key


def rhyme_scheme(lines: list[str]) -> str:
    """Label a stanza's rhyme scheme: "ABAB", "AABB", "AAAA".

    Lines that rhyme get the same letter. A line rhyming with nothing gets
    its own, so an unrhymed stanza reads "ABCD" rather than looking like a
    failure.
    """
    endings = []
    for line in lines:
        words = words_in(line)
        endings.append(rhyme_key(words[-1]) if words else "")

    labels: dict[str, str] = {}
    out: list[str] = []
    for ending in endings:
        if not ending:
            out.append("-")
            continue
        if ending not in labels:
            labels[ending] = chr(ord("A") + len(labels))
        out.append(labels[ending])
    return "".join(out)


# --------------------------------------------------------------------------- #
# rhythm
# --------------------------------------------------------------------------- #
class NoteValue(float, Enum):
    """Note durations, as a fraction of a whole note."""

    WHOLE = 1.0
    HALF = 0.5
    QUARTER = 0.25
    EIGHTH = 0.125
    SIXTEENTH = 0.0625
    #: Dotted notes are half again as long.
    DOTTED_HALF = 0.75
    DOTTED_QUARTER = 0.375
    DOTTED_EIGHTH = 0.1875
    #: A triplet eighth: three in the space of two.
    TRIPLET_EIGHTH = 1.0 / 12.0


@dataclass(frozen=True)
class TimeSignature:
    """Beats per bar, and which note value gets the beat."""

    beats: int = 4
    unit: int = 4

    def __post_init__(self) -> None:
        if self.beats < 1:
            raise ValueError("a bar needs at least one beat")
        if self.unit not in (1, 2, 4, 8, 16):
            raise ValueError(f"unusable beat unit: {self.unit}")

    @property
    def bar_whole_notes(self) -> float:
        """How much of a whole note fits in one bar."""
        return self.beats / self.unit

    @property
    def is_compound(self) -> bool:
        """6/8, 9/8, 12/8: the beat subdivides in three, not two."""
        return self.unit == 8 and self.beats % 3 == 0

    def __str__(self) -> str:
        return f"{self.beats}/{self.unit}"


#: The common time signatures, so a caller can name one instead of
#: constructing it.
COMMON_TIME = TimeSignature(4, 4)
WALTZ_TIME = TimeSignature(3, 4)
CUT_TIME = TimeSignature(2, 2)
COMPOUND_TIME = TimeSignature(6, 8)

#: Traditional tempo markings, in beats per minute. Ranges collapsed to a
#: representative value; a caller wanting exactness passes a number.
TEMPO_MARKS: dict[str, int] = {
    "grave": 40, "largo": 50, "adagio": 70, "andante": 92,
    "moderato": 112, "allegro": 138, "vivace": 166, "presto": 184,
}


@dataclass(frozen=True)
class Tempo:
    """How fast, in beats per minute."""

    bpm: float = 100.0

    def __post_init__(self) -> None:
        if not 20.0 <= self.bpm <= 300.0:
            raise ValueError(f"{self.bpm} bpm is outside anything singable")

    @property
    def beat_ms(self) -> float:
        return 60_000.0 / self.bpm

    def whole_note_ms(self, signature: TimeSignature) -> float:
        """A whole note lasts as many beats as the unit implies."""
        return self.beat_ms * signature.unit

    def note_ms(self, value: NoteValue | float, signature: TimeSignature) -> float:
        return self.whole_note_ms(signature) * float(value)

    def bar_ms(self, signature: TimeSignature) -> float:
        return self.beat_ms * signature.beats

    @classmethod
    def named(cls, mark: str) -> Tempo:
        """A tempo from its Italian marking."""
        key = mark.strip().lower()
        if key not in TEMPO_MARKS:
            raise KeyError(f"unknown tempo mark {mark!r}; known: {sorted(TEMPO_MARKS)}")
        return cls(float(TEMPO_MARKS[key]))

    def mark(self) -> str:
        """The closest traditional marking to this tempo."""
        return min(TEMPO_MARKS, key=lambda name: abs(TEMPO_MARKS[name] - self.bpm))


# --------------------------------------------------------------------------- #
# pitch
# --------------------------------------------------------------------------- #
#: Semitone steps from the tonic, for each scale. A singer needs the shape,
#: not the theory.
SCALES: dict[str, tuple[int, ...]] = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "natural_minor": (0, 2, 3, 5, 7, 8, 10),
    "harmonic_minor": (0, 2, 3, 5, 7, 8, 11),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "phrygian": (0, 1, 3, 5, 7, 8, 10),
    "lydian": (0, 2, 4, 6, 7, 9, 11),
    "mixolydian": (0, 2, 4, 5, 7, 9, 10),
    "major_pentatonic": (0, 2, 4, 7, 9),
    "minor_pentatonic": (0, 3, 5, 7, 10),
    "blues": (0, 3, 5, 6, 7, 10),
    # Used across South Asia and the Middle East; included because the
    # language packs cover those regions and a major scale would be wrong.
    "bhairav": (0, 1, 4, 5, 7, 8, 11),
    "hijaz": (0, 1, 4, 5, 7, 8, 10),
}

_NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def midi_to_hz(midi: float) -> float:
    """Concert pitch: A4 = MIDI 69 = 440 Hz."""
    return 440.0 * (2.0 ** ((midi - 69.0) / 12.0))


def note_name(midi: int) -> str:
    """"A4", "C#5" -- the name a musician would write."""
    return f"{_NOTE_NAMES[midi % 12]}{midi // 12 - 1}"


def name_to_midi(name: str) -> int:
    """Parse "A4" or "C#5" back to a MIDI number."""
    match = re.fullmatch(r"([A-Ga-g])([#b]?)(-?\d+)", name.strip())
    if not match:
        raise ValueError(f"not a note name: {name!r}")
    letter, accidental, octave = match.groups()
    semitone = _NOTE_NAMES.index(letter.upper())
    if accidental == "#":
        semitone += 1
    elif accidental == "b":
        semitone -= 1
    return semitone + (int(octave) + 1) * 12


def scale_degrees(tonic: int, scale: str, count: int) -> list[int]:
    """MIDI notes for the first ``count`` degrees of a scale, ascending."""
    if scale not in SCALES:
        raise KeyError(f"unknown scale {scale!r}; known: {sorted(SCALES)}")
    steps = SCALES[scale]
    return [
        tonic + steps[index % len(steps)] + 12 * (index // len(steps))
        for index in range(count)
    ]


# --------------------------------------------------------------------------- #
# emotion -> music
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class MusicalSetting:
    """The tempo, scale and articulation an emotion implies.

    These are conventions, not laws -- a fast minor key is not automatically
    sad. They encode what a listener expects by default, which is what a
    generator needs when nothing else has been specified.
    """

    tempo: Tempo
    scale: str
    signature: TimeSignature
    #: How much a note is held of its nominal length. Staccato is short.
    articulation: float
    #: Depth of pitch wobble, as a fraction of a semitone.
    vibrato: float
    #: Where the melody sits, as semitones from the persona's comfortable centre.
    register: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "bpm": self.tempo.bpm,
            "tempo_mark": self.tempo.mark(),
            "scale": self.scale,
            "time_signature": str(self.signature),
            "articulation": self.articulation,
            "vibrato": self.vibrato,
            "register": self.register,
        }


MUSIC_FOR_EMOTION: dict[Emotion, MusicalSetting] = {
    Emotion.EXCITED: MusicalSetting(Tempo(152), "major", COMMON_TIME, 0.92, 0.35, 4),
    Emotion.HAPPY: MusicalSetting(Tempo(126), "major_pentatonic", COMMON_TIME, 0.88, 0.25, 2),
    Emotion.CONFIDENT: MusicalSetting(Tempo(112), "mixolydian", COMMON_TIME, 0.95, 0.18, 0),
    Emotion.CURIOUS: MusicalSetting(Tempo(104), "lydian", WALTZ_TIME, 0.82, 0.22, 1),
    Emotion.NEUTRAL: MusicalSetting(Tempo(100), "major", COMMON_TIME, 0.85, 0.15, 0),
    Emotion.CALM: MusicalSetting(Tempo(74), "major", COMPOUND_TIME, 0.96, 0.12, -2),
    Emotion.CONCERNED: MusicalSetting(Tempo(96), "dorian", COMMON_TIME, 0.78, 0.28, -1),
    Emotion.SERIOUS: MusicalSetting(Tempo(84), "harmonic_minor", COMMON_TIME, 0.9, 0.2, -3),
    Emotion.SAD: MusicalSetting(Tempo(62), "natural_minor", WALTZ_TIME, 0.98, 0.3, -5),
}


def setting_for(emotion: Emotion) -> MusicalSetting:
    return MUSIC_FOR_EMOTION.get(emotion, MUSIC_FOR_EMOTION[Emotion.NEUTRAL])


# --------------------------------------------------------------------------- #
# song structure
# --------------------------------------------------------------------------- #
class SectionKind(str, Enum):
    VERSE = "verse"
    CHORUS = "chorus"
    BRIDGE = "bridge"
    REFRAIN = "refrain"


@dataclass
class Section:
    """One labelled block of a lyric."""

    kind: SectionKind
    lines: list[str]
    index: int = 0

    @property
    def syllables(self) -> int:
        return sum(syllables_in(line) for line in self.lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "index": self.index,
            "lines": list(self.lines),
            "syllables": self.syllables,
            "rhyme_scheme": rhyme_scheme(self.lines),
        }


def _normalise_line(line: str) -> str:
    return re.sub(r"[^\w\s]", "", line.lower(), flags=re.UNICODE).strip()


def sections_of(lyrics: str) -> list[Section]:
    """Split a lyric into verses and choruses.

    Blank lines separate blocks. A block that appears more than once is the
    chorus -- repetition is what makes a chorus a chorus, and it is the one
    structural cue available without the music. A single repeated line
    inside verses is a refrain. Everything unrepeated is a verse, except a
    lone odd-length block late in the song, which is where a bridge sits.
    """
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw in (lyrics or "").splitlines():
        if raw.strip():
            current.append(raw.strip())
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    if not blocks:
        return []

    fingerprints = ["\n".join(_normalise_line(line) for line in block) for block in blocks]
    counts: dict[str, int] = {}
    for print_ in fingerprints:
        counts[print_] = counts.get(print_, 0) + 1

    # Repetition alone does not make a chorus: in verse/chorus/verse/chorus
    # every block repeats, and labelling all four "chorus" said nothing.
    # The chorus is the repeated block that recurs *most*, and where several
    # tie, the one that is not the opening block -- a song almost always
    # opens on a verse.
    repeated = {p: n for p, n in counts.items() if n > 1}
    chorus_print: str | None = None
    if repeated:
        most = max(repeated.values())
        candidates = [p for p, n in repeated.items() if n == most]
        chorus_print = next(
            (p for p in candidates if p != fingerprints[0]), candidates[0]
        )

    sections: list[Section] = []
    numbering: dict[SectionKind, int] = {}
    for block, print_ in zip(blocks, fingerprints, strict=True):
        if print_ == chorus_print:
            kind = SectionKind.CHORUS
        elif len(block) == 1:
            kind = SectionKind.REFRAIN
        else:
            kind = SectionKind.VERSE
        numbering[kind] = numbering.get(kind, 0) + 1
        sections.append(Section(kind, block, numbering[kind]))

    # A bridge is the odd one out: a single block, late in the song, that
    # is shaped unlike the verses around it. Length alone is not the signal
    # -- "shorter than the others, after a chorus" relabelled every verse
    # in a plain verse/chorus/verse/chorus song, because all its verses are
    # short and all but the first follow a chorus.
    verses = [s for s in sections if s.kind is SectionKind.VERSE]
    if len(verses) > 2:
        typical = sorted(len(s.lines) for s in verses)[len(verses) // 2]
        seen_chorus = False
        for position, section in enumerate(sections):
            if section.kind is SectionKind.CHORUS:
                seen_chorus = True
                continue
            if (
                section.kind is SectionKind.VERSE
                and seen_chorus
                and len(section.lines) != typical
                and position >= len(sections) // 2
            ):
                section.kind = SectionKind.BRIDGE
                break  # a song has one bridge
    return sections


# --------------------------------------------------------------------------- #
# the note plan
# --------------------------------------------------------------------------- #
@dataclass
class SungNote:
    """One syllable, sung: what, how high, when, how long."""

    syllable: str
    midi: int
    start_ms: float
    duration_ms: float
    #: 0..1. Stressed syllables land on strong beats and are sung louder.
    emphasis: float
    #: True when this note continues the previous syllable rather than
    #: starting a new one -- a melisma.
    melisma: bool = False
    #: Bar and beat, so a caller can print a score or drive a metronome.
    bar: int = 0
    beat: float = 0.0

    @property
    def hz(self) -> float:
        return midi_to_hz(self.midi)

    def to_dict(self) -> dict[str, Any]:
        return {
            "syllable": self.syllable,
            "note": note_name(self.midi),
            "midi": self.midi,
            "hz": round(self.hz, 2),
            "start_ms": round(self.start_ms, 1),
            "duration_ms": round(self.duration_ms, 1),
            "emphasis": round(self.emphasis, 3),
            "melisma": self.melisma,
            "bar": self.bar,
            "beat": round(self.beat, 3),
        }


@dataclass
class SungPhrase:
    """A line of lyrics with its notes, and where the singer breathes."""

    text: str
    notes: list[SungNote] = field(default_factory=list)
    breath_after_ms: float = 0.0

    @property
    def duration_ms(self) -> float:
        if not self.notes:
            return 0.0
        last = self.notes[-1]
        return last.start_ms + last.duration_ms - self.notes[0].start_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "syllables": len(self.notes),
            "duration_ms": round(self.duration_ms, 1),
            "breath_after_ms": round(self.breath_after_ms, 1),
            "notes": [n.to_dict() for n in self.notes],
        }


#: How long a breath takes, as a fraction of a beat. Long enough to hear,
#: short enough not to break the bar.
_BREATH_BEATS = 0.5

#: How many scale degrees the melodic arch spans between the start of a line
#: and its middle. Five puts the peak roughly a fifth above the tonic, which
#: is where most singable melodies sit.
_ARCH_DEGREES = 5

#: A held syllable at the end of a phrase is sung across more than one note.
#: Only the final stressed syllable of a slow line gets one -- melisma is an
#: ornament, and applying it everywhere makes a melody sound aimless.
_MELISMA_MIN_BEAT_MS = 600.0


def sing(
    lyrics: str,
    *,
    emotion: Emotion | None = None,
    tonic: str | int = "C4",
    setting: MusicalSetting | None = None,
    language: str = "en",
) -> list[SungPhrase]:
    """Turn lyrics into a note plan: one note per syllable, on the beat.

    The melody is derived, not composed: it steps through the scale, rises
    where the line rises in stress and falls at the end of a phrase. What
    this gets right is the part that is actually determined by the words --
    how many notes there are, which syllables land on strong beats, where
    the singer can breathe, and how long the whole thing takes.

    ``emotion`` picks a tempo, scale and time signature when no explicit
    ``setting`` is given; passing the emotion analysed from the lyrics
    themselves is the usual case.
    """
    if emotion is None and setting is None:
        from .expression import ExpressionAnalyser

        emotion = ExpressionAnalyser(language=language).analyse(lyrics).emotion

    chosen = setting or setting_for(emotion or Emotion.NEUTRAL)
    root = name_to_midi(tonic) if isinstance(tonic, str) else int(tonic)
    root += chosen.register

    lines = [line.strip() for line in (lyrics or "").splitlines() if line.strip()]
    if not lines:
        return []

    beat_ms = chosen.tempo.beat_ms
    bar_beats = chosen.signature.beats
    degrees = scale_degrees(root, chosen.scale, 16)

    phrases: list[SungPhrase] = []
    cursor = 0.0
    for line in lines:
        syllables: list[str] = []
        for token in words_in(line):
            syllables.extend(syllabify(token))
        if not syllables:
            continue

        stresses = stress_pattern(line)
        notes: list[SungNote] = []
        for index, syllable in enumerate(syllables):
            stressed = bool(stresses[index]) if index < len(stresses) else False

            # A stressed syllable gets a beat; an unstressed one an offbeat.
            length = NoteValue.QUARTER if stressed else NoteValue.EIGHTH
            duration = chosen.tempo.note_ms(length, chosen.signature)

            # Arch the line: climb through the first half, fall through the
            # second, and put stressed syllables higher than the unstressed
            # ones around them. The arch used to span four scale degrees
            # from the tonic and stressed notes were nudged by two, so the
            # whole melody lived inside three semitones -- a monotone with
            # a wobble, not a tune.
            position = index / max(1, len(syllables) - 1)
            arch = 1.0 - abs(position - 0.5) * 2.0        # 0 at the edges, 1 mid-line
            step = int(round(arch * _ARCH_DEGREES))
            if stressed:
                step += 2
            # Land the last syllable of the phrase on the tonic: a line that
            # ends anywhere else sounds unfinished.
            if index == len(syllables) - 1:
                step = 0
            degree = degrees[max(0, min(len(degrees) - 1, step))]

            absolute_beat = cursor / beat_ms
            notes.append(
                SungNote(
                    syllable=syllable,
                    midi=degree,
                    start_ms=cursor,
                    duration_ms=duration * chosen.articulation,
                    emphasis=0.8 if stressed else 0.45,
                    bar=int(absolute_beat // bar_beats) + 1,
                    beat=absolute_beat % bar_beats + 1,
                )
            )
            cursor += duration

        # A slow tempo leaves room to carry the last vowel across a second
        # note. This is what the melisma flag is for; it was declared and
        # then never set by anything, so the field always read False.
        if notes and beat_ms >= _MELISMA_MIN_BEAT_MS and len(notes) > 2:
            tail = notes[-1]
            passing = degrees[min(len(degrees) - 1, 2)]
            extra_ms = chosen.tempo.note_ms(NoteValue.EIGHTH, chosen.signature)
            notes.append(
                SungNote(
                    syllable=tail.syllable,
                    midi=passing,
                    start_ms=cursor,
                    duration_ms=extra_ms * chosen.articulation,
                    emphasis=tail.emphasis * 0.8,
                    melisma=True,
                    bar=int((cursor / beat_ms) // bar_beats) + 1,
                    beat=(cursor / beat_ms) % bar_beats + 1,
                )
            )
            cursor += extra_ms

        breath = beat_ms * _BREATH_BEATS
        phrases.append(SungPhrase(text=line, notes=notes, breath_after_ms=breath))
        cursor += breath

    return phrases


def analyse_song(lyrics: str, *, language: str = "en") -> dict[str, Any]:
    """Everything the engine can tell about a lyric without hearing it.

    Structure, metre, rhyme, syllable counts, the emotion of the words and
    the musical setting that emotion implies. This is the "read the song"
    entry point; ``sing`` is the "perform it" one.
    """
    from .expression import ExpressionAnalyser

    reading = ExpressionAnalyser(language=language).analyse(lyrics)
    setting = setting_for(reading.emotion)
    sections = sections_of(lyrics)
    lines = [line.strip() for line in (lyrics or "").splitlines() if line.strip()]
    scansions = [scan(line) for line in lines]
    counts = [syllables_in(line) for line in lines]

    # A song whose lines are all the same length is singable to one tune;
    # one whose lines vary is not, and that is worth reporting.
    regular = len(set(counts)) <= 1 if counts else False

    total_syllables = sum(counts)
    beats = total_syllables * 0.75  # average of a quarter and an eighth
    duration_ms = beats * setting.tempo.beat_ms

    return {
        "language": language,
        "emotion": reading.emotion.value,
        "confidence": round(reading.confidence, 3),
        "lines": len(lines),
        "syllables": total_syllables,
        "syllables_per_line": counts,
        "regular_metre": regular,
        "metre": scansions[0].name if scansions else "free verse",
        "scansion": [s.to_dict() for s in scansions],
        "rhyme_scheme": rhyme_scheme(lines),
        "sections": [s.to_dict() for s in sections],
        "setting": setting.to_dict(),
        "estimated_duration_ms": round(duration_ms, 1),
    }
