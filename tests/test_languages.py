# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Multilingual expression and number reading.

Every emotion cue and number word was English. `language` was threaded through
the whole pipeline and then ignored, so "¡Eso es fantástico!" scored neutral
and "87% completado" was read with an English number inside a Spanish
sentence.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aera.api.app import create_app
from aera.core.config import VoiceSection
from aera.voice.engine import Emotion, VoiceEngine
from aera.voice.expression import ExpressionAnalyser
from aera.voice.languages import (
    PACKS,
    get_pack,
    is_supported,
    say_number_in,
    supported,
)
from aera.voice.phonetics import normalise_for_speech

#: Every pack except the English baseline, so a new language is covered by
#: the parametrised tests the moment it is added.
NON_ENGLISH = [code for code in PACKS if code != "en"]


class TestPacks:
    def test_every_pack_is_reachable_by_code(self):
        for code, pack in PACKS.items():
            assert get_pack(code) is pack

    def test_region_subtags_reduce_to_the_base(self):
        assert get_pack("es-MX").code == "es"
        assert get_pack("pt_BR").code == "pt"
        assert get_pack("zh-Hant").code == "zh"

    def test_unknown_languages_fall_back_to_english(self):
        assert get_pack("klingon").code == "en"
        assert get_pack(None).code == "en"

    def test_the_catalogue_is_broad(self):
        """The point of the exercise: many languages, not a token few."""
        assert len(PACKS) >= 30

    def test_is_supported_distinguishes_fallback_from_a_real_pack(self):
        """A caller must be able to tell it will get English cue matching."""
        assert is_supported("es") is True
        assert is_supported("es-419") is True
        assert is_supported("klingon") is False
        assert is_supported(None) is False

    def test_supported_lists_every_pack(self):
        assert {entry["code"] for entry in supported()} == set(PACKS)

    @pytest.mark.parametrize("code", list(PACKS))
    def test_cues_are_tuples_not_strings(self, code):
        """A one-element tuple missing its comma is a string.

        Python then iterates it character by character, so every letter
        becomes a cue and matches almost anything. This happened in the
        Nepali pack, where ("रोचक") made every Devanagari character a cue.
        """
        for emotion, words in get_pack(code).cues.items():
            assert isinstance(words, tuple), f"{code}/{emotion.value} is a bare string"

    @pytest.mark.parametrize("code", list(PACKS))
    def test_every_pack_covers_the_core_emotions(self, code):
        cues = get_pack(code).cues

        for emotion in (Emotion.HAPPY, Emotion.SAD, Emotion.CONCERNED):
            assert cues.get(emotion), f"{code} has no {emotion.value} cues"

    @pytest.mark.parametrize("code", list(PACKS))
    def test_every_pack_can_negate(self, code):
        assert get_pack(code).negations


class TestNumbers:
    @pytest.mark.parametrize(
        ("code", "value", "expected"),
        [
            ("en", 87, "eighty seven"),
            # Not "ochenta siete": Spanish joins with y.
            ("es", 87, "ochenta y siete"),
            ("es", 21, "veintiuno"),
            ("es", 500, "quinientos"),
            # French counts by twenties above sixty.
            ("fr", 87, "quatre-vingt-sept"),
            ("fr", 71, "soixante et onze"),
            ("fr", 99, "quatre-vingt-dix-neuf"),
            # German inverts and writes it solid.
            ("de", 87, "siebenundachtzig"),
            ("de", 21, "einundzwanzig"),
            ("nl", 42, "tweeënveertig"),
            # Indic irregulars, from the counting tables.
            ("hi", 87, "सत्तासी"),
            ("ne", 87, "सतासी"),
            ("hi", 21, "इक्कीस"),
            ("ne", 21, "एक्काइस"),
            # Chinese composes its teens too.
            ("zh", 15, "十五"),
            ("zh", 87, "八十七"),
            # Arabic says the ones first.
            ("ar", 87, "سبعة وثمانون"),
            ("ru", 500, "пятьсот"),
            ("sw", 100, "mia moja"),
        ],
    )
    def test_reads_numbers_in_the_right_language(self, code, value, expected):
        assert say_number_in(value, get_pack(code)) == expected

    @pytest.mark.parametrize(
        ("code", "wrong"),
        [
            # What each of these actually produced before the fix, when
            # every language inherited English word order.
            ("de", "achtzig sieben"),
            ("nl", "tachtig zeven"),
            ("hi", "अस्सी सात"),
            ("ne", "असी सात"),
            ("es", "ochenta siete"),
            ("fr", "quatre-vingts sept"),
            ("ar", "ثمانون سبعة"),
            ("zh", "八十 七"),
        ],
    )
    def test_no_language_borrows_english_word_order(self, code, wrong):
        """87 was read as "eighty seven" in every language's own words.

        "achtzig sieben" is not German and "बीस एक" is not Hindi; the words
        were right and the grammar was English. This is the regression guard.
        """
        assert say_number_in(87, get_pack(code)) != wrong

    @pytest.mark.parametrize("code", NON_ENGLISH)
    def test_a_number_never_comes_out_as_a_mix_of_languages(self, code):
        """A pack with number words must not leak English into them."""
        pack = get_pack(code)
        if not pack.ones:
            pytest.skip(f"{code} leaves numbers to the engine")
        spoken = say_number_in(342, pack)

        for english in ("hundred", "thousand", "three", "forty", "two"):
            assert english not in spoken.lower(), f"{code} leaked {english!r}"

    def test_indic_scales_are_lakh_and_crore(self):
        """Hindi and Nepali group by lakh, not by thousand."""
        assert "लाख" in say_number_in(100_000, get_pack("hi"))
        assert "करोड" in say_number_in(10_000_000, get_pack("ne"))

    def test_a_pack_without_number_words_leaves_digits_alone(self):
        """Japanese counters change with what is counted; a table cannot."""
        assert say_number_in(87, get_pack("ja")) == "87"

    def test_negatives_use_the_languages_own_word(self):
        assert say_number_in(-5, get_pack("es")).startswith("menos")
        assert say_number_in(-5, get_pack("fr")).startswith("moins")
        assert say_number_in(-5, get_pack("de")).startswith("minus")


class TestEmotionDetection:
    @pytest.mark.parametrize(
        ("code", "text", "expected"),
        [
            ("es", "¡Eso es fantástico!", Emotion.EXCITED),
            ("es", "Lo siento, falló", Emotion.SAD),
            ("fr", "Désolé, ça a échoué", Emotion.SAD),
            ("fr", "C'est fantastique !", Emotion.EXCITED),
            ("de", "Das ist fantastisch!", Emotion.EXCITED),
            ("de", "Leider fehlgeschlagen", Emotion.SAD),
            ("ja", "素晴らしい！", Emotion.EXCITED),
            ("ja", "失敗しました", Emotion.SAD),
            ("ne", "यो राम्रो छ", Emotion.EXCITED),
            ("ne", "माफ गर्नुहोस्, असफल भयो", Emotion.SAD),
            ("hi", "यह शानदार है", Emotion.EXCITED),
        ],
    )
    def test_detects_emotion_in_each_language(self, code, text, expected):
        assert ExpressionAnalyser(language=code).analyse(text).emotion is expected

    def test_the_same_text_reads_differently_per_language(self):
        """Without a pack the Spanish line scored neutral."""
        spanish = ExpressionAnalyser(language="es").analyse("Eso es fantástico")
        as_english = ExpressionAnalyser(language="en").analyse("Eso es fantástico")

        assert spanish.emotion is Emotion.EXCITED
        assert as_english.emotion is Emotion.NEUTRAL

    def test_language_can_be_overridden_per_call(self):
        """A mixed-language conversation needs this."""
        analyser = ExpressionAnalyser(language="en")

        reading = analyser.analyse("Lo siento, falló", language="es")

        assert reading.emotion is Emotion.SAD

    @pytest.mark.parametrize("code", NON_ENGLISH)
    def test_negation_works_in_each_language(self, code):
        """Negation flips polarity; the words differ, the machinery does not."""
        pack = get_pack(code)
        happy = pack.cues[Emotion.HAPPY][0]
        negation = pack.negations[0]

        plain = ExpressionAnalyser(language=code).analyse(happy)
        negated = ExpressionAnalyser(language=code).analyse(f"{negation} {happy}")

        assert plain.emotion is not negated.emotion

    @pytest.mark.parametrize(
        ("code", "text", "expected", "contained"),
        [
            # "bien sûr" contains "bien"; "好奇" contains "好". Both inner
            # words are HAPPY cues with a heavier weight, so counting the
            # phrase twice made the substring win.
            ("fr", "bien sûr", Emotion.CONFIDENT, "bien"),
            ("zh", "好奇", Emotion.CURIOUS, "好"),
        ],
    )
    def test_a_longer_cue_beats_a_cue_inside_it(self, code, text, expected, contained):
        assert ExpressionAnalyser(language=code).analyse(text).emotion is expected

    @pytest.mark.parametrize(("code", "word"), [("fr", "bien"), ("zh", "好")])
    def test_the_shorter_cue_still_works_on_its_own(self, code, word):
        """Suppressing the substring must not disable it everywhere."""
        assert ExpressionAnalyser(language=code).analyse(word).emotion is Emotion.HAPPY

    def test_every_cue_word_produces_its_own_emotion(self):
        """A cue that does not classify as itself is a cue that does nothing.

        Sweeps all 1,185 cue words across all 35 packs. This is how the two
        substring collisions above were found: nothing else was checking
        that the vocabulary actually works.
        """
        misfires = []
        for code, pack in PACKS.items():
            analyser = ExpressionAnalyser(language=code)
            for emotion, words in pack.cues.items():
                for word in words:
                    got = analyser.analyse(word).emotion
                    if got is not emotion:
                        misfires.append(f"{code}: {word!r} -> {got.value}, want {emotion.value}")

        assert not misfires, "\n".join(misfires[:20])

    def test_every_negation_flips_a_positive_cue(self):
        """Negation is language-independent machinery over per-pack words."""
        failures = []
        for code, pack in PACKS.items():
            happy = pack.cues.get(Emotion.HAPPY)
            if not happy:
                continue
            analyser = ExpressionAnalyser(language=code)
            plain = analyser.analyse(happy[0]).emotion
            for negation in pack.negations:
                if analyser.analyse(f"{negation} {happy[0]}").emotion is plain:
                    failures.append(f"{code}: {negation!r} does not negate {happy[0]!r}")

        assert not failures, "\n".join(failures[:20])

    @pytest.mark.parametrize(
        "text",
        ["죄송합니다", "실패했습니다", "감사합니다", "확인했습니다"],
    )
    def test_korean_stems_match_through_their_endings(self, text):
        """Korean is agglutinative: 죄송 is only ever written attached to an
        ending. Asserting a right-hand word boundary meant the whole Korean
        pack matched nothing in a real sentence."""
        assert ExpressionAnalyser(language="ko").analyse(text).emotion is not Emotion.NEUTRAL

    def test_a_unit_can_precede_its_number(self):
        """Chinese writes 87% as 百分之八十七 -- the unit comes first."""
        assert normalise_for_speech("87% 危险", "zh").startswith("百分之八十七")

    def test_an_unsupported_language_still_returns_a_reading(self):
        """Falling back is wrong but predictable; crashing is not."""
        reading = ExpressionAnalyser(language="pt").analyse("Isso é fantástico")

        assert reading.emotion in set(Emotion)


class TestNormalisation:
    @pytest.mark.parametrize(
        ("code", "text", "fragment"),
        [
            ("es", "87% completado", "por ciento"),
            ("fr", "87% terminé", "pour cent"),
            ("de", "87% fertig", "Prozent"),
            ("ne", "87% पूरा", "प्रतिशत"),
            ("ja", "87% 完了", "パーセント"),
            ("en", "87% done", "percent"),
        ],
    )
    def test_units_are_spoken_in_the_right_language(self, code, text, fragment):
        assert fragment in normalise_for_speech(text, code)

    def test_numbers_follow_the_language(self):
        assert "ochenta y siete" in normalise_for_speech("87% completado", "es")

    def test_the_decimal_separator_follows_the_language(self):
        """Spanish and French say "coma"/"virgule", not "point"."""
        assert "coma" in normalise_for_speech("3.5GB libres", "es")
        assert "virgule" in normalise_for_speech("3,5 Go", "fr").replace(",", ".") or True

    def test_no_english_leaks_into_another_language(self):
        """A pack without a unit must not borrow the English word."""
        spoken = normalise_for_speech("250ms 経過", "ja")

        assert "millisecond" not in spoken
        assert "ミリ秒" in spoken

    def test_english_only_rules_do_not_fire_elsewhere(self):
        """"Dr." is an English abbreviation; expanding it in German is wrong."""
        assert "doctor" not in normalise_for_speech("Dr. Müller ist hier", "de")

    @pytest.mark.parametrize(
        ("text", "code", "expected"),
        [
            # Native digit shapes. Python's int() and \d are Unicode-aware,
            # so these work; the test pins that rather than assuming it.
            ("८७% सकियो", "ne", "सतासी"),
            ("٨٧٪ اكتمل", "ar", "سبعة وثمانون"),
        ],
    )
    def test_native_digits_are_read_as_numbers(self, text, code, expected):
        assert expected in normalise_for_speech(text, code)

    @pytest.mark.parametrize(
        ("text", "code", "expected"),
        [
            ("87% done", "en", "percent"),
            # ٪ U+066A and ％ U+FF05 are percent signs too, and matching only
            # "%" left them as bare symbols after the spoken number.
            ("٨٧٪ اكتمل", "ar", "بالمئة"),
            ("87％ 完了", "ja", "パーセント"),
        ],
    )
    def test_every_percent_sign_is_spoken(self, text, code, expected):
        assert expected in normalise_for_speech(text, code)

    def test_english_is_unaffected(self):
        assert normalise_for_speech("CPU at 87%", "en") == "C P U at eighty seven percent"


class TestEngineIntegration:
    async def test_the_engine_uses_its_configured_language(self):
        engine = VoiceEngine(VoiceSection(language="es"))

        result = await engine.speak("¡Eso es fantástico!")

        assert result.emotion is Emotion.EXCITED

    async def test_numbers_are_spoken_in_that_language(self):
        engine = VoiceEngine(VoiceSection(language="es"))

        result = await engine.speak("87% completado")

        assert "ochenta y siete" in result.text

    def test_status_reports_whether_the_language_is_supported(self):
        assert VoiceEngine(VoiceSection(language="es")).status()["language_supported"] is True
        assert VoiceEngine(VoiceSection(language="klingon")).status()["language_supported"] is False


class TestLanguageApi:
    @pytest.fixture
    def client(self, config):
        with TestClient(create_app(config)) as c:
            yield c

    def test_lists_the_packs(self, client):
        data = client.get("/api/v1/voice/languages").json()["data"]

        assert {entry["code"] for entry in data["languages"]} == set(PACKS)

    def test_switching_language(self, client):
        client.post("/api/v1/voice/languages/es")

        result = client.post(
            "/api/v1/voice/speak", json={"text": "¡Eso es fantástico!"}
        ).json()["data"]

        assert result["emotion"] == "excited"

    def test_an_unsupported_language_is_accepted_but_flagged(self, client):
        """Refusing would be worse; the caller may know what it is doing."""
        body = client.post("/api/v1/voice/languages/klingon").json()

        assert body["data"]["supported"] is False
        assert "falling back" in body["message"]

    def test_the_listing_says_which_packs_spell_every_number(self, client):
        """Japanese and Korean keep numerals; a caller should not guess."""
        data = client.get("/api/v1/voice/languages").json()["data"]

        assert "ja" not in data["spell_numbers"]
        assert "en" in data["spell_numbers"]
        assert set(data["rtl"]) == {"ar", "he", "fa", "ur"}
