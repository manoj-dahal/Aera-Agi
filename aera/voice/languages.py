"""Language packs for expression and spoken-form normalisation.

Every emotion cue, negation and number word in the voice engine was English.
The `language` field was threaded through the whole pipeline and then ignored,
so "¡Eso es fantástico!" scored neutral and "87% completado" was read with an
English number inside a Spanish sentence.

A pack supplies the vocabulary for one language. The analysis machinery --
clause-scoped negation, intensifier boosting, recency weighting -- is
language-independent and stays in ``expression.py``; only the words change.

Scope is stated rather than implied. Six languages have real packs. Anything
else falls back to English matching, which is wrong but predictable, and
``supported()`` says which is which so a caller is never guessing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..core.logging import get_logger
from .engine import Emotion

logger = get_logger("voice.languages")


@dataclass(frozen=True)
class LanguagePack:
    """Emotion and number vocabulary for one language."""

    code: str
    label: str
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
    #: 0-19, then tens. Empty when numbers are left to the engine.
    ones: tuple[str, ...] = ()
    tens: tuple[str, ...] = ()
    #: Words for scale and the decimal point.
    hundred: str = ""
    scales: tuple[tuple[int, str], ...] = ()
    point: str = "point"
    #: Unit names, singular and plural.
    units: dict[str, tuple[str, str]] = field(default_factory=dict)
    #: Whether the script is alphabetic. Logographic scripts (Chinese,
    #: Japanese kanji) carry no letter-to-sound mapping, so visemes have to
    #: come from syllable count instead.
    alphabetic: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "label": self.label,
            "emotion_cues": sum(len(words) for words in self.cues.values()),
            "has_numbers": bool(self.ones),
            "alphabetic": self.alphabetic,
        }


def _pattern(words: tuple[str, ...]) -> re.Pattern[str] | None:
    """Word-boundary alternation, or None when there is nothing to match.

    ``\\b`` is unreliable around non-ASCII, so scripts without spaces between
    words use a plain alternation.
    """
    if not words:
        return None
    joined = "|".join(re.escape(w) for w in words)
    ascii_only = all(w.isascii() for w in words)
    return re.compile(rf"\b({joined})\b" if ascii_only else f"({joined})", re.IGNORECASE)


ENGLISH = LanguagePack(
    code="en",
    label="English",
    negations=(
        "not", "no", "never", "cannot", "can't", "won't", "isn't", "aren't",
        "wasn't", "weren't", "doesn't", "didn't", "don't", "couldn't",
        "shouldn't", "wouldn't", "hardly", "barely", "without", "lacks",
        "lacking", "lack",
    ),
    intensifiers=(
        "very", "really", "extremely", "incredibly", "absolutely", "totally",
        "so", "much", "deeply", "highly", "seriously", "terribly", "utterly",
        "completely",
    ),
    hedges=(
        "maybe", "perhaps", "possibly", "might", "probably", "seems",
        "appears", "somewhat", "slightly", "fairly",
    ),
    clause_breaks=("but", "however", "although", "though", "yet", "whereas"),
    cues={
        Emotion.EXCITED: ("amazing", "awesome", "fantastic", "incredible", "brilliant", "wonderful", "perfect", "wow"),
        Emotion.HAPPY: ("great", "glad", "happy", "pleased", "success", "thanks", "working", "fixed", "resolved", "recovered"),
        Emotion.CONFIDENT: ("certainly", "definitely", "absolutely", "confirmed", "verified", "guaranteed"),
        Emotion.CURIOUS: ("interesting", "wonder", "curious"),
        Emotion.CALM: ("steady", "stable", "fine", "alright"),
        Emotion.CONCERNED: ("warning", "careful", "risk", "danger", "caution", "unstable"),
        Emotion.SERIOUS: ("critical", "security", "vulnerability", "urgent", "fatal", "severe"),
        Emotion.SAD: ("sorry", "unfortunately", "failed", "failure", "unable", "broken", "disaster", "crashed"),
    },
    ones=(
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "sixteen", "seventeen", "eighteen", "nineteen",
    ),
    tens=("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"),
    hundred="hundred",
    scales=((1_000_000_000, "billion"), (1_000_000, "million"), (1_000, "thousand")),
    point="point",
    units={"%": ("percent", "percent"), "ms": ("millisecond", "milliseconds"),
           "gb": ("gigabyte", "gigabytes"), "mb": ("megabyte", "megabytes")},
)

SPANISH = LanguagePack(
    code="es",
    label="Español",
    negations=("no", "nunca", "jamás", "ni", "tampoco", "sin", "nada"),
    intensifiers=("muy", "súper", "realmente", "totalmente", "completamente", "extremadamente", "bastante"),
    hedges=("quizás", "tal vez", "posiblemente", "puede", "parece", "algo"),
    clause_breaks=("pero", "aunque", "sin embargo", "mientras"),
    cues={
        Emotion.EXCITED: ("increíble", "fantástico", "genial", "maravilloso", "perfecto"),
        Emotion.HAPPY: ("bien", "bueno", "gracias", "éxito", "contento", "resuelto", "arreglado"),
        Emotion.CONFIDENT: ("seguro", "confirmado", "verificado", "claro"),
        Emotion.CURIOUS: ("interesante", "curioso"),
        Emotion.CALM: ("tranquilo", "estable", "calma"),
        Emotion.CONCERNED: ("cuidado", "riesgo", "peligro", "advertencia"),
        Emotion.SERIOUS: ("crítico", "urgente", "grave", "seguridad"),
        Emotion.SAD: ("lo siento", "error", "falló", "fallo", "roto", "desafortunadamente", "perdido"),
    },
    ones=("cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho",
          "nueve", "diez", "once", "doce", "trece", "catorce", "quince",
          "dieciséis", "diecisiete", "dieciocho", "diecinueve"),
    tens=("", "", "veinte", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"),
    hundred="cien",
    scales=((1_000_000, "millón"), (1_000, "mil")),
    point="coma",
    units={"%": ("por ciento", "por ciento"), "ms": ("milisegundo", "milisegundos"),
           "gb": ("gigabyte", "gigabytes"), "mb": ("megabyte", "megabytes")},
)

FRENCH = LanguagePack(
    code="fr",
    label="Français",
    negations=("ne", "pas", "non", "jamais", "aucun", "sans", "rien"),
    intensifiers=("très", "vraiment", "extrêmement", "totalement", "complètement", "tellement"),
    hedges=("peut-être", "possiblement", "semble", "paraît", "un peu"),
    clause_breaks=("mais", "cependant", "bien que", "pourtant"),
    cues={
        Emotion.EXCITED: ("incroyable", "fantastique", "génial", "merveilleux", "parfait"),
        Emotion.HAPPY: ("bien", "bon", "merci", "succès", "content", "résolu", "réparé"),
        Emotion.CONFIDENT: ("certainement", "confirmé", "vérifié", "sûr"),
        Emotion.CURIOUS: ("intéressant", "curieux"),
        Emotion.CALM: ("calme", "stable", "tranquille"),
        Emotion.CONCERNED: ("attention", "risque", "danger", "avertissement"),
        Emotion.SERIOUS: ("critique", "urgent", "grave", "sécurité"),
        Emotion.SAD: ("désolé", "erreur", "échoué", "échec", "cassé", "malheureusement", "perdu"),
    },
    ones=("zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit",
          "neuf", "dix", "onze", "douze", "treize", "quatorze", "quinze",
          "seize", "dix-sept", "dix-huit", "dix-neuf"),
    tens=("", "", "vingt", "trente", "quarante", "cinquante", "soixante", "soixante-dix", "quatre-vingts", "quatre-vingt-dix"),
    hundred="cent",
    scales=((1_000_000, "million"), (1_000, "mille")),
    point="virgule",
    units={"%": ("pour cent", "pour cent"), "ms": ("milliseconde", "millisecondes"),
           "gb": ("gigaoctet", "gigaoctets"), "mb": ("mégaoctet", "mégaoctets")},
)

GERMAN = LanguagePack(
    code="de",
    label="Deutsch",
    negations=("nicht", "kein", "keine", "nie", "niemals", "ohne", "nichts"),
    intensifiers=("sehr", "wirklich", "extrem", "total", "völlig", "äußerst", "ziemlich"),
    hedges=("vielleicht", "möglicherweise", "scheint", "etwas", "eventuell"),
    clause_breaks=("aber", "jedoch", "obwohl", "dennoch"),
    cues={
        Emotion.EXCITED: ("unglaublich", "fantastisch", "toll", "wunderbar", "perfekt"),
        Emotion.HAPPY: ("gut", "danke", "erfolg", "froh", "gelöst", "repariert", "funktioniert"),
        Emotion.CONFIDENT: ("sicher", "bestätigt", "definitiv", "geprüft"),
        Emotion.CURIOUS: ("interessant", "neugierig"),
        Emotion.CALM: ("ruhig", "stabil", "gelassen"),
        Emotion.CONCERNED: ("achtung", "vorsicht", "risiko", "gefahr", "warnung"),
        Emotion.SERIOUS: ("kritisch", "dringend", "schwerwiegend", "sicherheit"),
        Emotion.SAD: ("entschuldigung", "leider", "fehler", "fehlgeschlagen", "kaputt", "verloren"),
    },
    ones=("null", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht",
          "neun", "zehn", "elf", "zwölf", "dreizehn", "vierzehn", "fünfzehn",
          "sechzehn", "siebzehn", "achtzehn", "neunzehn"),
    tens=("", "", "zwanzig", "dreißig", "vierzig", "fünfzig", "sechzig", "siebzig", "achtzig", "neunzig"),
    hundred="hundert",
    scales=((1_000_000, "Millionen"), (1_000, "tausend")),
    point="Komma",
    units={"%": ("Prozent", "Prozent"), "ms": ("Millisekunde", "Millisekunden"),
           "gb": ("Gigabyte", "Gigabyte"), "mb": ("Megabyte", "Megabyte")},
)

HINDI = LanguagePack(
    code="hi",
    label="हिन्दी",
    negations=("नहीं", "ना", "मत", "बिना", "कभी नहीं"),
    intensifiers=("बहुत", "अत्यंत", "पूरी तरह", "काफी"),
    hedges=("शायद", "संभवतः", "लगता है"),
    clause_breaks=("लेकिन", "परंतु", "मगर", "फिर भी"),
    cues={
        Emotion.EXCITED: ("अद्भुत", "शानदार", "बढ़िया"),
        Emotion.HAPPY: ("अच्छा", "धन्यवाद", "सफल", "खुश", "ठीक हो गया"),
        Emotion.CONFIDENT: ("निश्चित", "पक्का", "पुष्टि"),
        Emotion.CURIOUS: ("दिलचस्प", "जिज्ञासु"),
        Emotion.CALM: ("शांत", "स्थिर"),
        Emotion.CONCERNED: ("सावधान", "खतरा", "जोखिम", "चेतावनी"),
        Emotion.SERIOUS: ("गंभीर", "जरूरी", "सुरक्षा"),
        Emotion.SAD: ("क्षमा", "माफ", "विफल", "त्रुटि", "टूटा", "दुर्भाग्य"),
    },
    ones=("शून्य", "एक", "दो", "तीन", "चार", "पांच", "छह", "सात", "आठ", "नौ",
          "दस", "ग्यारह", "बारह", "तेरह", "चौदह", "पंद्रह", "सोलह", "सत्रह", "अठारह", "उन्नीस"),
    tens=("", "", "बीस", "तीस", "चालीस", "पचास", "साठ", "सत्तर", "अस्सी", "नब्बे"),
    hundred="सौ",
    scales=((10_000_000, "करोड़"), (100_000, "लाख"), (1_000, "हज़ार")),
    point="दशमलव",
    units={"%": ("प्रतिशत", "प्रतिशत")},
)

NEPALI = LanguagePack(
    code="ne",
    label="नेपाली",
    negations=("छैन", "होइन", "नगर", "बिना", "कहिल्यै छैन"),
    intensifiers=("धेरै", "अत्यन्तै", "पूर्ण रूपमा"),
    hedges=("सायद", "होला", "लाग्छ"),
    clause_breaks=("तर", "यद्यपि", "तैपनि"),
    cues={
        Emotion.EXCITED: ("अद्भुत", "उत्कृष्ट", "राम्रो"),
        Emotion.HAPPY: ("धन्यवाद", "सफल", "खुसी", "मिल्यो"),
        Emotion.CONFIDENT: ("निश्चित", "पक्का"),
        Emotion.CURIOUS: ("रोचक",),
        Emotion.CALM: ("शान्त", "स्थिर"),
        Emotion.CONCERNED: ("होसियार", "जोखिम", "खतरा"),
        Emotion.SERIOUS: ("गम्भीर", "जरुरी", "सुरक्षा"),
        Emotion.SAD: ("माफ", "असफल", "त्रुटि", "बिग्रियो", "दुर्भाग्य"),
    },
    ones=("शून्य", "एक", "दुई", "तीन", "चार", "पाँच", "छ", "सात", "आठ", "नौ",
          "दश", "एघार", "बाह्र", "तेह्र", "चौध", "पन्ध्र", "सोह्र", "सत्र", "अठार", "उन्नाइस"),
    tens=("", "", "बीस", "तीस", "चालीस", "पचास", "साठी", "सत्तरी", "असी", "नब्बे"),
    hundred="सय",
    scales=((10_000_000, "करोड"), (100_000, "लाख"), (1_000, "हजार")),
    point="दशमलव",
    units={"%": ("प्रतिशत", "प्रतिशत")},
)

JAPANESE = LanguagePack(
    code="ja",
    label="日本語",
    negations=("ない", "ません", "じゃない", "なし"),
    intensifiers=("とても", "非常に", "すごく", "本当に", "完全に"),
    hedges=("たぶん", "おそらく", "かもしれない", "ようだ"),
    clause_breaks=("でも", "しかし", "けれど", "が"),
    cues={
        Emotion.EXCITED: ("素晴らしい", "すごい", "最高"),
        Emotion.HAPPY: ("ありがとう", "成功", "嬉しい", "直った", "良い"),
        Emotion.CONFIDENT: ("確実", "確認", "もちろん"),
        Emotion.CURIOUS: ("面白い", "興味深い"),
        Emotion.CALM: ("安定", "静か"),
        Emotion.CONCERNED: ("注意", "危険", "警告", "リスク"),
        Emotion.SERIOUS: ("重大", "緊急", "深刻", "セキュリティ"),
        Emotion.SAD: ("すみません", "申し訳", "失敗", "エラー", "残念", "壊れ"),
    },
    # Numbers are left to the engine: Japanese counters change the reading
    # depending on what is counted, which a lookup table cannot capture.
    units={"%": ("パーセント", "パーセント"), "ms": ("ミリ秒", "ミリ秒"),
           "gb": ("ギガバイト", "ギガバイト"), "mb": ("メガバイト", "メガバイト")},
    alphabetic=False,
)

PACKS: dict[str, LanguagePack] = {
    pack.code: pack
    for pack in (ENGLISH, SPANISH, FRENCH, GERMAN, HINDI, NEPALI, JAPANESE)
}

# A one-element cue tuple written without its trailing comma is a plain
# string, and Python then iterates it character by character -- every letter
# becomes a separate cue and matches almost anything. Caught exactly that in
# Nepali, so it is asserted at import rather than left to a reader's eye.
for _pack in PACKS.values():
    for _emotion, _words in _pack.cues.items():
        if not isinstance(_words, tuple):
            raise TypeError(
                f"{_pack.code} cues for {_emotion.value} must be a tuple, "
                f"got {type(_words).__name__}: a single entry needs a trailing comma"
            )


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
    """
    if not pack.ones:
        return str(value)
    if value < 0:
        return f"-{say_number_in(-value, pack)}"
    if value < 20:
        return pack.ones[value]
    if value < 100:
        tens, ones = divmod(value, 10)
        word = pack.tens[tens]
        return f"{word} {pack.ones[ones]}".strip() if ones else word
    if value < 1000:
        hundreds, rest = divmod(value, 100)
        prefix = pack.hundred if hundreds == 1 else f"{pack.ones[hundreds]} {pack.hundred}"
        return f"{prefix} {say_number_in(rest, pack)}" if rest else prefix
    for size, name in pack.scales:
        if value >= size:
            count, rest = divmod(value, size)
            out = f"{say_number_in(count, pack)} {name}"
            return f"{out} {say_number_in(rest, pack)}" if rest else out
    return str(value)


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
