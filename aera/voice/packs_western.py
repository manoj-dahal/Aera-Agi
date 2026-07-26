# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Language packs: Europe and the Americas.

Split from ``languages.py`` because thirty-five packs in one file is a file
nobody reads. Grouped by region rather than by script so a reviewer who
speaks one of them can find it.

Each pack states its own two-digit rule. Germanic languages invert
("siebenundachtzig"), Romance languages mostly juxtapose but Spanish needs
its "y", and French has the vigesimal seventies and nineties that no generic
rule reproduces -- so French lists 0-99 outright.
"""

from __future__ import annotations

from .engine import Emotion
from .languages import LanguagePack, TensRule

_BYTES_EN = {
    "ms": ("millisecond", "milliseconds"),
    "kb": ("kilobyte", "kilobytes"),
    "mb": ("megabyte", "megabytes"),
    "gb": ("gigabyte", "gigabytes"),
    "tb": ("terabyte", "terabytes"),
}

ENGLISH = LanguagePack(
    code="en",
    label="English",
    endonym="English",
    negations=(
        "not", "no", "never", "cannot", "can't", "won't", "isn't", "aren't",
        "wasn't", "weren't", "doesn't", "didn't", "don't", "couldn't",
        "shouldn't", "wouldn't", "hardly", "barely", "without", "lacks",
        "lacking", "lack", "none", "nor", "neither",
    ),
    intensifiers=(
        "very", "really", "extremely", "incredibly", "absolutely", "totally",
        "so", "much", "deeply", "highly", "seriously", "terribly", "utterly",
        "completely", "entirely", "thoroughly",
    ),
    hedges=(
        "maybe", "perhaps", "possibly", "might", "probably", "seems",
        "appears", "somewhat", "slightly", "fairly", "could be", "i think",
        "kind of", "sort of",
    ),
    clause_breaks=("but", "however", "although", "though", "yet", "whereas"),
    cues={
        Emotion.EXCITED: (
            "amazing", "awesome", "fantastic", "incredible", "brilliant",
            "wonderful", "perfect", "wow", "yay", "hooray", "excellent",
        ),
        Emotion.HAPPY: (
            "great", "glad", "happy", "pleased", "success", "succeeded",
            "thanks", "thank you", "working", "works now", "fixed",
            "resolved", "recovered", "repaired", "sorted", "good news",
            "nice work", "well done", "complete", "completed", "up and running",
        ),
        Emotion.CONFIDENT: (
            "certainly", "definitely", "absolutely", "confirmed", "verified",
            "guaranteed", "of course", "no problem",
        ),
        Emotion.CURIOUS: ("interesting", "wonder", "curious", "how come", "what if"),
        # "safe" belongs here so that "not safe" has something to negate.
        # Without it the phrase scored neutral, and "Warning: it is not safe"
        # only read as concerned because "warning" happened to sit in the
        # same sentence -- split the clause apart and the meaning vanished.
        Emotion.CALM: (
            "steady", "stable", "fine", "alright", "no rush", "all good",
            "take your time", "safe", "secure", "healthy",
        ),
        Emotion.CONCERNED: (
            "warning", "careful", "risk", "danger", "caution", "unstable",
            "deprecated", "breaking", "watch out", "might fail",
        ),
        Emotion.SERIOUS: (
            "critical", "security", "vulnerability", "urgent", "fatal",
            "severe", "breach", "immediately", "must not",
        ),
        Emotion.SAD: (
            "sorry", "unfortunately", "failed", "failure", "unable",
            "broken", "disaster", "crashed", "crash", "outage", "regret",
            "lost", "could not", "couldn't",
        ),
    },
    ones=(
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "sixteen", "seventeen", "eighteen", "nineteen",
    ),
    tens=("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"),
    tens_rule=TensRule.TENS_FIRST,
    compound=" ",
    hundred="hundred",
    hundred_needs_one=True,
    after_hundred=" and ",
    scales=((1_000_000_000, "billion"), (1_000_000, "million"), (1_000, "thousand")),
    point="point",
    units={"%": ("percent", "percent"), "hz": ("hertz", "hertz"),
           "khz": ("kilohertz", "kilohertz"), **_BYTES_EN},
)

SPANISH = LanguagePack(
    code="es",
    label="Spanish",
    endonym="Español",
    negations=("no", "nunca", "jamás", "ni", "tampoco", "sin", "nada", "ningún", "ninguna"),
    intensifiers=("muy", "súper", "realmente", "totalmente", "completamente",
                  "extremadamente", "bastante", "sumamente"),
    hedges=("quizás", "quizá", "tal vez", "posiblemente", "puede", "parece", "algo"),
    clause_breaks=("pero", "aunque", "sin embargo", "mientras"),
    cues={
        Emotion.EXCITED: ("increíble", "fantástico", "genial", "maravilloso", "perfecto", "excelente"),
        Emotion.HAPPY: ("bien", "bueno", "gracias", "éxito", "contento", "resuelto", "arreglado", "funciona"),
        Emotion.CONFIDENT: ("seguro", "confirmado", "verificado", "claro", "por supuesto"),
        Emotion.CURIOUS: ("interesante", "curioso"),
        Emotion.CALM: ("tranquilo", "estable", "calma"),
        Emotion.CONCERNED: ("cuidado", "riesgo", "peligro", "advertencia", "inestable"),
        Emotion.SERIOUS: ("crítico", "urgente", "grave", "seguridad", "vulnerabilidad"),
        Emotion.SAD: ("lo siento", "error", "falló", "fallo", "roto", "desafortunadamente", "perdido", "caída"),
    },
    # 0-29 are listed because 16-29 are written solid ("dieciséis",
    # "veintiuno") rather than composed.
    ones=("cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho",
          "nueve", "diez", "once", "doce", "trece", "catorce", "quince",
          "dieciséis", "diecisiete", "dieciocho", "diecinueve", "veinte",
          "veintiuno", "veintidós", "veintitrés", "veinticuatro", "veinticinco",
          "veintiséis", "veintisiete", "veintiocho", "veintinueve"),
    tens=("", "", "veinte", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"),
    # 0-29 are listed above because 21-29 are written solid ("veintiuno");
    # 30 and up take " y ".
    tens_rule=TensRule.TENS_FIRST,
    compound=" y ",
    hundred="cien",
    # 500 is "quinientos", 700 "setecientos", 900 "novecientos" -- none of
    # them "cinco cien".
    hundreds=("", "cien", "doscientos", "trescientos", "cuatrocientos",
              "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos"),
    scales=((1_000_000, ("un millón", "millones", "millones")), (1_000, "mil")),
    point="coma",
    units={"%": ("por ciento", "por ciento"), "ms": ("milisegundo", "milisegundos"),
           "kb": ("kilobyte", "kilobytes"), "mb": ("megabyte", "megabytes"),
           "gb": ("gigabyte", "gigabytes"), "tb": ("terabyte", "terabytes"),
           "hz": ("hercio", "hercios"), "khz": ("kilohercio", "kilohercios")},
)

FRENCH = LanguagePack(
    code="fr",
    label="French",
    endonym="Français",
    negations=("ne", "pas", "non", "jamais", "aucun", "aucune", "sans", "rien", "ni"),
    intensifiers=("très", "vraiment", "extrêmement", "totalement", "complètement", "tellement", "fort"),
    hedges=("peut-être", "possiblement", "semble", "paraît", "un peu", "probablement"),
    clause_breaks=("mais", "cependant", "bien que", "pourtant", "toutefois"),
    cues={
        Emotion.EXCITED: ("incroyable", "fantastique", "génial", "merveilleux", "parfait", "excellent"),
        Emotion.HAPPY: ("bien", "bon", "merci", "succès", "content", "résolu", "réparé", "fonctionne"),
        Emotion.CONFIDENT: ("certainement", "confirmé", "vérifié", "sûr", "bien sûr"),
        Emotion.CURIOUS: ("intéressant", "curieux"),
        Emotion.CALM: ("calme", "stable", "tranquille"),
        Emotion.CONCERNED: ("attention", "risque", "danger", "avertissement", "instable"),
        Emotion.SERIOUS: ("critique", "urgent", "grave", "sécurité", "vulnérabilité"),
        Emotion.SAD: ("désolé", "erreur", "échoué", "échec", "cassé", "malheureusement", "perdu", "panne"),
    },
    # French counts by twenties above sixty: 70 is "soixante-dix", 80 is
    # "quatre-vingts", 97 is "quatre-vingt-dix-sept". No tens table can
    # generate that, so all of 0-99 is listed.
    ones=(
        "zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit",
        "neuf", "dix", "onze", "douze", "treize", "quatorze", "quinze",
        "seize", "dix-sept", "dix-huit", "dix-neuf", "vingt",
        "vingt et un", "vingt-deux", "vingt-trois", "vingt-quatre", "vingt-cinq",
        "vingt-six", "vingt-sept", "vingt-huit", "vingt-neuf", "trente",
        "trente et un", "trente-deux", "trente-trois", "trente-quatre", "trente-cinq",
        "trente-six", "trente-sept", "trente-huit", "trente-neuf", "quarante",
        "quarante et un", "quarante-deux", "quarante-trois", "quarante-quatre",
        "quarante-cinq", "quarante-six", "quarante-sept", "quarante-huit",
        "quarante-neuf", "cinquante", "cinquante et un", "cinquante-deux",
        "cinquante-trois", "cinquante-quatre", "cinquante-cinq", "cinquante-six",
        "cinquante-sept", "cinquante-huit", "cinquante-neuf", "soixante",
        "soixante et un", "soixante-deux", "soixante-trois", "soixante-quatre",
        "soixante-cinq", "soixante-six", "soixante-sept", "soixante-huit",
        "soixante-neuf", "soixante-dix", "soixante et onze", "soixante-douze",
        "soixante-treize", "soixante-quatorze", "soixante-quinze", "soixante-seize",
        "soixante-dix-sept", "soixante-dix-huit", "soixante-dix-neuf",
        "quatre-vingts", "quatre-vingt-un", "quatre-vingt-deux", "quatre-vingt-trois",
        "quatre-vingt-quatre", "quatre-vingt-cinq", "quatre-vingt-six",
        "quatre-vingt-sept", "quatre-vingt-huit", "quatre-vingt-neuf",
        "quatre-vingt-dix", "quatre-vingt-onze", "quatre-vingt-douze",
        "quatre-vingt-treize", "quatre-vingt-quatorze", "quatre-vingt-quinze",
        "quatre-vingt-seize", "quatre-vingt-dix-sept", "quatre-vingt-dix-huit",
        "quatre-vingt-dix-neuf",
    ),
    tens=(),
    tens_rule=TensRule.LISTED,
    hundred="cent",
    # "deux cents" alone, but "deux cent quarante" when something follows --
    # so the plural form is only safe at the end. Kept singular to stay
    # correct in the common case.
    hundreds=("", "cent", "deux cent", "trois cent", "quatre cent", "cinq cent",
              "six cent", "sept cent", "huit cent", "neuf cent"),
    scales=((1_000_000, ("un million", "millions", "millions")), (1_000, "mille")),
    point="virgule",
    units={"%": ("pour cent", "pour cent"), "ms": ("milliseconde", "millisecondes"),
           "kb": ("kilooctet", "kilooctets"), "mb": ("mégaoctet", "mégaoctets"),
           "gb": ("gigaoctet", "gigaoctets"), "tb": ("téraoctet", "téraoctets"),
           "hz": ("hertz", "hertz"), "khz": ("kilohertz", "kilohertz")},
)

GERMAN = LanguagePack(
    code="de",
    label="German",
    endonym="Deutsch",
    negations=("nicht", "kein", "keine", "keinen", "nie", "niemals", "ohne", "nichts", "weder"),
    intensifiers=("sehr", "wirklich", "extrem", "total", "völlig", "äußerst", "ziemlich", "höchst"),
    hedges=("vielleicht", "möglicherweise", "scheint", "etwas", "eventuell", "wahrscheinlich"),
    clause_breaks=("aber", "jedoch", "obwohl", "dennoch", "allerdings"),
    cues={
        Emotion.EXCITED: ("unglaublich", "fantastisch", "toll", "wunderbar", "perfekt", "ausgezeichnet"),
        Emotion.HAPPY: ("gut", "danke", "erfolg", "froh", "gelöst", "repariert", "funktioniert", "behoben"),
        Emotion.CONFIDENT: ("sicher", "bestätigt", "definitiv", "geprüft", "natürlich"),
        Emotion.CURIOUS: ("interessant", "neugierig"),
        Emotion.CALM: ("ruhig", "stabil", "gelassen"),
        Emotion.CONCERNED: ("achtung", "vorsicht", "risiko", "gefahr", "warnung", "instabil"),
        Emotion.SERIOUS: ("kritisch", "dringend", "schwerwiegend", "sicherheit", "sicherheitslücke"),
        Emotion.SAD: ("entschuldigung", "leider", "fehler", "fehlgeschlagen", "kaputt", "verloren", "ausfall", "abgestürzt"),
    },
    # "eins" only stands alone; in a compound it is "ein"
    # ("einundzwanzig", not "einsundzwanzig").
    ones=("null", "ein", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht",
          "neun", "zehn", "elf", "zwölf", "dreizehn", "vierzehn", "fünfzehn",
          "sechzehn", "siebzehn", "achtzehn", "neunzehn"),
    tens=("", "", "zwanzig", "dreißig", "vierzig", "fünfzig", "sechzig", "siebzig", "achtzig", "neunzig"),
    # 87 is "siebenundachtzig": ones, joiner, tens, written solid.
    tens_rule=TensRule.ONES_FIRST,
    compound="und",
    hundred="hundert",
    join="",
    # "zweihundert" is solid but "zwei Millionen" is not; thousands stay
    # solid, so the space lives in the million word itself.
    scale_join="",
    scales=((1_000_000, (" eine Million ", " Millionen ", " Millionen ")), (1_000, "tausend")),
    point="Komma",
    units={"%": ("Prozent", "Prozent"), "ms": ("Millisekunde", "Millisekunden"),
           "kb": ("Kilobyte", "Kilobyte"), "mb": ("Megabyte", "Megabyte"),
           "gb": ("Gigabyte", "Gigabyte"), "tb": ("Terabyte", "Terabyte"),
           "hz": ("Hertz", "Hertz"), "khz": ("Kilohertz", "Kilohertz")},
)

ITALIAN = LanguagePack(
    code="it",
    label="Italian",
    endonym="Italiano",
    negations=("non", "no", "mai", "nessun", "nessuna", "senza", "niente", "né"),
    intensifiers=("molto", "davvero", "estremamente", "totalmente", "completamente", "assai"),
    hedges=("forse", "possibilmente", "sembra", "probabilmente", "un po'"),
    clause_breaks=("ma", "però", "tuttavia", "sebbene", "anche se"),
    cues={
        Emotion.EXCITED: ("incredibile", "fantastico", "meraviglioso", "perfetto", "eccellente"),
        Emotion.HAPPY: ("bene", "buono", "grazie", "successo", "contento", "risolto", "riparato", "funziona"),
        Emotion.CONFIDENT: ("certamente", "confermato", "verificato", "sicuro", "certo"),
        Emotion.CURIOUS: ("interessante", "curioso"),
        Emotion.CALM: ("calmo", "stabile", "tranquillo"),
        Emotion.CONCERNED: ("attenzione", "rischio", "pericolo", "avvertimento", "instabile"),
        Emotion.SERIOUS: ("critico", "urgente", "grave", "sicurezza", "vulnerabilità"),
        Emotion.SAD: ("scusa", "mi dispiace", "errore", "fallito", "rotto", "purtroppo", "perso"),
    },
    ones=("zero", "uno", "due", "tre", "quattro", "cinque", "sei", "sette", "otto",
          "nove", "dieci", "undici", "dodici", "tredici", "quattordici", "quindici",
          "sedici", "diciassette", "diciotto", "diciannove", "venti",
          # The tens word drops its final vowel before uno and otto:
          # ventuno, ventotto -- not "ventiuno".
          "ventuno", "ventidue", "ventitré", "ventiquattro", "venticinque",
          "ventisei", "ventisette", "ventotto", "ventinove"),
    tens=("", "", "venti", "trenta", "quaranta", "cinquanta", "sessanta", "settanta", "ottanta", "novanta"),
    tens_rule=TensRule.TENS_FIRST,
    compound="",
    hundred="cento",
    hundreds=("", "cento", "duecento", "trecento", "quattrocento", "cinquecento",
              "seicento", "settecento", "ottocento", "novecento"),
    # 1000 is "mille"; only the plural is "mila".
    scale_join="",
    scales=((1_000_000, ("un milione", " milioni ", " milioni ")), (1_000, ("mille", "mila", "mila"))),
    point="virgola",
    units={"%": ("per cento", "per cento"), "ms": ("millisecondo", "millisecondi"),
           "kb": ("kilobyte", "kilobyte"), "mb": ("megabyte", "megabyte"),
           "gb": ("gigabyte", "gigabyte"), "tb": ("terabyte", "terabyte"),
           "hz": ("hertz", "hertz"), "khz": ("kilohertz", "kilohertz")},
)

PORTUGUESE = LanguagePack(
    code="pt",
    label="Portuguese",
    endonym="Português",
    negations=("não", "nunca", "jamais", "nem", "sem", "nada", "nenhum", "nenhuma"),
    intensifiers=("muito", "realmente", "extremamente", "totalmente", "completamente", "bastante"),
    hedges=("talvez", "possivelmente", "parece", "provavelmente", "um pouco"),
    clause_breaks=("mas", "porém", "contudo", "embora", "entretanto"),
    cues={
        Emotion.EXCITED: ("incrível", "fantástico", "ótimo", "maravilhoso", "perfeito", "excelente"),
        Emotion.HAPPY: ("bom", "bem", "obrigado", "sucesso", "contente", "resolvido", "consertado", "funciona"),
        Emotion.CONFIDENT: ("certamente", "confirmado", "verificado", "claro", "com certeza"),
        Emotion.CURIOUS: ("interessante", "curioso"),
        Emotion.CALM: ("calmo", "estável", "tranquilo"),
        Emotion.CONCERNED: ("cuidado", "risco", "perigo", "aviso", "instável"),
        Emotion.SERIOUS: ("crítico", "urgente", "grave", "segurança", "vulnerabilidade"),
        Emotion.SAD: ("desculpe", "erro", "falhou", "falha", "quebrado", "infelizmente", "perdido"),
    },
    ones=("zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito",
          "nove", "dez", "onze", "doze", "treze", "catorze", "quinze",
          "dezesseis", "dezessete", "dezoito", "dezenove"),
    tens=("", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa"),
    tens_rule=TensRule.TENS_FIRST,
    compound=" e ",
    hundred="cem",
    hundreds=("", "cem", "duzentos", "trezentos", "quatrocentos", "quinhentos",
              "seiscentos", "setecentos", "oitocentos", "novecentos"),
    scales=((1_000_000, ("um milhão", "milhões", "milhões")), (1_000, "mil")),
    point="vírgula",
    units={"%": ("por cento", "por cento"), "ms": ("milissegundo", "milissegundos"),
           "kb": ("kilobyte", "kilobytes"), "mb": ("megabyte", "megabytes"),
           "gb": ("gigabyte", "gigabytes"), "tb": ("terabyte", "terabytes"),
           "hz": ("hertz", "hertz"), "khz": ("quilohertz", "quilohertz")},
)

DUTCH = LanguagePack(
    code="nl",
    label="Dutch",
    endonym="Nederlands",
    negations=("niet", "geen", "nooit", "zonder", "niets", "noch"),
    intensifiers=("heel", "erg", "zeer", "echt", "extreem", "totaal", "volledig"),
    hedges=("misschien", "mogelijk", "lijkt", "waarschijnlijk", "enigszins"),
    clause_breaks=("maar", "echter", "hoewel", "toch"),
    cues={
        Emotion.EXCITED: ("ongelooflijk", "fantastisch", "geweldig", "prachtig", "perfect", "uitstekend"),
        Emotion.HAPPY: ("goed", "bedankt", "succes", "blij", "opgelost", "gerepareerd", "werkt"),
        Emotion.CONFIDENT: ("zeker", "bevestigd", "geverifieerd", "natuurlijk"),
        Emotion.CURIOUS: ("interessant", "nieuwsgierig"),
        Emotion.CALM: ("rustig", "stabiel", "kalm"),
        Emotion.CONCERNED: ("waarschuwing", "voorzichtig", "risico", "gevaar", "instabiel"),
        Emotion.SERIOUS: ("kritiek", "dringend", "ernstig", "beveiliging", "kwetsbaarheid"),
        Emotion.SAD: ("sorry", "helaas", "fout", "mislukt", "kapot", "verloren", "storing"),
    },
    ones=("nul", "een", "twee", "drie", "vier", "vijf", "zes", "zeven", "acht",
          "negen", "tien", "elf", "twaalf", "dertien", "veertien", "vijftien",
          "zestien", "zeventien", "achttien", "negentien"),
    tens=("", "", "twintig", "dertig", "veertig", "vijftig", "zestig", "zeventig", "tachtig", "negentig"),
    tens_rule=TensRule.ONES_FIRST,
    # "en" after a vowel takes a diaeresis in Dutch: tweeënveertig, not
    # tweeenveertig. Handled by _dutch_diaeresis at read time.
    compound="en",
    hundred="honderd",
    join="",
    scale_join="",
    scales=((1_000_000, (" miljoen ", " miljoen ", " miljoen ")), (1_000, "duizend")),
    point="komma",
    units={"%": ("procent", "procent"), "ms": ("milliseconde", "milliseconden"),
           "kb": ("kilobyte", "kilobytes"), "mb": ("megabyte", "megabytes"),
           "gb": ("gigabyte", "gigabytes"), "tb": ("terabyte", "terabytes"),
           "hz": ("hertz", "hertz"), "khz": ("kilohertz", "kilohertz")},
)

SWEDISH = LanguagePack(
    code="sv",
    label="Swedish",
    endonym="Svenska",
    negations=("inte", "ingen", "inget", "aldrig", "utan", "varken"),
    intensifiers=("mycket", "verkligen", "extremt", "totalt", "helt", "väldigt"),
    hedges=("kanske", "möjligen", "verkar", "troligen", "något"),
    clause_breaks=("men", "dock", "fastän", "ändå"),
    cues={
        Emotion.EXCITED: ("otroligt", "fantastiskt", "underbart", "perfekt", "utmärkt"),
        Emotion.HAPPY: ("bra", "tack", "framgång", "glad", "löst", "fixat", "fungerar"),
        Emotion.CONFIDENT: ("säkert", "bekräftat", "verifierat", "definitivt"),
        Emotion.CURIOUS: ("intressant", "nyfiken"),
        Emotion.CALM: ("lugn", "stabil"),
        Emotion.CONCERNED: ("varning", "försiktig", "risk", "fara", "instabil"),
        Emotion.SERIOUS: ("kritisk", "brådskande", "allvarlig", "säkerhet", "sårbarhet"),
        Emotion.SAD: ("förlåt", "tyvärr", "fel", "misslyckades", "trasig", "förlorad", "avbrott"),
    },
    ones=("noll", "ett", "två", "tre", "fyra", "fem", "sex", "sju", "åtta",
          "nio", "tio", "elva", "tolv", "tretton", "fjorton", "femton",
          "sexton", "sjutton", "arton", "nitton"),
    tens=("", "", "tjugo", "trettio", "fyrtio", "femtio", "sextio", "sjuttio", "åttio", "nittio"),
    tens_rule=TensRule.TENS_FIRST,
    compound="",
    hundred="hundra",
    join="",
    scale_join="",
    scales=((1_000_000, (" en miljon ", " miljoner ", " miljoner ")), (1_000, "tusen")),
    point="komma",
    units={"%": ("procent", "procent"), "ms": ("millisekund", "millisekunder"),
           "kb": ("kilobyte", "kilobyte"), "mb": ("megabyte", "megabyte"),
           "gb": ("gigabyte", "gigabyte"), "tb": ("terabyte", "terabyte"),
           "hz": ("hertz", "hertz"), "khz": ("kilohertz", "kilohertz")},
)

POLISH = LanguagePack(
    code="pl",
    label="Polish",
    endonym="Polski",
    negations=("nie", "nigdy", "bez", "żaden", "żadna", "nic", "ani"),
    intensifiers=("bardzo", "naprawdę", "niezwykle", "całkowicie", "zupełnie", "wyjątkowo"),
    hedges=("może", "prawdopodobnie", "wydaje się", "chyba", "nieco"),
    clause_breaks=("ale", "jednak", "chociaż", "mimo to"),
    cues={
        Emotion.EXCITED: ("niesamowite", "fantastyczne", "wspaniałe", "doskonałe", "świetne"),
        Emotion.HAPPY: ("dobrze", "dziękuję", "sukces", "zadowolony", "naprawione", "działa", "rozwiązane"),
        Emotion.CONFIDENT: ("na pewno", "potwierdzone", "zweryfikowane", "oczywiście"),
        Emotion.CURIOUS: ("ciekawe", "interesujące"),
        Emotion.CALM: ("spokojnie", "stabilne"),
        Emotion.CONCERNED: ("uwaga", "ostrożnie", "ryzyko", "niebezpieczeństwo", "ostrzeżenie"),
        Emotion.SERIOUS: ("krytyczne", "pilne", "poważne", "bezpieczeństwo", "podatność"),
        Emotion.SAD: ("przepraszam", "niestety", "błąd", "nie powiodło się", "zepsute", "utracone", "awaria"),
    },
    ones=("zero", "jeden", "dwa", "trzy", "cztery", "pięć", "sześć", "siedem", "osiem",
          "dziewięć", "dziesięć", "jedenaście", "dwanaście", "trzynaście", "czternaście",
          "piętnaście", "szesnaście", "siedemnaście", "osiemnaście", "dziewiętnaście"),
    tens=("", "", "dwadzieścia", "trzydzieści", "czterdzieści", "pięćdziesiąt",
          "sześćdziesiąt", "siedemdziesiąt", "osiemdziesiąt", "dziewięćdziesiąt"),
    tens_rule=TensRule.TENS_FIRST,
    hundred="sto",
    hundreds=("", "sto", "dwieście", "trzysta", "czterysta", "pięćset",
              "sześćset", "siedemset", "osiemset", "dziewięćset"),
    scales=((1_000_000, ("milion", "miliony", "milionów")),
            (1_000, ("tysiąc", "tysiące", "tysięcy"))),
    point="przecinek",
    units={"%": ("procent", "procent"), "ms": ("milisekunda", "milisekundy"),
           "kb": ("kilobajt", "kilobajty"), "mb": ("megabajt", "megabajty"),
           "gb": ("gigabajt", "gigabajty"), "tb": ("terabajt", "terabajty"),
           "hz": ("herc", "herce"), "khz": ("kiloherc", "kiloherce")},
)

RUSSIAN = LanguagePack(
    code="ru",
    label="Russian",
    endonym="Русский",
    negations=("не", "нет", "никогда", "без", "ни", "ничего", "никакой"),
    intensifiers=("очень", "действительно", "крайне", "совершенно", "полностью", "чрезвычайно"),
    hedges=("может быть", "возможно", "кажется", "вероятно", "немного"),
    clause_breaks=("но", "однако", "хотя", "зато"),
    cues={
        Emotion.EXCITED: ("невероятно", "фантастика", "потрясающе", "отлично", "превосходно"),
        Emotion.HAPPY: ("хорошо", "спасибо", "успех", "рад", "исправлено", "работает", "решено"),
        Emotion.CONFIDENT: ("конечно", "подтверждено", "проверено", "определённо"),
        Emotion.CURIOUS: ("интересно", "любопытно"),
        Emotion.CALM: ("спокойно", "стабильно"),
        Emotion.CONCERNED: ("внимание", "осторожно", "риск", "опасность", "предупреждение"),
        Emotion.SERIOUS: ("критично", "срочно", "серьёзно", "безопасность", "уязвимость"),
        Emotion.SAD: ("извините", "к сожалению", "ошибка", "не удалось", "сломано", "потеряно", "сбой"),
    },
    ones=("ноль", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь",
          "девять", "десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать",
          "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"),
    tens=("", "", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят",
          "семьдесят", "восемьдесят", "девяносто"),
    tens_rule=TensRule.TENS_FIRST,
    hundred="сто",
    hundreds=("", "сто", "двести", "триста", "четыреста", "пятьсот",
              "шестьсот", "семьсот", "восемьсот", "девятьсот"),
    scales=((1_000_000, ("миллион", "миллиона", "миллионов")),
            (1_000, ("тысяча", "тысячи", "тысяч"))),
    point="запятая",
    units={"%": ("процент", "процентов"), "ms": ("миллисекунда", "миллисекунд"),
           "kb": ("килобайт", "килобайт"), "mb": ("мегабайт", "мегабайт"),
           "gb": ("гигабайт", "гигабайт"), "tb": ("терабайт", "терабайт"),
           "hz": ("герц", "герц"), "khz": ("килогерц", "килогерц")},
)

UKRAINIAN = LanguagePack(
    code="uk",
    label="Ukrainian",
    endonym="Українська",
    negations=("не", "ні", "ніколи", "без", "нічого", "жоден"),
    intensifiers=("дуже", "справді", "надзвичайно", "повністю", "цілком"),
    hedges=("можливо", "мабуть", "здається", "ймовірно", "трохи"),
    clause_breaks=("але", "проте", "хоча", "однак"),
    cues={
        Emotion.EXCITED: ("неймовірно", "фантастично", "чудово", "відмінно"),
        Emotion.HAPPY: ("добре", "дякую", "успіх", "радий", "виправлено", "працює", "вирішено"),
        Emotion.CONFIDENT: ("звичайно", "підтверджено", "перевірено", "безумовно"),
        Emotion.CURIOUS: ("цікаво", "допитливо"),
        Emotion.CALM: ("спокійно", "стабільно"),
        Emotion.CONCERNED: ("увага", "обережно", "ризик", "небезпека", "попередження"),
        Emotion.SERIOUS: ("критично", "терміново", "серйозно", "безпека", "вразливість"),
        Emotion.SAD: ("вибачте", "на жаль", "помилка", "не вдалося", "зламано", "втрачено", "збій"),
    },
    ones=("нуль", "один", "два", "три", "чотири", "п'ять", "шість", "сім", "вісім",
          "дев'ять", "десять", "одинадцять", "дванадцять", "тринадцять", "чотирнадцять",
          "п'ятнадцять", "шістнадцять", "сімнадцять", "вісімнадцять", "дев'ятнадцять"),
    tens=("", "", "двадцять", "тридцять", "сорок", "п'ятдесят", "шістдесят",
          "сімдесят", "вісімдесят", "дев'яносто"),
    tens_rule=TensRule.TENS_FIRST,
    hundred="сто",
    hundreds=("", "сто", "двісті", "триста", "чотириста", "п'ятсот",
              "шістсот", "сімсот", "вісімсот", "дев'ятсот"),
    scales=((1_000_000, ("мільйон", "мільйони", "мільйонів")),
            (1_000, ("тисяча", "тисячі", "тисяч"))),
    point="кома",
    units={"%": ("відсоток", "відсотків"), "ms": ("мілісекунда", "мілісекунд"),
           "gb": ("гігабайт", "гігабайт"), "mb": ("мегабайт", "мегабайт")},
)

GREEK = LanguagePack(
    code="el",
    label="Greek",
    endonym="Ελληνικά",
    negations=("δεν", "όχι", "ποτέ", "χωρίς", "τίποτα", "μην", "ούτε"),
    intensifiers=("πολύ", "πραγματικά", "εξαιρετικά", "τελείως", "απόλυτα"),
    hedges=("ίσως", "πιθανώς", "φαίνεται", "μάλλον", "κάπως"),
    clause_breaks=("αλλά", "όμως", "παρόλο", "ωστόσο"),
    cues={
        Emotion.EXCITED: ("απίστευτο", "φανταστικό", "υπέροχο", "τέλειο", "εξαιρετικό"),
        Emotion.HAPPY: ("καλά", "ευχαριστώ", "επιτυχία", "χαρούμενος", "διορθώθηκε", "λειτουργεί"),
        Emotion.CONFIDENT: ("σίγουρα", "επιβεβαιώθηκε", "επαληθεύτηκε", "βεβαίως"),
        Emotion.CURIOUS: ("ενδιαφέρον", "περίεργο"),
        Emotion.CALM: ("ήρεμα", "σταθερό"),
        Emotion.CONCERNED: ("προσοχή", "κίνδυνος", "ρίσκο", "προειδοποίηση"),
        Emotion.SERIOUS: ("κρίσιμο", "επείγον", "σοβαρό", "ασφάλεια", "ευπάθεια"),
        Emotion.SAD: ("συγγνώμη", "δυστυχώς", "σφάλμα", "απέτυχε", "χαλασμένο", "χάθηκε"),
    },
    ones=("μηδέν", "ένα", "δύο", "τρία", "τέσσερα", "πέντε", "έξι", "επτά", "οκτώ",
          "εννέα", "δέκα", "έντεκα", "δώδεκα", "δεκατρία", "δεκατέσσερα", "δεκαπέντε",
          "δεκαέξι", "δεκαεπτά", "δεκαοκτώ", "δεκαεννέα"),
    tens=("", "", "είκοσι", "τριάντα", "σαράντα", "πενήντα", "εξήντα",
          "εβδομήντα", "ογδόντα", "ενενήντα"),
    tens_rule=TensRule.TENS_FIRST,
    hundred="εκατό",
    hundreds=("", "εκατό", "διακόσια", "τριακόσια", "τετρακόσια", "πεντακόσια",
              "εξακόσια", "επτακόσια", "οκτακόσια", "εννιακόσια"),
    scales=((1_000_000, ("ένα εκατομμύριο", "εκατομμύρια", "εκατομμύρια")),
            (1_000, ("χίλια", "χιλιάδες", "χιλιάδες"))),
    point="κόμμα",
    units={"%": ("τοις εκατό", "τοις εκατό"), "ms": ("χιλιοστό", "χιλιοστά"),
           "gb": ("γιγκαμπάιτ", "γιγκαμπάιτ"), "mb": ("μεγκαμπάιτ", "μεγκαμπάιτ")},
)

TURKISH = LanguagePack(
    code="tr",
    label="Turkish",
    endonym="Türkçe",
    negations=("değil", "yok", "hiç", "asla", "olmadan", "hiçbir"),
    intensifiers=("çok", "gerçekten", "son derece", "tamamen", "aşırı"),
    hedges=("belki", "muhtemelen", "görünüyor", "sanırım", "biraz"),
    clause_breaks=("ama", "fakat", "ancak", "yine de"),
    cues={
        Emotion.EXCITED: ("inanılmaz", "harika", "muhteşem", "mükemmel"),
        Emotion.HAPPY: ("iyi", "teşekkürler", "başarı", "mutlu", "düzeltildi", "çalışıyor", "çözüldü"),
        Emotion.CONFIDENT: ("kesinlikle", "onaylandı", "doğrulandı", "elbette"),
        Emotion.CURIOUS: ("ilginç", "merak"),
        Emotion.CALM: ("sakin", "istikrarlı"),
        Emotion.CONCERNED: ("dikkat", "risk", "tehlike", "uyarı"),
        Emotion.SERIOUS: ("kritik", "acil", "ciddi", "güvenlik", "güvenlik açığı"),
        Emotion.SAD: ("üzgünüm", "maalesef", "hata", "başarısız", "bozuk", "kayıp", "çöktü"),
    },
    ones=("sıfır", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz",
          "dokuz", "on", "on bir", "on iki", "on üç", "on dört", "on beş",
          "on altı", "on yedi", "on sekiz", "on dokuz"),
    tens=("", "", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"),
    tens_rule=TensRule.TENS_FIRST,
    hundred="yüz",
    scales=((1_000_000, "milyon"), (1_000, "bin")),
    point="virgül",
    units={"%": ("yüzde", "yüzde"), "ms": ("milisaniye", "milisaniye"),
           "gb": ("gigabayt", "gigabayt"), "mb": ("megabayt", "megabayt")},
)

WESTERN = (
    ENGLISH, SPANISH, FRENCH, GERMAN, ITALIAN, PORTUGUESE, DUTCH, SWEDISH,
    POLISH, RUSSIAN, UKRAINIAN, GREEK, TURKISH,
)
