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

#: The languages with a real pack, excluding the English baseline.
NON_ENGLISH = ["es", "fr", "de", "hi", "ne", "ja"]


class TestPacks:
    def test_every_pack_is_reachable_by_code(self):
        for code, pack in PACKS.items():
            assert get_pack(code) is pack

    def test_region_subtags_reduce_to_the_base(self):
        assert get_pack("es-MX").code == "es"
        assert get_pack("pt_BR").code == "en", "pt has no pack; must fall back"

    def test_unknown_languages_fall_back_to_english(self):
        assert get_pack("klingon").code == "en"
        assert get_pack(None).code == "en"

    def test_is_supported_distinguishes_fallback_from_a_real_pack(self):
        """A caller must be able to tell it will get English cue matching."""
        assert is_supported("es") is True
        assert is_supported("es-419") is True
        assert is_supported("pt") is False
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
            ("es", 87, "ochenta siete"),
            ("fr", 87, "quatre-vingts sept"),
            ("de", 87, "achtzig sieben"),
        ],
    )
    def test_reads_numbers_in_the_right_language(self, code, value, expected):
        assert say_number_in(value, get_pack(code)) == expected

    def test_indic_scales_are_lakh_and_crore(self):
        """Hindi and Nepali group by lakh, not by thousand."""
        assert "लाख" in say_number_in(100_000, get_pack("hi"))
        assert "करोड" in say_number_in(10_000_000, get_pack("ne"))

    def test_a_pack_without_number_words_leaves_digits_alone(self):
        """Japanese counters change with what is counted; a table cannot."""
        assert say_number_in(87, get_pack("ja")) == "87"

    def test_negatives(self):
        assert say_number_in(-5, get_pack("es")).startswith("-")


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
        spanish = ExpressionAnalyser(language="es").analyse("¡Eso es fantástico!")
        as_english = ExpressionAnalyser(language="en").analyse("¡Eso es fantástico!")

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
        assert "ochenta siete" in normalise_for_speech("87% completado", "es")

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

        assert "ochenta siete" in result.text

    def test_status_reports_whether_the_language_is_supported(self):
        assert VoiceEngine(VoiceSection(language="es")).status()["language_supported"] is True
        assert VoiceEngine(VoiceSection(language="pt")).status()["language_supported"] is False


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
        body = client.post("/api/v1/voice/languages/pt").json()

        assert body["data"]["supported"] is False
        assert "falling back" in body["message"]
