# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Spoken-form normalisation and phoneme-aligned visemes.

Three defects prompted this. A TTS engine reads what it is given, so "87%"
was spoken as a symbol. "Dr. Smith" took a full sentence pause mid-name
because the abbreviation's dot looked like a full stop. And the viseme track
had one mouth shape per *letter*, animating silent letters and holding a vowel
through pauses.
"""

from __future__ import annotations

import pytest

from aera.voice.engine import VoiceEngine
from aera.voice.expression import prosody_for
from aera.voice.phonetics import (
    normalise_for_speech,
    say_number,
    visemes_for_words,
    word_to_visemes,
)


class TestNumbers:
    @pytest.mark.parametrize(
        ("value", "spoken"),
        [
            (0, "zero"),
            (7, "seven"),
            (13, "thirteen"),
            (42, "forty two"),
            (100, "one hundred"),
            (250, "two hundred and fifty"),
            (1_000, "one thousand"),
            (1_200, "one thousand two hundred"),
            (1_000_000, "one million"),
        ],
    )
    def test_reads_integers_aloud(self, value, spoken):
        assert say_number(value) == spoken

    def test_handles_negatives(self):
        assert say_number(-5) == "minus five"


class TestNormalisation:
    def test_percentages(self):
        """The unit rule silently skipped every percentage: '%' is not a word
        character, so a trailing \\b after it could never assert."""
        assert normalise_for_speech("CPU at 87%") == "C P U at eighty seven percent"

    def test_singular_units(self):
        assert "one percent" in normalise_for_speech("Only 1% left")

    def test_data_sizes(self):
        assert "gigabytes" in normalise_for_speech("3.5GB free")

    def test_currency(self):
        assert "one thousand two hundred dollars" in normalise_for_speech("Cost: $1,200")

    def test_times(self):
        assert "three thirty" in normalise_for_speech("at 3:30")

    def test_times_on_the_hour(self):
        assert "o'clock" in normalise_for_speech("at 4:00")

    def test_times_past_the_hour(self):
        assert "oh five" in normalise_for_speech("at 14:05")

    def test_urls_do_not_become_a_stream_of_slashes(self):
        spoken = normalise_for_speech("Visit https://example.com/docs")

        assert "https" not in spoken
        assert "example dot com" in spoken

    def test_emails(self):
        assert "bob at test dot org" in normalise_for_speech("mail bob@test.org")

    def test_abbreviations_do_not_end_the_sentence(self):
        """'Dr.' looked like a full stop and drew a 380 ms pause mid-name."""
        spoken = normalise_for_speech("Dr. Smith is here")

        assert spoken.startswith("doctor Smith")
        assert "Dr." not in spoken

    def test_version_strings(self):
        assert normalise_for_speech("v2.1.0") == "two point one point zero"

    def test_technical_terms_get_a_pronunciation(self):
        spoken = normalise_for_speech("the SQL API")

        assert "sequel" in spoken
        assert "A P I" in spoken

    def test_pronunciations_match_whole_words_only(self):
        """'api' inside 'rapid' must not be rewritten."""
        assert "rapid" in normalise_for_speech("a rapid response")

    def test_plain_text_is_left_alone(self):
        assert normalise_for_speech("hello there") == "hello there"

    def test_empty_input(self):
        assert normalise_for_speech("") == ""
        assert normalise_for_speech("   ") == ""

    def test_a_realistic_sentence(self):
        spoken = normalise_for_speech("The API returned 500 in 250ms at 3:30pm.")

        for fragment in ("A P I", "five hundred", "milliseconds", "three thirty"):
            assert fragment in spoken


class TestVisemes:
    def test_digraphs_are_one_sound(self):
        """'th' is a single mouth position, not two."""
        assert word_to_visemes("the") == ["tongue", "open"]

    def test_silent_final_e_is_not_animated(self):
        # "make" is three sounds; the old letter-based track produced four.
        assert len(word_to_visemes("make")) == 3

    def test_short_words_keep_their_final_e(self):
        """In "the" the e is the only vowel and must survive."""
        assert word_to_visemes("the")[-1] == "open"

    def test_doubled_letters_collapse(self):
        """'gg' in "trigger" is one mouth position held, not two moves."""
        shapes = word_to_visemes("trigger")

        assert all(a != b for a, b in zip(shapes, shapes[1:], strict=False))

    def test_punctuation_and_digits_are_ignored(self):
        assert word_to_visemes("hello!") == word_to_visemes("hello")

    def test_empty_word(self):
        assert word_to_visemes("") == []
        assert word_to_visemes("123") == []

    def test_unknown_letters_fall_back(self):
        assert word_to_visemes("xyz")


class TestVisemeAlignment:
    def test_follows_word_timing(self):
        words = prosody_for("hello world")

        track = visemes_for_words([w.to_dict() for w in words])

        assert track
        assert all(entry["t"] >= 0 for entry in track)

    def test_the_mouth_closes_during_a_pause(self):
        """A held vowel through silence is the giveaway of fake lip-sync."""
        words = [w.to_dict() for w in prosody_for("First, second")]

        track = visemes_for_words(words)

        pause_start = words[0]["start_ms"] + words[0]["duration_ms"]
        closing = [e for e in track if e["t"] == pytest.approx(pause_start, abs=1)]
        assert closing and closing[0]["shape"] == "closed"

    def test_timings_do_not_go_backwards(self):
        words = [w.to_dict() for w in prosody_for("One, two. Three four.")]

        track = visemes_for_words(words)

        assert track == sorted(track, key=lambda e: e["t"])

    def test_empty_input(self):
        assert visemes_for_words([]) == []


class TestWakeWord:
    @pytest.fixture
    def engine(self):
        return VoiceEngine()

    def test_matches_the_wake_word(self, engine):
        assert engine.detect_wake_word("aera help me") is True

    def test_is_case_insensitive(self, engine):
        assert engine.detect_wake_word("AERA!") is True

    def test_does_not_fire_on_a_longer_word(self, engine):
        """Substring matching woke it on "area code" and "aeration"."""
        assert engine.detect_wake_word("the aeration system") is False

    def test_tolerates_a_mishearing(self, engine):
        """Speech recognition rarely returns the exact spelling."""
        assert engine.detect_wake_word("hey ara") is True
        assert engine.detect_wake_word("aira are you there") is True

    def test_rejects_something_unrelated(self, engine):
        assert engine.detect_wake_word("hello world") is False

    def test_an_empty_wake_word_never_fires(self, engine):
        engine.config.wake_word = ""

        assert engine.detect_wake_word("anything at all") is False

    def test_a_short_wake_word_demands_an_exact_match(self, engine):
        """One edit on a three-letter word collides with too much."""
        engine.config.wake_word = "ok"

        assert engine.detect_wake_word("ok go") is True
        assert engine.detect_wake_word("of go") is False


class TestEngineIntegration:
    async def test_speech_is_normalised_before_synthesis(self):
        engine = VoiceEngine()

        result = await engine.speak("CPU at 87%")

        assert "eighty seven percent" in result.text
        assert "%" not in result.text

    async def test_emotion_is_read_from_the_original_text(self):
        """Normalisation only expands symbols; it must not alter sentiment."""
        engine = VoiceEngine()

        result = await engine.speak("Sorry, the 500 error is back.")

        assert result.emotion.value == "sad"

    async def test_visemes_are_aligned_to_the_words(self):
        engine = VoiceEngine()

        result = await engine.speak("Make the site, then wait.")

        assert result.visemes
        # A closing shape somewhere means the pause was honoured.
        assert any(entry["shape"] == "closed" for entry in result.visemes)


class TestIdentifiersAreNotArithmetic:
    """Digit strings that name something, rather than counting something.

    The number rules ran over everything, so "555-1234" was read as
    "five hundred and fifty five" then a hyphen then "one thousand two
    hundred and thirty four" -- arithmetic where the only correct reading is
    digit by digit.
    """

    def test_a_phone_number_is_read_digit_by_digit(self):
        spoken = normalise_for_speech("Call 555-1234 now")

        assert "five five five one two three four" in spoken
        assert "hundred" not in spoken

    def test_a_long_serial_is_read_digit_by_digit(self):
        assert "thousand" not in normalise_for_speech("Order 4471-9930-2255")

    def test_an_ordinary_number_is_still_a_quantity(self):
        """The identifier rule must not swallow real numbers."""
        assert "one thousand two hundred" in normalise_for_speech("I counted 1200 items")


class TestDates:
    def test_an_iso_date_is_spoken_as_a_date(self):
        """It came out as "two thousand twenty four-one-fifteen": the hyphens
        survived, the leading zero was lost, and nothing named the month."""
        spoken = normalise_for_speech("2024-01-15 was the date")

        assert "January" in spoken
        assert "fifteenth" in spoken
        assert "-" not in spoken

    @pytest.mark.parametrize(
        ("date", "month"),
        [("2024-03-01", "March"), ("2020-12-25", "December"), ("1999-07-04", "July")],
    )
    def test_each_month_is_named(self, date, month):
        assert month in normalise_for_speech(date)

    def test_an_impossible_date_is_not_invented(self):
        """Month 13 is not a date. Falling through to digits is honest;
        naming a thirteenth month is not."""
        spoken = normalise_for_speech("2024-13-45 is not a date")

        assert "January" not in spoken
        assert "December" not in spoken


class TestVersionStrings:
    def test_a_four_part_version_is_fully_spoken(self):
        """The pattern captured exactly three components, so "1.2.3.4" was
        read as "one point two point three" and then a literal ".4"."""
        spoken = normalise_for_speech("Section 1.2.3.4 of the doc")

        assert spoken.count("point") == 3
        assert ".4" not in spoken

    @pytest.mark.parametrize("version", ["1.2", "1.2.3", "1.2.3.4", "1.2.3.4.5"])
    def test_any_length_works(self, version):
        assert not any(ch.isdigit() for ch in normalise_for_speech(version))
