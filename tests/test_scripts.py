# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Lip-sync outside the Latin alphabet.

Visemes were derived from Latin letters, so every other script fell through
to a single ``"neutral"``: one mouth shape for a whole Devanagari, Cyrillic,
Arabic, Kana, Hangul, Han or Thai word. The avatar's mouth sat still while
AERA spoke. With one language that was a corner case; with thirty-five it is
most of them.
"""

from __future__ import annotations

import pytest

from aera.voice.languages import PACKS, get_pack
from aera.voice.phonetics import word_to_visemes
from aera.voice.scripts import (
    ALPHABETIC,
    RTL_SCRIPTS,
    Script,
    detect_script,
    runs,
    shapes_for,
)

#: One real word per script, with what it means, so a failure is readable.
SAMPLES = [
    ("make", Script.LATIN, "English"),
    ("français", Script.LATIN, "French, with a cedilla"),
    ("привет", Script.CYRILLIC, "Russian hello"),
    ("Ελλάδα", Script.GREEK, "Greece"),
    ("مرحبا", Script.ARABIC, "Arabic hello"),
    ("שלום", Script.HEBREW, "Hebrew hello"),
    ("नमस्ते", Script.DEVANAGARI, "Hindi hello"),
    ("বাংলা", Script.BENGALI, "Bengali"),
    ("ਪੰਜਾਬੀ", Script.GURMUKHI, "Punjabi"),
    ("ગુજરાતી", Script.GUJARATI, "Gujarati"),
    ("தமிழ்", Script.TAMIL, "Tamil"),
    ("తెలుగు", Script.TELUGU, "Telugu"),
    ("ಕನ್ನಡ", Script.KANNADA, "Kannada"),
    ("മലയാളം", Script.MALAYALAM, "Malayalam"),
    ("සිංහල", Script.SINHALA, "Sinhala"),
    ("สวัสดี", Script.THAI, "Thai hello"),
    ("こんにちは", Script.KANA, "Japanese hello"),
    ("안녕하세요", Script.HANGUL, "Korean hello"),
    ("你好", Script.HAN, "Chinese hello"),
]


class TestScriptDetection:
    @pytest.mark.parametrize(("text", "script", "gloss"), SAMPLES)
    def test_identifies_the_script(self, text, script, gloss):
        assert detect_script(text) is script, gloss

    def test_mixed_text_reports_the_dominant_script(self):
        """A Hindi sentence quoting an English name is still Hindi."""
        assert detect_script("यो AERA हो") is Script.DEVANAGARI

    def test_punctuation_and_digits_carry_no_script(self):
        assert detect_script("123 -- !?") is Script.OTHER

    def test_runs_split_at_script_changes(self):
        """Each run has to be read by its own rules."""
        split = runs("AERA का status")

        assert [script for script, _ in split] == [
            Script.LATIN,
            Script.DEVANAGARI,
            Script.LATIN,
        ]

    def test_runs_drop_soundless_characters(self):
        assert "".join(text for _, text in runs("a, b! c?")) == "abc"

    def test_right_to_left_scripts_are_known(self):
        assert Script.ARABIC in RTL_SCRIPTS
        assert Script.HEBREW in RTL_SCRIPTS
        assert Script.LATIN not in RTL_SCRIPTS


class TestVisemes:
    @pytest.mark.parametrize(("text", "script", "gloss"), SAMPLES)
    def test_every_script_produces_more_than_one_shape(self, text, script, gloss):
        """The bug: one "neutral" for the whole word, so the mouth froze."""
        shapes = shapes_for(text)

        assert len(shapes) > 1, f"{gloss} collapsed to {shapes}"

    @pytest.mark.parametrize(("text", "script", "gloss"), SAMPLES)
    def test_shapes_are_valid_rig_positions(self, text, script, gloss):
        allowed = {"open", "narrow", "closed", "teeth", "tongue", "neutral"}

        assert set(shapes_for(text)) <= allowed, gloss

    @pytest.mark.parametrize(("text", "script", "gloss"), SAMPLES)
    def test_the_mouth_actually_opens(self, text, script, gloss):
        """Speech has vowels. A track with no open shape is not speech."""
        assert "open" in shapes_for(text), gloss

    def test_diacritics_do_not_lose_a_sound(self):
        """"français" and "francais" are the same mouth movements."""
        assert shapes_for("français") == shapes_for("francais")

    def test_accented_vowels_are_not_neutral(self):
        """Before folding, "está" dropped its final vowel to neutral."""
        assert "neutral" not in shapes_for("está")

    def test_devanagari_inherent_vowel_is_voiced(self):
        """A consonant carries an /a/ unless a sign or virama removes it.

        "नमस्ते" is six sounds written with four consonants; reading one
        shape per character loses half the word.
        """
        shapes = shapes_for("नमस्ते")

        assert len(shapes) >= 6

    def test_a_virama_suppresses_the_inherent_vowel(self):
        """The whole point of the abugida: क is "ka", क् is "k"."""
        assert len(shapes_for("क")) > len(shapes_for("क्"))

    def test_hangul_decomposes_into_jamo(self):
        """한 is three sounds -- h, a, n -- in one composed character."""
        assert len(shapes_for("한")) == 3

    def test_hangul_silent_onset_is_not_pronounced(self):
        """ㅇ is a placeholder in the onset, not a sound: 아 is one vowel."""
        assert shapes_for("아") == ["open"]

    def test_kana_labials_close_the_lips_first(self):
        """ま is m + a: the lips close, then open."""
        assert shapes_for("ま") == ["closed", "open"]

    def test_kana_n_closes_the_mouth(self):
        assert shapes_for("ん") == ["closed"]

    def test_arabic_diacritics_are_not_separate_shapes(self):
        """Short-vowel marks are written above the line, not articulated."""
        assert shapes_for("مَرْحَبا") == shapes_for("مرحبا")

    def test_thai_tone_marks_are_not_shapes(self):
        """Tone marks change pitch, not mouth position."""
        assert len(shapes_for("ก่")) == len(shapes_for("ก"))

    def test_han_gives_one_opening_per_syllable(self):
        """A Han character is one syllable, and the reading needs a
        dictionary AERA does not bundle. Timing is all that is claimed."""
        assert shapes_for("你好").count("open") == 2

    def test_mixed_script_text_is_read_run_by_run(self):
        both = shapes_for("AERA नमस्ते")

        assert len(both) > len(shapes_for("AERA"))
        assert len(both) > len(shapes_for("नमस्ते"))

    def test_alphabetic_scripts_are_declared(self):
        assert Script.DEVANAGARI in ALPHABETIC
        assert Script.HAN not in ALPHABETIC, "Han needs a reading dictionary"


class TestPhoneticsIntegration:
    """word_to_visemes is what the avatar actually calls."""

    def test_english_is_unchanged(self):
        assert word_to_visemes("make") == ["closed", "open", "tongue"]
        assert word_to_visemes("the") == ["tongue", "open"]

    def test_repeats_still_collapse(self):
        """"gg" in "trigger" is one mouth position, not two."""
        shapes = word_to_visemes("trigger")

        assert all(a != b for a, b in zip(shapes, shapes[1:], strict=False))

    def test_empty_and_numeric_input(self):
        assert word_to_visemes("") == []
        assert word_to_visemes("123") == []

    @pytest.mark.parametrize(("text", "script", "gloss"), SAMPLES)
    def test_no_script_returns_a_bare_neutral(self, text, script, gloss):
        """The exact regression: every non-Latin word gave ["neutral"]."""
        assert word_to_visemes(text) != ["neutral"], gloss


class TestPackScripts:
    @pytest.mark.parametrize("code", list(PACKS))
    def test_every_pack_reports_a_script(self, code):
        assert get_pack(code).script is not Script.OTHER

    @pytest.mark.parametrize("code", list(PACKS))
    def test_every_pack_can_animate_its_own_cue_words(self, code):
        """A language whose own vocabulary produces no mouth movement is a
        language the avatar cannot lip-sync."""
        pack = get_pack(code)
        word = next(iter(next(iter(pack.cues.values()))))

        assert len(shapes_for(word)) > 1, f"{code}: {word!r} gives no movement"

    def test_right_to_left_packs_are_flagged(self):
        assert {code for code in PACKS if get_pack(code).rtl} == {"ar", "he", "fa", "ur"}
