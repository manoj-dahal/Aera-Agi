# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Emotional expression: mood, nuance and prosody.

The original detector matched keywords and returned a label. It read "that is
not great at all" as HAPPY, had no memory between utterances, and delivered
every sentence on one flat pitch. These cover the replacement.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from aera.api.app import create_app
from aera.voice.engine import Emotion, detect_emotion
from aera.voice.expression import (
    ExpressionAnalyser,
    Mood,
    prosody_for,
    to_ssml,
)


@pytest.fixture
def analyser():
    return ExpressionAnalyser()


class TestNegation:
    """The bug this file was written for."""

    def test_negated_praise_is_not_praise(self, analyser):
        assert analyser.analyse("That is not great at all").emotion is not Emotion.HAPPY

    def test_negated_praise_reads_as_concern(self, analyser):
        reading = analyser.analyse("That is not great at all")

        assert reading.emotion is Emotion.CONCERNED
        assert reading.negated is True

    def test_reassurance_reads_as_calm(self, analyser):
        # "not a risk" is the opposite of a warning, and should sound like it.
        assert analyser.analyse("It is not a risk.").emotion is Emotion.CALM

    def test_negation_only_affects_what_follows_it(self, analyser):
        """"Warning: it is not safe" is a warning, not reassurance.

        Applying negation across the whole sentence flipped `warning` too, so
        an urgent line came out calm.
        """
        reading = analyser.analyse("Warning: it is not safe at all.")

        assert reading.emotion in (Emotion.CONCERNED, Emotion.SERIOUS)

    def test_a_distant_negation_does_not_reach(self, analyser):
        """Beyond a few words the link is too weak to trust."""
        text = "It did not start well, but the release is a complete success"

        assert analyser.analyse(text).emotion in (Emotion.HAPPY, Emotion.EXCITED)


class TestNuance:
    def test_intensifiers_raise_intensity(self, analyser):
        plain = analyser.analyse("This is broken")
        strong = ExpressionAnalyser().analyse("This is completely broken")

        assert strong.intensity > plain.intensity

    def test_hedging_lowers_intensity(self, analyser):
        firm = analyser.analyse("This is broken")
        hedged = ExpressionAnalyser().analyse("This might be slightly broken")

        assert hedged.intensity < firm.intensity

    def test_the_closing_sentence_carries_most_weight(self, analyser):
        """"It failed. But I fixed it." should not sound defeated."""
        reading = analyser.analyse("It failed. But I fixed it and everything works now.")

        assert reading.emotion is Emotion.HAPPY

    def test_confidence_falls_when_signals_conflict(self, analyser):
        clear = analyser.analyse("Absolutely fantastic, brilliant work!")
        mixed = ExpressionAnalyser().analyse("A critical failure, but a great recovery.")

        assert mixed.confidence < clear.confidence

    def test_reasons_explain_the_decision(self, analyser):
        reading = analyser.analyse("Sorry, the deployment failed.")

        assert reading.reasons
        assert any("sad" in reason for reason in reading.reasons)

    def test_empty_text_is_neutral_with_no_confidence(self, analyser):
        reading = analyser.analyse("   ")

        assert reading.emotion is Emotion.NEUTRAL
        assert reading.confidence == 0.0


class TestMood:
    def test_starts_even(self):
        assert Mood().label() == "even"

    def test_repeated_bad_news_lowers_the_baseline(self, analyser):
        for _ in range(3):
            analyser.analyse("The build failed.")

        assert analyser.mood.decayed() < -0.2
        assert analyser.mood.label() in ("subdued", "low")

    def test_recovery_lifts_it_again(self, analyser):
        for _ in range(3):
            analyser.analyse("It failed.")
        low = analyser.mood.decayed()

        for _ in range(3):
            analyser.analyse("Fixed! Everything works perfectly now.")

        assert analyser.mood.decayed() > low

    def test_one_signal_does_not_overwrite_the_baseline(self):
        """Mood is a trend, not a switch."""
        mood = Mood(valence=-0.8)

        mood.observe(Emotion.HAPPY, 1.0)

        # Moved toward positive, but nowhere near flipped.
        assert -0.8 < mood.decayed() < 0.0

    def test_it_decays_toward_neutral(self):
        mood = Mood(valence=-0.9, half_life=60.0)
        mood.updated_at = time.time() - 300

        assert abs(mood.decayed()) < 0.05

    def test_a_low_mood_colours_an_otherwise_flat_line(self):
        """With nothing to go on, the standing mood shows through."""
        analyser = ExpressionAnalyser(Mood(valence=-0.6))

        assert analyser.analyse("Processing your request.").emotion is Emotion.SERIOUS

    def test_a_bright_mood_does_the_same(self):
        analyser = ExpressionAnalyser(Mood(valence=0.6))

        assert analyser.analyse("Processing your request.").emotion is Emotion.HAPPY

    def test_bad_news_lands_harder_when_things_are_already_bad(self):
        fresh = ExpressionAnalyser(Mood(valence=0.0)).analyse("It failed.")
        weary = ExpressionAnalyser(Mood(valence=-0.7)).analyse("It failed.")

        assert weary.intensity > fresh.intensity

    def test_reset_clears_it(self, analyser):
        analyser.analyse("Everything is broken and failing.")

        analyser.mood.reset()

        assert analyser.mood.decayed() == 0.0


class TestProsody:
    def test_produces_one_entry_per_word(self):
        words = prosody_for("Hello there friend")

        assert [w.text for w in words] == ["Hello", "there", "friend"]

    def test_content_words_are_stressed_more_than_function_words(self):
        words = {w.text: w for w in prosody_for("the database is unreachable")}

        assert words["database"].emphasis > words["the"].emphasis

    def test_capitals_are_read_as_emphasis(self):
        words = {w.text: w for w in prosody_for("this is URGENT now")}

        assert words["URGENT"].emphasis > words["this"].emphasis

    def test_commas_create_a_pause(self):
        words = prosody_for("First, second")

        assert words[0].pause_after_ms > 0

    def test_the_final_word_has_no_trailing_pause(self):
        """Silence after the last word is dead air, not phrasing."""
        words = prosody_for("It is done.")

        assert words[-1].pause_after_ms == 0

    def test_questions_rise_and_statements_fall(self):
        question = prosody_for("Is the server running?", emotion=Emotion.CURIOUS)
        statement = prosody_for("The server is running.", emotion=Emotion.NEUTRAL)

        assert question[-1].pitch_scale > question[0].pitch_scale
        assert statement[-1].pitch_scale <= statement[0].pitch_scale

    def test_sadness_falls_further_than_neutral(self):
        sad = prosody_for("The deployment failed", emotion=Emotion.SAD, intensity=0.9)
        neutral = prosody_for("The deployment failed", emotion=Emotion.NEUTRAL)

        assert sad[-1].pitch_scale < neutral[-1].pitch_scale

    def test_sadness_lengthens_pauses_and_excitement_shortens_them(self):
        sad = prosody_for("First, second", emotion=Emotion.SAD)
        excited = prosody_for("First, second", emotion=Emotion.EXCITED)

        assert sad[0].pause_after_ms > excited[0].pause_after_ms

    def test_intensity_widens_the_contour(self):
        gentle = prosody_for("Is it working?", emotion=Emotion.CURIOUS, intensity=0.1)
        strong = prosody_for("Is it working?", emotion=Emotion.CURIOUS, intensity=1.0)

        gentle_span = abs(gentle[-1].pitch_scale - gentle[0].pitch_scale)
        strong_span = abs(strong[-1].pitch_scale - strong[0].pitch_scale)
        assert strong_span > gentle_span

    def test_words_do_not_overlap(self):
        words = prosody_for("One, two. Three four five")

        for earlier, later in zip(words, words[1:], strict=False):
            assert later.start_ms >= earlier.start_ms + earlier.duration_ms

    def test_empty_text_produces_nothing(self):
        assert prosody_for("") == []


class TestSsml:
    def test_wraps_in_a_speak_element(self, analyser):
        ssml = to_ssml("Hello there", analyser.analyse("Hello there"))

        assert ssml.startswith("<speak>") and ssml.endswith("</speak>")

    def test_carries_pitch_and_breaks(self, analyser):
        ssml = to_ssml("First, second.", analyser.analyse("First, second."))

        assert "<prosody" in ssml
        assert "<break" in ssml

    def test_includes_the_persona_pitch_when_given(self, analyser):
        ssml = to_ssml("Hello", analyser.analyse("Hello"), persona_pitch_hz=255.0)

        assert 'pitch="255Hz"' in ssml

    def test_escapes_markup_in_the_text(self, analyser):
        """Unescaped input would corrupt the document or inject tags."""
        ssml = to_ssml("a < b & c", analyser.analyse("a < b & c"))

        assert "&lt;" in ssml and "&amp;" in ssml


class TestEngineIntegration:
    async def test_speaking_attaches_prosody_and_mood(self):
        from aera.voice.engine import VoiceEngine

        engine = VoiceEngine()

        result = await engine.speak("The database is unreachable.")

        assert result.prosody
        assert result.mood["label"]
        assert 0.0 <= result.intensity <= 1.0

    async def test_mood_persists_across_utterances(self):
        from aera.voice.engine import VoiceEngine

        engine = VoiceEngine()

        await engine.speak("It failed.")
        first = engine.expression.mood.decayed()
        await engine.speak("It failed again.")

        assert engine.expression.mood.decayed() < first

    async def test_an_explicit_emotion_still_carries_intensity(self):
        """Naming an emotion used to hardcode intensity to 0.6 and skip mood."""
        from aera.voice.engine import VoiceEngine

        engine = VoiceEngine()
        for _ in range(3):
            await engine.speak("Everything failed badly.")

        result = await engine.speak("Understood.", emotion="sad")

        assert result.intensity != 0.6
        assert result.mood["label"] in ("subdued", "low")

    async def test_an_explicit_emotion_still_moves_the_mood(self):
        from aera.voice.engine import VoiceEngine

        engine = VoiceEngine()
        before = engine.expression.mood.decayed()

        await engine.speak("The service failed and is down.", emotion="serious")

        assert engine.expression.mood.decayed() != before

    def test_the_legacy_helper_still_works(self):
        """detect_emotion is used elsewhere; its signature must not change."""
        emotion, confidence = detect_emotion("Sorry, it failed")

        assert emotion is Emotion.SAD
        assert 0.0 <= confidence <= 1.0

    def test_the_legacy_helper_is_stateless(self):
        """It must not accumulate mood between unrelated calls."""
        detect_emotion("Everything is broken and failing badly.")

        assert detect_emotion("Processing.")[0] is Emotion.NEUTRAL


class TestExpressionApi:
    @pytest.fixture
    def client(self, config):
        with TestClient(create_app(config)) as c:
            yield c

    def test_reports_mood(self, client):
        data = client.get("/api/v1/voice/mood").json()["data"]

        assert data["label"] == "even"
        assert data["enabled"] is True

    def test_mood_shifts_after_bad_news(self, client):
        for _ in range(3):
            client.post("/api/v1/voice/speak", json={"text": "The build failed."})

        assert client.get("/api/v1/voice/mood").json()["data"]["valence"] < 0

    def test_mood_can_be_reset(self, client):
        client.post("/api/v1/voice/speak", json={"text": "Everything failed."})

        client.post("/api/v1/voice/mood/reset")

        assert client.get("/api/v1/voice/mood").json()["data"]["valence"] == 0.0

    def test_expression_cannot_be_turned_off(self, client):
        """There is no off switch: flat delivery sounded broken, not neutral."""
        assert client.post("/api/v1/voice/mood/enabled?enabled=false").status_code == 404

    def test_mood_always_reports_enabled(self, client):
        assert client.get("/api/v1/voice/mood").json()["data"]["enabled"] is True

    def test_expression_survives_the_legacy_config_flag(self, client):
        """An old voice.yaml with emotion:false must not flatten delivery."""
        client.app.state.kernel.voice.config.emotion = False

        result = client.post(
            "/api/v1/voice/speak", json={"text": "That is fantastic!"}
        ).json()["data"]

        assert result["emotion"] != "neutral"

    def test_analyse_explains_a_line_without_speaking_it(self, client):
        data = client.post(
            "/api/v1/voice/analyse", params={"text": "Sorry, it failed."}
        ).json()["data"]

        assert data["emotion"] == "sad"
        assert data["words"]
        assert data["ssml"].startswith("<speak>")

    def test_analyse_does_not_move_the_mood(self, client):
        before = client.get("/api/v1/voice/mood").json()["data"]["valence"]

        client.post("/api/v1/voice/analyse", params={"text": "Everything failed badly."})

        assert client.get("/api/v1/voice/mood").json()["data"]["valence"] == before


class TestPunctuationAndEmoji:
    """Signals that are punctuation, not vocabulary.

    They live outside the language packs because they apply in every
    language, and they were lost entirely when the cue tables moved into the
    packs.
    """

    @pytest.mark.parametrize(
        ("text", "emotion"),
        [
            ("Deployment finished 😀", Emotion.HAPPY),
            ("Nice work 🥰", Emotion.HAPPY),
            ("It broke 😢", Emotion.SAD),
            ("Everything is gone 😭", Emotion.SAD),
        ],
    )
    def test_emoji_are_detected(self, text, emotion):
        """The pattern read "\\U0001F600-\\U0001F60F" inside an alternation
        rather than inside a character class, which is a literal
        three-character sequence: it matched the string "😀-😏" and no actual
        emoji, ever."""
        assert ExpressionAnalyser().analyse(text).emotion is emotion

    @pytest.mark.parametrize(
        ("text", "emotion"),
        [("All done :)", Emotion.HAPPY), ("It broke :(", Emotion.SAD)],
    )
    def test_ascii_emoticons_still_work(self, text, emotion):
        assert ExpressionAnalyser().analyse(text).emotion is emotion

    def test_a_semicolon_is_not_a_question_in_english(self):
        """";" was treated as a question mark in every language, so
        "Step one; step two;" read as curious."""
        reading = ExpressionAnalyser(language="en").analyse("Step one; step two;")

        assert reading.emotion is not Emotion.CURIOUS

    def test_a_semicolon_is_a_question_mark_in_greek(self):
        """Greek genuinely writes its question mark as a semicolon."""
        reading = ExpressionAnalyser(language="el").analyse("Τι κάνεις;")

        assert reading.emotion is Emotion.CURIOUS

    def test_a_real_question_mark_still_reads_as_curious(self):
        assert ExpressionAnalyser().analyse("what now?").emotion is Emotion.CURIOUS


class TestEmotionTimeline:
    """Emotion over time, not one label for a whole line.

    ``analyse`` collapses an utterance to its winner. That is right for a
    single statement and wrong for anything that turns partway through:
    "It failed. But I fixed it!" is sad and then happy, and the avatar was
    handed only "happy" -- so the failure never showed on its face.
    """

    TURNING = "It failed completely. But I fixed it and everything works now!"

    def test_a_turning_line_produces_two_spans(self):
        timeline = ExpressionAnalyser().timeline(self.TURNING)

        assert len(timeline.spans) == 2
        assert timeline.spans[0].emotion is Emotion.SAD
        assert timeline.spans[1].emotion is Emotion.HAPPY

    def test_a_single_statement_stays_one_span(self):
        """No pointless expression changes on a line that does not turn."""
        timeline = ExpressionAnalyser().timeline("The deployment failed.")

        assert len(timeline.spans) == 1
        assert timeline.changes == 0

    def test_spans_are_contiguous(self):
        """A gap would leave the face with no instruction for that moment."""
        spans = ExpressionAnalyser().timeline(self.TURNING).spans

        for earlier, later in zip(spans, spans[1:], strict=False):
            assert earlier.end_ms == pytest.approx(later.start_ms, abs=0.2)

    def test_the_first_span_starts_at_zero(self):
        assert ExpressionAnalyser().timeline(self.TURNING).spans[0].start_ms == 0.0

    def test_a_change_carries_a_blend(self):
        """Faces do not snap between expressions; roughly 200 ms is a real
        voluntary transition."""
        spans = ExpressionAnalyser().timeline(self.TURNING).spans

        assert spans[0].blend_ms == 0.0, "the first span eases in from rest"
        assert spans[1].blend_ms > 0

    def test_a_blend_never_outlasts_its_span(self):
        """Otherwise the ease-in is still running when the expression ends."""
        for span in ExpressionAnalyser().timeline("Yes! No. Maybe? Fine.").spans:
            assert span.blend_ms <= span.duration_ms

    def test_the_turn_is_found_inside_a_sentence(self):
        """The emotional change usually sits at "but", not at a full stop."""
        timeline = ExpressionAnalyser().timeline(
            "Great news! Although there is a critical security problem."
        )

        assert timeline.changes == 1
        assert timeline.spans[-1].emotion is Emotion.SERIOUS

    def test_adjacent_matching_spans_are_merged(self):
        """Four neutral clauses are one expression, not four identical spans
        and three pointless blend events."""
        timeline = ExpressionAnalyser().timeline(
            "The file is here; the folder is there; the path is set."
        )

        emotions = [s.emotion for s in timeline.spans]
        assert emotions == list(dict.fromkeys(emotions)), "adjacent duplicates remain"

    def test_dominant_is_weighted_by_time(self):
        """A long sad clause should not be outvoted by short neutral ones."""
        timeline = ExpressionAnalyser().timeline(self.TURNING)
        longest = max(timeline.spans, key=lambda s: s.duration_ms)

        assert timeline.dominant is longest.emotion

    def test_at_finds_the_span_covering_a_moment(self):
        """This is what a frame-by-frame renderer calls."""
        timeline = ExpressionAnalyser().timeline(self.TURNING)
        first, second = timeline.spans

        assert timeline.at(first.start_ms + 1).emotion is first.emotion
        assert timeline.at(second.start_ms + 1).emotion is second.emotion

    def test_at_past_the_end_holds_the_last_expression(self):
        """Better than dropping to neutral the instant audio stops."""
        timeline = ExpressionAnalyser().timeline(self.TURNING)

        assert timeline.at(timeline.duration_ms + 5000) is timeline.spans[-1]

    def test_it_scales_onto_the_real_audio_length(self):
        """The splitter drops connectives, so summed clause prosody lands
        short of the whole line -- 5,013 ms against 4,750 ms on one measured
        example. Unscaled, the face drifts against the mouth."""
        timeline = ExpressionAnalyser().timeline(self.TURNING, total_ms=3000.0)

        assert timeline.duration_ms == pytest.approx(3000.0, abs=1.0)
        assert timeline.spans[-1].end_ms == pytest.approx(3000.0, abs=1.0)

    def test_empty_input(self):
        assert ExpressionAnalyser().timeline("").spans == []
        assert ExpressionAnalyser().timeline("   ").duration_ms == 0.0

    def test_a_tiny_clause_does_not_flicker(self):
        """"Yes, but no" must not become a three-frame expression stutter."""
        assert len(ExpressionAnalyser().timeline("Yes, but no.").spans) <= 2

    def test_the_mood_moves_once_for_the_whole_line(self):
        """Six clauses must not shift the standing baseline six times as far
        as one clause saying the same thing."""
        long_line = ExpressionAnalyser()
        short_line = ExpressionAnalyser()

        long_line.timeline("It failed; it failed; it failed; it failed.")
        short_line.timeline("It failed.")

        assert long_line.mood.valence == pytest.approx(short_line.mood.valence, abs=0.05)

    def test_negation_survives_the_clause_split(self):
        """Splitting exposed that "safe" was never a cue word, so "not safe"
        had nothing to negate and scored neutral. It only ever read as
        concerned because "warning" sat in the same sentence."""
        assert ExpressionAnalyser().analyse("it is not safe").emotion is Emotion.CONCERNED
        assert ExpressionAnalyser().analyse("safe").emotion is Emotion.CALM


class TestTimelineApi:
    @pytest.fixture
    def client(self, config):
        from fastapi.testclient import TestClient

        from aera.api.app import create_app

        with TestClient(create_app(config)) as c:
            yield c

    def test_the_endpoint_returns_spans(self, client):
        data = client.post(
            "/api/v1/voice/timeline",
            json={"text": "It failed. But I fixed it and everything works now!"},
        ).json()["data"]

        assert len(data["spans"]) == 2
        assert data["changes"] == 1

    def test_speaking_includes_the_timeline(self, client):
        data = client.post(
            "/api/v1/voice/speak",
            json={"text": "It failed. But I fixed it and everything works now!"},
        ).json()["data"]

        assert [s["emotion"] for s in data["emotion_timeline"]] == ["sad", "happy"]

    def test_the_timeline_matches_the_audio_length(self, client):
        """If these disagree the face and the mouth drift apart."""
        data = client.post(
            "/api/v1/voice/speak", json={"text": "It failed. But I fixed it!"}
        ).json()["data"]

        assert data["emotion_timeline"][-1]["end_ms"] == pytest.approx(
            data["duration_ms"], abs=1.0
        )
