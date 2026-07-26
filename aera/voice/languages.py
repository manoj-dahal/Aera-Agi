"""Language packs for expression and spoken-form normalisation.

Every emotion cue, negation and number word in the voice engine was English.
The `language` field was threaded through the whole pipeline and then ignored,
so "¡Eso es fantástico!" scored neutral and "87% completado" was read with an
English number inside a Spanish sentence.

A pack supplies the vocabulary for one language. The analysis machinery --
clause-scoped negation, intensifier boosting, recency weighting -- is
language-independent and stays in ``expression.py``; only the words change.

Scope is stated rather than implied. Every pack here is real vocabulary, not
a stub; ``supported()`` says which languages have one, and anything else
falls back to English matching, which is wrong but predictable.

Two things a pack must get right that are easy to get wrong:

*Tens are not "eighty seven".* Germanic and Indic languages do not build
two-digit numbers by juxtaposition. German says *siebenundachtzig* (seven and
eighty), Hindi and Nepali have a hundred irregular forms with no derivation
at all. ``tens_rule`` and ``compound`` exist so each pack states its own
convention instead of inheriting English word order.

*Word boundaries are script-dependent.* Matching without a boundary made
Hindi "नाम" (name) hit the negation "ना"; matching with a plain ``\b`` then
broke every word ending in a vowel sign, because those are combining marks
and ``\w`` excludes them. See ``_pattern``.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..core.logging import get_logger
from .engine import Emotion
from .scripts import RTL_SCRIPTS, Script, detect_script

logger = get_logger("voice.languages")


class TensRule(str, Enum):
    """How a language builds 21-99 from its tens and ones.

    English juxtaposes ("eighty seven"). German and Dutch invert and join
    ("siebenundachtzig"). Indic languages do neither: every value has its own
    word. Getting this wrong is not a rounding error -- "achtzig sieben" is
    not German, it is nothing.
    """

    #: tens then ones, separated: "eighty seven", "ochenta y siete".
    #: Teens are irregular, so 0-19 must be listed.
    TENS_FIRST = "tens_first"
    #: ones, a joiner, then tens, written solid: "siebenundachtzig".
    ONES_FIRST = "ones_first"
    #: Fully regular: teens compose too, so only 0-9 are listed. Chinese
    #: builds 11 as 十一 (ten-one) and 87 as 八十七 (eight-ten-seven).
    DECIMAL = "decimal"
    #: no rule -- the pack lists all of 0-99 in ``ones``.
    LISTED = "listed"
    #: 21-99 are irregular and this pack does not carry the table. Exact
    #: tens and 0-20 are spoken; everything else stays a numeral.
    #:
    #: Bengali 21 is একুশ, Gujarati એકવીસ, Punjabi ਇੱਕੀ, Marathi एकवीस --
    #: none of them "twenty one" in their own words. Composing anyway
    #: produced confident nonsense in ten languages. Saying the digits is
    #: worse than a correct reading and much better than a wrong one, and
    #: ``spells_all_numbers`` reports which case a caller is in.
    IRREGULAR = "irregular"


@dataclass(frozen=True)
class LanguagePack:
    """Emotion and number vocabulary for one language."""

    code: str
    label: str
    #: The language's own name for itself, for a language picker.
    endonym: str
    #: Words that flip the polarity of what follows.
    negations: tuple[str, ...]
    #: Words that amplify what they modify.
    intensifiers: tuple[str, ...]
    #: Words that soften a claim.
    hedges: tuple[str, ...]
    #: Conjunctions that end a negation's scope.
    clause_breaks: tuple[str, ...]
    #: Emotion cues: emotion -> the words that signal it.
    cues: dict[Emotion, tuple[str, ...]]
    #: 0-19, or 0-99 when ``tens_rule`` is LISTED. Empty leaves numbers to
    #: the engine.
    ones: tuple[str, ...] = ()
    tens: tuple[str, ...] = ()
    tens_rule: TensRule = TensRule.TENS_FIRST
    #: Inserted between tens and ones. Spanish needs "y", German "und".
    compound: str = " "
    #: Between a hundreds multiplier and the hundred word. German writes
    #: "zweihundert" solid; English writes "two hundred".
    join: str = " "
    #: Between a scale group and what follows it. German keeps a space
    #: around "Millionen" even though it joins hundreds solid, so this is
    #: separate -- sharing one setting produced "zweiMillionenfünfhundert".
    scale_join: str | None = None
    #: Between a group and the *next* group. Persian links them all with
    #: و: "دو میلیون و پانصد هزار". Using scale_join for this put the و
    #: between the multiplier and its own scale word too.
    group_join: str | None = None
    #: Word for a hundred, and the multiples where that word is irregular.
    hundred: str = ""
    #: Some languages say "one hundred", others just "hundred".
    hundred_needs_one: bool = False
    #: 0, 100, 200 ... 900 when they are not derivable. Spanish
    #: "quinientos" and Russian "двести" are not five/two plus hundred, and
    #: composing them gave "cinco cien" and "два сто".
    hundreds: tuple[str, ...] = ()
    #: Between the hundreds and what follows: English says "three hundred
    #: AND forty two". Defaults to the plain join.
    after_hundred: str | None = None
    #: Swahili counts "mia tatu" -- the hundred word first, then how many.
    hundred_after: bool = False
    #: Same for larger scales: "elfu mbili", "milioni tano".
    scale_after: bool = False
    #: Scale words. A three-form entry is a Slavic plural: the form used for
    #: 1, for 2-4, and for 5 and above.
    scales: tuple[tuple[int, str | tuple[str, str, str]], ...] = ()
    point: str = "point"
    #: Unit names, singular and plural.
    units: dict[str, tuple[str, str]] = field(default_factory=dict)
    #: Units written before the number rather than after. Chinese says
    #: 百分之八十七 -- "of a hundred parts, eighty-seven" -- so emitting
    #: "八十七 百分之" was backwards.
    units_before: tuple[str, ...] = ()

    @property
    def scale_separator(self) -> str:
        """Between a multiplier and its scale word."""
        return self.join if self.scale_join is None else self.scale_join

    @property
    def hundred_separator(self) -> str:
        """Between the hundreds group and the remainder."""
        return self.join if self.after_hundred is None else self.after_hundred

    @property
    def group_separator(self) -> str:
        """Between one scale group and the next."""
        if self.group_join is not None:
            return self.group_join
        return self.scale_separator

    @property
    def spells_all_numbers(self) -> bool:
        """Whether every integer gets words, or some stay numerals.

        False for Japanese and Korean (counter-dependent readings) and for
        the Indic packs whose irregular 21-99 forms are not carried here.
        """
        if not self.ones:
            return False
        return self.tens_rule is not TensRule.IRREGULAR

    @property
    def script(self) -> Script:
        """The script this language is written in, from its own vocabulary."""
        sample = "".join(self.negations) + "".join(
            w for words in self.cues.values() for w in words
        )
        return detect_script(sample)

    @property
    def rtl(self) -> bool:
        return self.script in RTL_SCRIPTS

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "label": self.label,
            "endonym": self.endonym,
            "emotion_cues": sum(len(words) for words in self.cues.values()),
            "has_numbers": bool(self.ones),
            "spells_all_numbers": self.spells_all_numbers,
            "script": self.script.value,
            "rtl": self.rtl,
        }


#: Scripts where a word boundary cannot be asserted at all: Han and Kana
#: have no spaces and no ASCII word characters, and Thai, Lao, Khmer and
#: Myanmar are written without spaces between words. Anchoring there matches
#: nothing.
_NO_BOUNDARY = frozenset(
    {Script.HAN, Script.KANA, Script.THAI, Script.LAO, Script.KHMER, Script.MYANMAR}
)

#: Scripts where a cue is a stem that takes grammatical endings, so a
#: right-hand boundary must not be asserted. Korean 죄송 ("sorry") is only
#: ever written attached to one -- 죄송합니다, 죄송해요 -- and anchoring the
#: end meant the Korean pack matched nothing in a real sentence. The left
#: edge still holds, so a stem must start a word.
_SUFFIXING = frozenset({Script.HANGUL})


def _mark_characters() -> str:
    """Every combining mark in the scripts these packs use.

    Python's ``re`` has no ``\\p{M}``, and ``\\w`` excludes combining marks,
    so ``\\b`` cannot assert after a word that ends in one. Devanagari
    "राम्रो" ends in the vowel sign ो (category Mc), which meant
    ``\\bराम्रो\\b`` never matched and the Nepali word for "good" stopped
    being detected. Same for Arabic, Hebrew, Thai and every abugida.

    Scanned once at import over the ranges the packs actually cover.
    """
    marks = []
    for code in range(0x0300, 0x1B00):
        char = chr(code)
        if unicodedata.category(char) in ("Mn", "Mc", "Me"):
            marks.append(char)
    return "".join(marks)


#: A character that continues a word: a word character, or a combining mark
#: attached to one.
_WORD_CLASS = "\\w" + re.escape(_mark_characters())
_LEFT_EDGE = f"(?<![{_WORD_CLASS}])"
_RIGHT_EDGE = f"(?![{_WORD_CLASS}])"


def _pattern(words: tuple[str, ...]) -> re.Pattern[str] | None:
    """Word-boundary alternation, or None when there is nothing to match.

    Uses an explicit edge assertion rather than ``\\b``. The previous code
    dropped the boundary for every non-ASCII pack, so Hindi "नाम" (name) hit
    the negation "ना" and the sentence read CONCERNED; switching to a plain
    ``\\b`` then broke every word ending in a vowel sign. Neither works --
    the boundary has to know that a combining mark is part of the word.
    """
    if not words:
        return None
    joined = "|".join(re.escape(w) for w in words)
    scripts = {detect_script(w) for w in words}
    if scripts & _NO_BOUNDARY:
        return re.compile(f"({joined})", re.IGNORECASE)
    if scripts & _SUFFIXING:
        return re.compile(f"{_LEFT_EDGE}({joined})", re.IGNORECASE)
    return re.compile(f"{_LEFT_EDGE}({joined}){_RIGHT_EDGE}", re.IGNORECASE)


# The pack modules import LanguagePack and TensRule from here, so they can
# only be imported once those exist. Deliberately placed after the
# definitions rather than at the top of the file, where it would be a
# circular import that fails at load.
from .packs_asia import ASIA  # noqa: E402
from .packs_western import WESTERN  # noqa: E402

#: Every language with real vocabulary, keyed by ISO 639-1 code.
PACKS: dict[str, LanguagePack] = {pack.code: pack for pack in (*WESTERN, *ASIA)}

#: The fallback. Named separately so the fallback path is explicit rather
#: than "whatever happens to be first".
ENGLISH = PACKS["en"]


def _validate(packs: dict[str, LanguagePack]) -> None:
    """Catch pack mistakes at import, where the traceback names the pack.

    Every check here corresponds to a bug that actually shipped:

    * A one-element cue tuple without its trailing comma is a plain string,
      and Python iterates it character by character -- every letter becomes a
      cue. Nepali's ``("रोचक")`` did this and matched almost anything.
    * ``tens`` needs ten slots when a rule composes from it; a short table
      raised IndexError only for the values that reached the missing entry.
    * ``TensRule.LISTED`` promises all hundred forms are present.
    """
    for pack in packs.values():
        for emotion, words in pack.cues.items():
            if not isinstance(words, tuple):
                raise TypeError(
                    f"{pack.code} cues for {emotion.value} must be a tuple, "
                    f"got {type(words).__name__}: a single entry needs a trailing comma"
                )
        for name in ("negations", "intensifiers", "hedges", "clause_breaks"):
            value = getattr(pack, name)
            if not isinstance(value, tuple):
                raise TypeError(f"{pack.code}.{name} must be a tuple, got {type(value).__name__}")
        if not pack.ones:
            continue
        if pack.tens_rule is TensRule.LISTED:
            if len(pack.ones) < 100:
                raise ValueError(
                    f"{pack.code} declares TensRule.LISTED but lists only "
                    f"{len(pack.ones)} of 100 forms"
                )
        elif pack.tens_rule is TensRule.IRREGULAR:
            if len(pack.ones) < 21:
                raise ValueError(
                    f"{pack.code} declares TensRule.IRREGULAR and must still "
                    f"cover 0-20, has {len(pack.ones)}"
                )
            if len(pack.tens) != 10:
                raise ValueError(f"{pack.code} needs 10 slots in tens, has {len(pack.tens)}")
        elif pack.tens_rule is TensRule.DECIMAL:
            if len(pack.ones) < 10:
                raise ValueError(f"{pack.code} needs 0-9 in ones, has {len(pack.ones)}")
            if len(pack.tens) != 10:
                raise ValueError(f"{pack.code} needs 10 slots in tens, has {len(pack.tens)}")
        else:
            if len(pack.ones) < 20:
                raise ValueError(f"{pack.code} needs 0-19 in ones, has {len(pack.ones)}")
            if len(pack.tens) != 10:
                raise ValueError(
                    f"{pack.code} needs 10 slots in tens (0 and 1 unused), "
                    f"has {len(pack.tens)}"
                )
        if not pack.hundred:
            raise ValueError(f"{pack.code} has number words but no word for hundred")


_validate(PACKS)


def get_pack(language: str | None) -> LanguagePack:
    """The pack for a language tag, falling back to English.

    Accepts region subtags: "es-MX" and "pt_BR" both reduce to their base.
    """
    if not language:
        return ENGLISH
    base = re.split(r"[-_]", language.strip().lower())[0]
    return PACKS.get(base, ENGLISH)


def is_supported(language: str | None) -> bool:
    """Whether a real pack exists, rather than the English fallback."""
    if not language:
        return False
    return re.split(r"[-_]", language.strip().lower())[0] in PACKS


def supported() -> list[dict[str, Any]]:
    """Every language with a pack, for a caller deciding what to offer."""
    return [pack.to_dict() for pack in PACKS.values()]


def say_number_in(value: int, pack: LanguagePack) -> str:
    """Spell an integer in one language.

    Returns the digits unchanged when the pack has no number words, which is
    honest: a wrong reading is worse than letting the engine handle it.

    Two-digit numbers follow the pack's own rule. Reading them all as English
    juxtaposition produced "achtzig sieben" for 87 in German and "बीस एक" for
    21 in Hindi -- word salad in both, and it was doing that in every
    language at once.
    """
    if not pack.ones:
        return str(value)
    if value < 0:
        return f"{_MINUS.get(pack.code, 'minus')} {say_number_in(-value, pack)}"
    if pack.tens_rule is TensRule.DECIMAL:
        if value < 10:
            return pack.ones[value]
        if value < 100:
            tens, ones = divmod(value, 10)
            word = pack.tens[tens]
            return f"{word}{pack.compound}{pack.ones[ones]}" if ones else word
    elif value < len(pack.ones) and pack.ones[value]:
        # A pack may list past 19 where those forms are irregular: Spanish
        # writes 21-29 solid ("veintiuno"), so the listed form wins over the
        # " y " rule that applies from 30 up.
        return pack.ones[value]
    if value < 100:
        tens, ones = divmod(value, 10)
        word = pack.tens[tens]
        if not ones:
            return word
        if pack.tens_rule is TensRule.IRREGULAR:
            # No table for this one; a numeral is honest, a guess is not.
            return str(value)
        if pack.tens_rule is TensRule.ONES_FIRST:
            # German, Dutch, Danish: "sieben-und-achtzig", written solid.
            joiner = pack.compound
            if pack.code == "nl" and pack.ones[ones].endswith(("a", "e", "i", "o", "u")):
                # tweeënveertig, drieënveertig -- the joining en takes a
                # diaeresis after a vowel, or the vowels run together.
                joiner = "ën"
            return f"{pack.ones[ones]}{joiner}{word}"
        return f"{word}{pack.compound}{pack.ones[ones]}"
    if value < 1000:
        hundreds, rest = divmod(value, 100)
        prefix = _hundreds(hundreds, pack)
        tail = say_number_in(rest, pack) if rest else ""
        return f"{prefix}{pack.hundred_separator}{tail}" if tail else prefix
    for size, name in pack.scales:
        if value >= size:
            count, rest = divmod(value, size)
            word = _scale_word(name, count)
            sep = pack.scale_separator
            # "one thousand", but Spanish says "mil", not "uno mil". A
            # three-form scale already carries its own "one" variant.
            if count == 1 and (not pack.hundred_needs_one or not isinstance(name, str)):
                out = word
            elif pack.scale_after:
                out = f"{word}{sep}{say_number_in(count, pack)}"
            else:
                out = f"{say_number_in(count, pack)}{sep}{word}"
            tail = say_number_in(rest, pack) if rest else ""
            return f"{out}{pack.group_separator}{tail}" if tail else out
    return str(value)


def _hundreds(count: int, pack: LanguagePack) -> str:
    """The word for count hundreds, honouring irregular forms and word order."""
    if pack.hundreds and count < len(pack.hundreds) and pack.hundreds[count]:
        return pack.hundreds[count]
    if count == 1 and not pack.hundred_needs_one:
        return pack.hundred
    if pack.hundred_after:
        # Swahili: "mia tatu", the scale word before the multiplier.
        return f"{pack.hundred}{pack.join}{pack.ones[count]}"
    return f"{pack.ones[count]}{pack.join}{pack.hundred}"


def _scale_word(name: str | tuple[str, str, str], count: int) -> str:
    """Pick the right plural of a scale word.

    Russian, Ukrainian and Polish inflect it by the final digits: одна
    тысяча, две тысячи, пять тысяч. Reading "тысяч" for all of them was
    wrong in two cases out of three.
    """
    if isinstance(name, str):
        return name
    one, few, many = name
    if count % 100 in range(11, 15):
        return many
    last = count % 10
    if last == 1:
        return one
    if last in (2, 3, 4):
        return few
    return many


#: How each language says a negative sign. Falls back to "minus", which most
#: of Europe borrows anyway.
_MINUS: dict[str, str] = {
    "en": "minus", "es": "menos", "fr": "moins", "de": "minus", "it": "meno",
    "pt": "menos", "nl": "min", "sv": "minus", "da": "minus", "nb": "minus",
    "fi": "miinus", "pl": "minus", "cs": "mínus", "uk": "мінус",
    "ru": "минус", "el": "μείον", "tr": "eksi", "id": "minus", "vi": "âm",
    "hi": "ऋण", "ne": "ऋण", "bn": "ঋণাত্মক", "ta": "கழித்தல்",
    "te": "రుణ", "mr": "उणे", "gu": "ઓછા", "kn": "ಋಣ", "ml": "മൈനസ്",
    "pa": "ਘਟਾਓ", "ur": "منفی", "ar": "ناقص", "he": "מינוס", "fa": "منفی",
    "th": "ลบ", "ko": "마이너스", "ja": "マイナス", "zh": "负", "sw": "kasi",
}


#: Compiled patterns, built once per pack.
_CACHE: dict[str, dict[str, Any]] = {}


def compiled(pack: LanguagePack) -> dict[str, Any]:
    """Regexes for a pack, compiled on first use."""
    if pack.code not in _CACHE:
        _CACHE[pack.code] = {
            "negations": _pattern(pack.negations),
            "intensifiers": _pattern(pack.intensifiers),
            "hedges": _pattern(pack.hedges),
            "clause_breaks": _pattern(pack.clause_breaks),
            "cues": {
                emotion: _pattern(words)
                for emotion, words in pack.cues.items()
                if words
            },
        }
    return _CACHE[pack.code]
