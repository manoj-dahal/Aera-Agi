# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Singing: lyrics, rhythm, metre and melody.

Speech prosody cannot be relabelled as song. Sung pitch is quantised to a
scale where spoken pitch glides; sung timing is fixed by the bar where
spoken timing follows stress; the unit is the syllable, not the word. These
tests pin the parts that are determined by the words -- how many notes there
are, which land on strong beats, where the singer breathes -- and state the
limits of the parts that are not.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aera.api.app import create_app
from aera.voice.engine import Emotion
from aera.voice.languages import PACKS
from aera.voice.music import (
    COMMON_TIME,
    COMPOUND_TIME,
    MUSIC_FOR_EMOTION,
    SCALES,
    TEMPO_MARKS,
    WALTZ_TIME,
    Foot,
    NoteValue,
    SectionKind,
    Tempo,
    TimeSignature,
    analyse_song,
    midi_to_hz,
    name_to_midi,
    note_name,
    rhyme_key,
    rhyme_scheme,
    scale_degrees,
    scan,
    sections_of,
    setting_for,
    sing,
    stress_pattern,
    syllabify,
    syllables_in,
    words_in,
)

VERSE_CHORUS = """Fire in the morning light
Burning through the endless night

We will rise again
We will rise again

Cold across the empty plain
Waiting for the falling rain

We will rise again
We will rise again"""


class TestSyllables:
    @pytest.mark.parametrize(
        ("word", "count"),
        [
            ("hello", 2), ("make", 1), ("maker", 2), ("little", 2),
            ("the", 1), ("beat", 1), ("wonderful", 3), ("happy", 2),
            ("beautiful", 3), ("remember", 3), ("tonight", 2), ("away", 2),
            ("morning", 2), ("sky", 1), ("myth", 1),
            # y is a vowel here and there is no other: counting only aeiou
            # made "rhythm" one syllable and "everything" three.
            ("rhythm", 2), ("everything", 4), ("crying", 2),
            # Hiatus: two written vowels, two spoken syllables.
            ("poet", 2), ("radio", 3), ("piano", 3),
            # -tion and -tial are one sound; the hiatus rule must not split
            # them, which it did before it was scoped to the vowel group.
            ("nation", 2), ("mission", 2), ("special", 2), ("patient", 2),
            # A syllabic consonant carries its own beat.
            ("prism", 2),
        ],
    )
    def test_counts_english_syllables(self, word, count):
        assert syllables_in(word) == count

    @pytest.mark.parametrize(
        ("text", "count"),
        [
            ("नमस्ते", 3),      # na-mas-te
            ("你好", 2),         # one syllable per Han character
            ("こんにちは", 5),    # one per mora
            ("きゃく", 2),        # ゃ attaches; きゃ is one mora, not two
            ("안녕하세요", 5),    # one per Hangul block
        ],
    )
    def test_counts_syllables_outside_latin(self, text, count):
        """Lyrics are not only in English, and the count drives everything."""
        assert syllables_in(text) == count

    def test_counts_a_whole_line(self):
        assert syllables_in("Fire in the morning light") == 7

    @pytest.mark.parametrize(
        "word",
        ["wonderful", "everything", "hello", "nation", "beautiful", "remember",
         "rhythm", "poet", "radio", "crying", "piano", "prism", "make", "the"],
    )
    def test_the_split_matches_the_count(self, word):
        """The count and the split are two views of one fact.

        Letting them disagree gives a lyric four notes for a three-note word.
        They drifted on "poet", "radio", "rhythm" and "crying" before this
        was enforced.
        """
        assert len(syllabify(word)) == syllables_in(word)

    @pytest.mark.parametrize(
        "word",
        ["wonderful", "everything", "nation", "beautiful", "remember", "poet"],
    )
    def test_the_split_loses_no_letters(self, word):
        assert "".join(syllabify(word)) == word

    def test_splits_non_latin_by_its_own_unit(self):
        assert syllabify("你好") == ["你", "好"]
        assert syllabify("안녕") == ["안", "녕"]
        assert syllabify("きゃく") == ["きゃ", "く"]

    def test_empty_input(self):
        assert syllables_in("") == 0
        assert syllabify("") == []


class TestMetre:
    def test_content_words_take_the_stress(self):
        """The same distinction speech prosody uses, applied per syllable."""
        assert stress_pattern("the cat") == (0, 1)

    def test_a_polysyllable_stresses_its_first_syllable(self):
        assert stress_pattern("wonderful") == (1, 0, 0)

    @pytest.mark.parametrize(
        ("line", "foot"),
        [
            ("Tiger tiger burning bright", Foot.TROCHEE),
            ("Merrily merrily merrily", Foot.DACTYL),
        ],
    )
    def test_recognises_a_repeating_foot(self, line, foot):
        assert scan(line).foot is foot

    def test_names_the_metre_the_way_a_reader_would(self):
        assert scan("Tiger tiger burning bright").name == "trochaic trimeter"

    def test_an_irregular_line_is_free_verse_not_a_forced_label(self):
        """Below three-quarters agreement the pattern is coincidence."""
        assert scan("The quick brown fox jumps over").foot is Foot.FREE
        assert scan("The quick brown fox jumps over").name == "free verse"

    def test_an_empty_line_scans_to_nothing(self):
        assert scan("").syllables == 0


class TestRhyme:
    @pytest.mark.parametrize(
        ("left", "right"),
        [
            ("cat", "hat"), ("nation", "station"), ("night", "light"),
            # A bare final "e" is not a rhyme: both reduced to "e" and would
            # have rhymed with "the".
            ("fire", "desire"),
            # y and i are the same vowel; only the spelling differs.
            ("time", "rhyme"),
            # A word-final "gh" is silent.
            ("sky", "high"),
        ],
    )
    def test_words_that_rhyme_share_a_key(self, left, right):
        assert rhyme_key(left) == rhyme_key(right)

    @pytest.mark.parametrize(("left", "right"), [("cat", "dog"), ("light", "love")])
    def test_words_that_do_not_rhyme_differ(self, left, right):
        assert rhyme_key(left) != rhyme_key(right)

    def test_a_silent_e_does_not_rhyme_everything_together(self):
        """"fire" reducing to "e" would rhyme it with "the" and "be"."""
        assert rhyme_key("fire") != rhyme_key("the")

    @pytest.mark.parametrize(
        ("lines", "scheme"),
        [
            (["cat", "dog", "hat", "log"], "ABAB"),
            (["cat", "hat", "dog", "log"], "AABB"),
            (["sky", "high", "cry", "by"], "AAAA"),
            (["one", "two", "three", "four"], "ABCD"),
        ],
    )
    def test_labels_the_scheme(self, lines, scheme):
        assert rhyme_scheme(lines) == scheme

    def test_an_empty_line_gets_a_placeholder(self):
        assert rhyme_scheme(["cat", ""]) == "A-"


class TestRhythm:
    def test_a_beat_is_sixty_thousand_over_bpm(self):
        assert Tempo(120).beat_ms == 500.0

    def test_note_lengths_scale_with_the_signature(self):
        tempo = Tempo(120)

        assert tempo.note_ms(NoteValue.QUARTER, COMMON_TIME) == 500.0
        assert tempo.note_ms(NoteValue.EIGHTH, COMMON_TIME) == 250.0
        assert tempo.note_ms(NoteValue.WHOLE, COMMON_TIME) == 2000.0

    def test_a_dotted_note_is_half_again(self):
        assert NoteValue.DOTTED_QUARTER == NoteValue.QUARTER * 1.5

    def test_a_bar_is_its_beats(self):
        assert Tempo(120).bar_ms(COMMON_TIME) == 2000.0
        assert Tempo(120).bar_ms(WALTZ_TIME) == 1500.0

    def test_compound_time_is_recognised(self):
        """6/8 subdivides in three; 4/4 does not."""
        assert COMPOUND_TIME.is_compound is True
        assert COMMON_TIME.is_compound is False

    def test_tempo_marks_round_trip(self):
        assert Tempo.named("allegro").bpm == TEMPO_MARKS["allegro"]
        assert Tempo(138).mark() == "allegro"

    def test_an_unsingable_tempo_is_refused(self):
        with pytest.raises(ValueError, match="singable"):
            Tempo(5)
        with pytest.raises(ValueError, match="singable"):
            Tempo(1000)

    def test_an_impossible_signature_is_refused(self):
        with pytest.raises(ValueError):
            TimeSignature(0, 4)
        with pytest.raises(ValueError):
            TimeSignature(4, 5)

    def test_an_unknown_tempo_mark_names_the_known_ones(self):
        with pytest.raises(KeyError, match="allegro"):
            Tempo.named("quickly")


class TestPitch:
    def test_concert_pitch(self):
        assert name_to_midi("A4") == 69
        assert midi_to_hz(69) == 440.0

    def test_an_octave_doubles_the_frequency(self):
        assert midi_to_hz(81) == pytest.approx(880.0)

    def test_note_names_round_trip(self):
        for name in ("C4", "A4", "C#5", "F#3", "Bb2"):
            assert note_name(name_to_midi(name))

    def test_a_bad_note_name_is_refused(self):
        with pytest.raises(ValueError, match="not a note name"):
            name_to_midi("H9")

    def test_the_major_scale_is_the_major_scale(self):
        degrees = scale_degrees(name_to_midi("C4"), "major", 8)

        assert [note_name(m) for m in degrees] == [
            "C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"
        ]

    def test_pentatonic_has_five_degrees_before_it_repeats(self):
        assert len(SCALES["major_pentatonic"]) == 5

    def test_non_western_scales_are_available(self):
        """The language packs cover South Asia and the Middle East; a major
        scale would be the wrong default for those lyrics."""
        assert "bhairav" in SCALES
        assert "hijaz" in SCALES

    def test_an_unknown_scale_names_the_known_ones(self):
        with pytest.raises(KeyError, match="major"):
            scale_degrees(60, "klingon", 8)


class TestSongStructure:
    def test_finds_the_chorus_by_repetition(self):
        kinds = [s.kind for s in sections_of(VERSE_CHORUS)]

        assert kinds == [
            SectionKind.VERSE, SectionKind.CHORUS,
            SectionKind.VERSE, SectionKind.CHORUS,
        ]

    def test_repetition_alone_does_not_make_everything_a_chorus(self):
        """In verse/chorus/verse/chorus every block repeats. Labelling all
        four "chorus" said nothing at all, which is what it used to do."""
        kinds = {s.kind for s in sections_of(VERSE_CHORUS)}

        assert SectionKind.VERSE in kinds

    def test_a_song_with_no_repeats_has_no_chorus(self):
        """Honest: nothing repeated, so nothing is a chorus."""
        lyrics = "One line here\nAnd another\n\nA different thought\nEntirely"

        assert all(s.kind is not SectionKind.CHORUS for s in sections_of(lyrics))

    def test_sections_are_numbered(self):
        verses = [s for s in sections_of(VERSE_CHORUS) if s.kind is SectionKind.VERSE]

        assert [s.index for s in verses] == [1, 2]

    def test_empty_lyrics(self):
        assert sections_of("") == []


class TestSinging:
    def test_one_note_per_syllable(self):
        line = "Fire in the morning light"
        # Excited is fast, so no melisma is added and the counts match
        # exactly. A melisma deliberately adds notes without adding
        # syllables; that is covered separately.
        phrases = sing(line, tonic="C4", emotion=Emotion.EXCITED)

        assert len(phrases) == 1
        assert len(phrases[0].notes) == syllables_in(line)

    def test_a_melisma_adds_a_note_but_not_a_syllable(self):
        """The extra note repeats the syllable it is carrying."""
        phrases = sing("Fire in the morning light", tonic="C4", emotion=Emotion.SAD)
        notes = phrases[0].notes
        sung = [n for n in notes if not n.melisma]

        assert len(sung) == syllables_in("Fire in the morning light")
        assert notes[-1].melisma
        assert notes[-1].syllable == sung[-1].syllable

    def test_a_phrase_per_line(self):
        assert len(sing("Fire in the light\nBurning in the night")) == 2

    def test_the_melody_has_a_range(self):
        """A three-semitone span is a monotone with a wobble, not a tune --
        which is what the first arch produced."""
        notes = [n.midi for p in sing(VERSE_CHORUS, emotion=Emotion.HAPPY) for n in p.notes]

        assert max(notes) - min(notes) >= 7

    def test_a_line_ends_on_the_tonic(self):
        """A phrase that ends anywhere else sounds unfinished."""
        phrases = sing("Fire in the morning light", tonic="C4", emotion=Emotion.HAPPY)
        setting = setting_for(Emotion.HAPPY)
        expected = name_to_midi("C4") + setting.register

        assert phrases[0].notes[-1].midi == expected

    def test_stressed_syllables_are_louder_and_longer(self):
        notes = sing("the cat", tonic="C4")[0].notes
        weak, strong = notes[0], notes[1]

        assert strong.emphasis > weak.emphasis
        assert strong.duration_ms > weak.duration_ms

    def test_notes_do_not_overlap(self):
        notes = [n for p in sing(VERSE_CHORUS) for n in p.notes]

        for earlier, later in zip(notes, notes[1:], strict=False):
            assert later.start_ms >= earlier.start_ms

    def test_bars_and_beats_are_reported(self):
        notes = sing("Fire in the morning light", tonic="C4")[0].notes

        assert notes[0].bar == 1
        assert all(n.bar >= 1 for n in notes)

    def test_the_singer_breathes_between_lines(self):
        phrases = sing("Fire in the light\nBurning in the night")

        assert phrases[0].breath_after_ms > 0

    def test_emotion_sets_the_tempo_and_the_scale(self):
        assert setting_for(Emotion.SAD).tempo.bpm < setting_for(Emotion.EXCITED).tempo.bpm
        assert "minor" in setting_for(Emotion.SAD).scale
        assert setting_for(Emotion.HAPPY).scale.startswith("major")

    def test_a_slow_song_carries_a_syllable_across_notes(self):
        """Melisma. The flag was declared and never set by anything, so it
        always read False."""
        phrases = sing(VERSE_CHORUS, emotion=Emotion.SAD)

        assert any(n.melisma for p in phrases for n in p.notes)

    def test_a_fast_song_does_not(self):
        """An ornament applied everywhere makes a melody sound aimless."""
        phrases = sing(VERSE_CHORUS, emotion=Emotion.EXCITED)

        assert not any(n.melisma for p in phrases for n in p.notes)

    def test_every_note_carries_a_frequency(self):
        for phrase in sing("Fire in the light"):
            for note in phrase.notes:
                assert 20.0 < note.hz < 5000.0

    def test_lyrics_in_another_script_are_sung(self):
        """Syllable counting works outside Latin, so singing should too."""
        phrases = sing("नमस्ते संसार", language="hi", tonic="C4")

        assert phrases
        assert len(phrases[0].notes) >= 3

    def test_empty_lyrics_produce_no_notes(self):
        assert sing("") == []
        assert sing("   \n  ") == []


class TestAnalysis:
    def test_reports_structure_metre_and_rhyme(self):
        result = analyse_song(VERSE_CHORUS)

        assert result["lines"] == 8
        assert result["syllables"] > 0
        assert result["rhyme_scheme"]
        assert len(result["sections"]) == 4

    def test_reports_the_emotion_and_the_setting_it_implies(self):
        result = analyse_song("Sorry, everything failed and broke")

        assert result["emotion"] == "sad"
        assert result["setting"]["bpm"] == MUSIC_FOR_EMOTION[Emotion.SAD].tempo.bpm

    def test_flags_whether_the_lines_are_the_same_length(self):
        """A song whose lines vary cannot be sung to one repeating tune."""
        even = analyse_song("Fire in the light\nBurning in the night")
        uneven = analyse_song("Fire\nBurning through the endless night")

        assert even["regular_metre"] is True
        assert uneven["regular_metre"] is False

    def test_estimates_a_duration(self):
        assert analyse_song(VERSE_CHORUS)["estimated_duration_ms"] > 0


class TestMusicApi:
    @pytest.fixture
    def client(self, config):
        with TestClient(create_app(config)) as c:
            yield c

    def test_sing_returns_a_note_plan(self, client):
        data = client.post(
            "/api/v1/voice/sing", json={"lyrics": VERSE_CHORUS, "tonic": "C4"}
        ).json()["data"]

        assert data["notes"] > 0
        assert data["duration_ms"] > 0
        assert data["phrases"][0]["notes"][0]["note"]

    def test_sing_says_it_is_not_audio(self, client):
        """The same limit as the rest of the voice stack, stated where a
        caller will actually read it."""
        data = client.post("/api/v1/voice/sing", json={"lyrics": "Fire"}).json()["data"]

        assert data["audio"] is None
        assert "not audio" in data["note"]

    def test_an_explicit_key_and_tempo_are_honoured(self, client):
        data = client.post(
            "/api/v1/voice/sing",
            json={"lyrics": "Fire in the light", "tonic": "A3", "bpm": 90, "scale": "blues"},
        ).json()["data"]

        assert data["setting"]["bpm"] == 90
        assert data["setting"]["scale"] == "blues"

    def test_an_unknown_scale_is_refused_with_the_known_ones(self, client):
        response = client.post(
            "/api/v1/voice/sing", json={"lyrics": "Fire", "scale": "klingon"}
        )

        assert response.status_code == 422
        assert "major" in response.json()["error"]

    def test_an_unsingable_tempo_is_refused(self, client):
        """Rejected by the schema, so this is the app's 400 for a bad body
        rather than FastAPI's default 422."""
        assert client.post(
            "/api/v1/voice/sing", json={"lyrics": "Fire", "bpm": 5}
        ).status_code == 400

    def test_analyse_reads_a_lyric_without_singing_it(self, client):
        data = client.post(
            "/api/v1/voice/music/analyse", json={"lyrics": VERSE_CHORUS}
        ).json()["data"]

        assert data["sections"]
        assert data["metre"]
        assert "phrases" not in data

    def test_the_reference_lists_what_the_engine_accepts(self, client):
        """So a picker does not hardcode a list that drifts."""
        data = client.get("/api/v1/voice/music").json()["data"]

        assert set(data["scales"]) == set(SCALES)
        assert set(data["tempo_marks"]) == set(TEMPO_MARKS)
        assert len(data["emotion_settings"]) == len(Emotion)

    def test_empty_lyrics_are_refused(self, client):
        assert client.post("/api/v1/voice/sing", json={"lyrics": ""}).status_code == 400


#: One real lyric line per language, so "works in English" is not mistaken
#: for "works". Each is a plain sentence, not a cue word, because cue words
#: are what the emotion tests already cover.
LYRIC_BY_LANGUAGE = {
    "en": "Fire in the morning light", "es": "Fuego en la luz del alba",
    "fr": "Feu dans la lumière du matin", "de": "Feuer im Licht des Morgens",
    "it": "Fuoco nella luce del mattino", "pt": "Fogo na luz da manhã",
    "nl": "Vuur in het licht van de morgen", "sv": "Eld i morgonens ljus",
    "pl": "Ogień w świetle poranka", "ru": "Огонь в утреннем свете",
    "uk": "Вогонь у ранковому світлі", "el": "Φωτιά στο φως του πρωινού",
    "tr": "Sabah ışığında ateş", "hi": "सुबह की रोशनी में आग",
    "ne": "बिहानको उज्यालोमा आगो", "mr": "सकाळच्या प्रकाशात आग",
    "bn": "সকালের আলোয় আগুন", "gu": "સવારના પ્રકાશમાં આગ",
    "pa": "ਸਵੇਰ ਦੀ ਰੌਸ਼ਨੀ ਵਿੱਚ ਅੱਗ", "ta": "காலை ஒளியில் நெருப்பு",
    "te": "ఉదయపు వెలుగులో అగ్ని", "kn": "ಬೆಳಗಿನ ಬೆಳಕಿನಲ್ಲಿ ಬೆಂಕಿ",
    "ml": "പ്രഭാത വെളിച്ചത്തിൽ തീ", "si": "උදෑසන ආලෝකයේ ගින්න",
    "ur": "صبح کی روشنی میں آگ", "ar": "نار في ضوء الصباح",
    "he": "אש באור הבוקר", "fa": "آتش در نور صبح", "ja": "朝の光の中の炎",
    "zh": "晨光中的火焰", "ko": "아침 빛 속의 불꽃", "th": "ไฟในแสงยามเช้า",
    "vi": "Lửa trong ánh sáng ban mai", "id": "Api dalam cahaya pagi",
    "sw": "Moto katika mwanga wa asubuhi",
}


class TestEveryLanguageSings:
    """The catalogue is 35 languages; singing has to work in all of them.

    Sweeping every language is how the Thai splitter was caught returning
    two notes for six syllables, and how the Cyrillic, Arabic and Hebrew
    words were found being sung whole on a single note.
    """

    def test_there_is_a_lyric_for_every_pack(self):
        assert set(LYRIC_BY_LANGUAGE) == set(PACKS)

    @pytest.mark.parametrize("code", sorted(LYRIC_BY_LANGUAGE))
    def test_the_line_has_syllables(self, code):
        assert syllables_in(LYRIC_BY_LANGUAGE[code]) >= 4

    @pytest.mark.parametrize("code", sorted(LYRIC_BY_LANGUAGE))
    def test_one_note_per_syllable_in_every_language(self, code):
        """Thai returned two notes for six syllables, and Russian sang
        "утреннем" -- three syllables -- on one, because the counter knew
        about vowels the splitter did not."""
        lyric = LYRIC_BY_LANGUAGE[code]
        phrases = sing(lyric, language=code, tonic="C4", emotion=Emotion.HAPPY)
        sung = [n for p in phrases for n in p.notes if not n.melisma]

        assert len(sung) == syllables_in(lyric)

    @pytest.mark.parametrize("code", sorted(LYRIC_BY_LANGUAGE))
    def test_the_melody_moves_in_every_language(self, code):
        notes = [
            n.midi
            for p in sing(LYRIC_BY_LANGUAGE[code], language=code, emotion=Emotion.HAPPY)
            for n in p.notes
        ]

        assert max(notes) - min(notes) >= 5

    @pytest.mark.parametrize("code", sorted(LYRIC_BY_LANGUAGE))
    def test_the_split_and_the_count_agree(self, code):
        """They are one fact with two views. Fourteen of thirty-five
        languages disagreed before the count was defined as the split."""
        lyric = LYRIC_BY_LANGUAGE[code]
        pieces = sum(len(syllabify(word)) for word in words_in(lyric))

        assert pieces == syllables_in(lyric)

    @pytest.mark.parametrize("code", sorted(LYRIC_BY_LANGUAGE))
    def test_no_letters_are_lost_when_splitting(self, code):
        for word in words_in(LYRIC_BY_LANGUAGE[code]):
            assert "".join(syllabify(word)) == word

    def test_a_combining_mark_does_not_end_a_word(self):
        """The virama is a combining mark, so a plain \\w tokeniser cut
        "नमस्ते" into "नमस" and "त" and counted four syllables, not three.
        The same defect once broke word boundaries in the language packs."""
        assert words_in("नमस्ते संसार") == ["नमस्ते", "संसार"]
        assert syllables_in("नमस्ते") == 3
