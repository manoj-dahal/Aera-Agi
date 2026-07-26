# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Voice personas for the anime-g and anime-b avatars.

Two things are under test: that the personas are genuinely distinct and
respond to emotion, and that the bundled synthesiser never claims to be a
speech engine. The second matters as much as the first -- audio that sounds
like speech but is not must say so.
"""

from __future__ import annotations

import array
import math
import wave

import pytest
from fastapi.testclient import TestClient

from aera.api.app import create_app
from aera.voice.engine import Emotion
from aera.voice.personas import (
    ALL_PERSONAS,
    ANIME_BOY,
    ANIME_GIRL,
    FORMANT_NOTE,
    NEUTRAL,
    PERSONAS,
    SAMPLE_RATE,
    PersonaTTS,
    get_persona,
    persona_for_variant,
    synthesize_wav,
)


def energy_at(path, freq: float) -> float:
    """Goertzel: signal energy at one frequency.

    Autocorrelation locks onto sub-harmonics when strong formants are present,
    so measuring the target frequency directly is the reliable check.
    """
    with wave.open(str(path)) as handle:
        rate = handle.getframerate()
        samples = array.array("h")
        samples.frombytes(handle.readframes(handle.getnframes()))

    window = [float(v) for v in samples[rate // 2 : rate // 2 + 4096]]
    if not window:
        return 0.0
    coeff = 2 * math.cos(2 * math.pi * freq / rate)
    s1 = s2 = 0.0
    for value in window:
        s0 = value + coeff * s1 - s2
        s2, s1 = s1, s0
    return math.sqrt(max(0.0, s1 * s1 + s2 * s2 - coeff * s1 * s2))


class TestDuration:
    """How long a line takes to say, in any script.

    Duration came from ``len(text.split())``. Chinese, Japanese, Korean and
    Thai are written without spaces, so a whole sentence counted as one word
    and a seven-syllable Japanese line was timed at 364 ms -- roughly a
    third of what it takes to say, with the lip-sync track compressed to
    match.
    """

    @pytest.mark.parametrize(
        ("text", "floor_ms"),
        [
            ("Fire in the morning light", 1400),
            ("朝の光の中の炎", 1400),
            ("晨光中的火焰", 1200),
            ("안녕하세요", 1000),
            ("नमस्ते संसार", 1200),
        ],
    )
    def test_a_line_is_timed_by_its_syllables(self, text, floor_ms):
        from aera.voice.personas import speech_duration_ms

        assert speech_duration_ms(text) >= floor_ms

    def test_scripts_without_spaces_are_not_timed_as_one_word(self):
        """The regression: these two lines have the same syllable count."""
        from aera.voice.personas import speech_duration_ms

        english = speech_duration_ms("Fire in the morning light")   # 7 syllables
        japanese = speech_duration_ms("朝の光の中の炎")                # 7 syllables

        assert japanese == pytest.approx(english, rel=0.15)

    def test_text_with_no_syllables_still_gets_a_duration(self):
        from aera.voice.personas import speech_duration_ms

        assert speech_duration_ms("12345") > 0

    def test_speed_scales_it(self):
        from aera.voice.personas import speech_duration_ms

        assert speech_duration_ms("Hello there", rate=2.0) < speech_duration_ms("Hello there")


class TestAudioFilenames:
    """Rendered audio is content-addressed so a cache actually hits.

    Three backends built this name with ``hash()``, which Python randomises
    per process: the same line got a different filename on every restart,
    the cache never hit, and the directory filled with duplicate renders of
    identical audio. ``synthesize_wav`` had already been fixed for exactly
    this and the filenames beside it had not.
    """

    def test_the_same_request_gives_the_same_name(self):
        from aera.voice.personas import audio_filename

        first = audio_filename("hello", "anime-g", Emotion.HAPPY)
        second = audio_filename("hello", "anime-g", Emotion.HAPPY)

        assert first == second

    @pytest.mark.parametrize(
        ("text", "persona", "emotion"),
        [
            ("goodbye", "anime-g", Emotion.HAPPY),
            ("hello", "anime-b", Emotion.HAPPY),
            ("hello", "anime-g", Emotion.SAD),
        ],
    )
    def test_a_different_request_gives_a_different_name(self, text, persona, emotion):
        from aera.voice.personas import audio_filename

        assert audio_filename(text, persona, emotion) != audio_filename(
            "hello", "anime-g", Emotion.HAPPY
        )

    def test_the_name_is_stable_across_processes(self):
        """The whole point: hash() is stable within a run and not between."""
        import subprocess
        import sys

        code = (
            "from aera.voice.personas import audio_filename;"
            "from aera.voice.engine import Emotion;"
            "print(audio_filename('hello', 'anime-g', Emotion.HAPPY))"
        )
        runs = {
            subprocess.run(
                [sys.executable, "-c", code], capture_output=True, text=True, check=True
            ).stdout.strip()
            for _ in range(2)
        }

        assert len(runs) == 1


class TestPersonaDefinitions:
    def test_the_two_avatar_voices_exist(self):
        assert "anime-g" in PERSONAS
        assert "anime-b" in PERSONAS

    def test_the_girl_is_pitched_above_the_boy(self):
        # The whole point: they must not sound the same.
        assert ANIME_GIRL.base_pitch_hz > ANIME_BOY.base_pitch_hz

    def test_the_separation_is_audible(self):
        """A few hertz apart would be indistinguishable in practice."""
        ratio = ANIME_GIRL.base_pitch_hz / ANIME_BOY.base_pitch_hz
        assert ratio > 1.4

    def test_anime_pitches_sit_above_natural_averages(self):
        # Adult speech centres near 200 Hz (female) and 120 Hz (male); anime
        # delivery is performed higher than both.
        assert ANIME_GIRL.base_pitch_hz > 200
        assert ANIME_BOY.base_pitch_hz > 120

    def test_the_girl_voice_is_brighter_and_more_expressive(self):
        assert ANIME_GIRL.brightness > ANIME_BOY.brightness
        assert ANIME_GIRL.pitch_range > ANIME_BOY.pitch_range

    def test_each_persona_carries_hints_for_real_engines(self):
        """Personas must be portable, not tied to the bundled synthesiser."""
        for persona in (ANIME_GIRL, ANIME_BOY):
            assert "piper" in persona.engine_hints

    def test_unknown_ids_fall_back_rather_than_failing(self):
        assert get_persona("nonexistent") is NEUTRAL
        assert get_persona(None) is NEUTRAL


class TestVariantMapping:
    @pytest.mark.parametrize(
        ("variant", "expected"),
        [
            ("feminine", ANIME_GIRL),
            ("masculine", ANIME_BOY),
            ("neutral", NEUTRAL),
            ("unspecified", NEUTRAL),
            ("nonsense", NEUTRAL),
        ],
    )
    def test_variant_selects_the_voice(self, variant, expected):
        assert persona_for_variant(variant) is expected

    def test_the_mapping_matches_the_avatar_loader(self):
        """anime-g.glb resolves to 'feminine'; that must reach the voice."""
        from aera.hologram.loader import AvatarVariant

        for variant in AvatarVariant:
            # ALL_PERSONAS, not PERSONAS: an avatar with no declared variant
            # maps to the neutral fallback, which is deliberately absent from
            # the two offered in the picker.
            assert persona_for_variant(variant.value) in ALL_PERSONAS.values()


class TestEmotionResponse:
    @pytest.mark.parametrize("persona", [ANIME_GIRL, ANIME_BOY])
    def test_excitement_raises_pitch_and_sadness_lowers_it(self, persona):
        excited = persona.pitch_for(Emotion.EXCITED)
        neutral = persona.pitch_for(Emotion.NEUTRAL)
        sad = persona.pitch_for(Emotion.SAD)

        assert excited > neutral > sad

    @pytest.mark.parametrize("persona", [ANIME_GIRL, ANIME_BOY])
    def test_sadness_slows_delivery(self, persona):
        assert persona.speed_for(Emotion.SAD) < persona.speed_for(Emotion.EXCITED)

    def test_a_reserved_persona_moves_less(self):
        """pitch_range is what keeps the boy from sounding as animated."""
        girl_swing = ANIME_GIRL.pitch_for(Emotion.EXCITED) / ANIME_GIRL.pitch_for(Emotion.SAD)
        boy_swing = ANIME_BOY.pitch_for(Emotion.EXCITED) / ANIME_BOY.pitch_for(Emotion.SAD)

        assert girl_swing > boy_swing

    def test_neutral_is_the_baseline(self):
        assert ANIME_GIRL.pitch_for(Emotion.NEUTRAL) == ANIME_GIRL.base_pitch_hz


class TestSynthesis:
    def test_writes_a_playable_wav(self, tmp_path):
        path, duration, visemes = synthesize_wav(
            "Hello there", ANIME_GIRL, path=tmp_path / "out.wav"
        )

        assert path.is_file()
        with wave.open(str(path)) as handle:
            assert handle.getframerate() == SAMPLE_RATE
            assert handle.getnframes() > 0
        assert duration > 0
        assert visemes

    @pytest.mark.parametrize("persona", [ANIME_GIRL, ANIME_BOY, NEUTRAL])
    def test_the_audio_carries_the_persona_pitch(self, persona, tmp_path):
        """Energy must peak at the persona's fundamental, not a neighbour's.

        Measured on a sustained vowel. Ordinary speech switches viseme every
        few frames, so a fixed analysis window straddles two formant settings
        and reads their transition rather than the pitch.
        """
        path, _, _ = synthesize_wav("aaa " * 40, persona, path=tmp_path / "o.wav")

        energies = {
            candidate.base_pitch_hz: energy_at(path, candidate.base_pitch_hz)
            for candidate in (ANIME_GIRL, ANIME_BOY, NEUTRAL)
        }

        assert max(energies, key=energies.get) == persona.base_pitch_hz

    def test_a_sustained_vowel_is_one_segment_not_many(self, tmp_path):
        """Repeated shapes collapse before they reach the synthesiser.

        Each keyframe is rendered with an attack and a decay, so leaving the
        repeats in chopped a held vowel into 120 ramped segments. That
        amplitude-modulated the tone at ~13 Hz and smeared the fundamental
        badly enough that anime-g's 255 Hz measured weaker than a persona
        that was not even speaking.
        """
        _, _, visemes = synthesize_wav("aaa " * 40, ANIME_GIRL, path=tmp_path / "o.wav")

        assert len(visemes) == 1

    def test_real_speech_still_animates(self, tmp_path):
        """Collapsing repeats must not flatten a line that does change shape."""
        _, _, visemes = synthesize_wav("hello world", ANIME_GIRL, path=tmp_path / "o.wav")

        assert len({frame["shape"] for frame in visemes}) > 1

    def test_two_personas_produce_different_audio(self, tmp_path):
        girl, _, _ = synthesize_wav("Same words", ANIME_GIRL, path=tmp_path / "g.wav")
        boy, _, _ = synthesize_wav("Same words", ANIME_BOY, path=tmp_path / "b.wav")

        assert girl.read_bytes() != boy.read_bytes()

    def test_no_path_means_no_file_but_still_timing(self):
        """The hologram needs visemes even when audio is not being written."""
        path, duration, visemes = synthesize_wav("Hello", ANIME_GIRL, path=None)

        assert path is None
        assert duration > 0
        assert visemes

    def test_audio_does_not_clip(self, tmp_path):
        """Clipping would be audible distortion on every utterance."""
        path, _, _ = synthesize_wav("Testing levels", ANIME_GIRL, path=tmp_path / "o.wav")

        with wave.open(str(path)) as handle:
            samples = array.array("h")
            samples.frombytes(handle.readframes(handle.getnframes()))

        assert max(abs(s) for s in samples) < 32_000

    def test_sad_speech_lasts_longer_than_excited(self, tmp_path):
        _, excited, _ = synthesize_wav(
            "A sentence of several words", ANIME_GIRL,
            emotion=Emotion.EXCITED, path=tmp_path / "e.wav",
        )
        _, sad, _ = synthesize_wav(
            "A sentence of several words", ANIME_GIRL,
            emotion=Emotion.SAD, path=tmp_path / "s.wav",
        )

        assert sad > excited

    def test_empty_text_does_not_crash(self, tmp_path):
        path, duration, _ = synthesize_wav("", ANIME_GIRL, path=tmp_path / "o.wav")

        assert path.is_file()
        assert duration > 0


class TestPersonaBackend:
    async def test_synthesise_reports_the_persona(self, tmp_path):
        from aera.voice.engine import SpeechRequest

        backend = PersonaTTS(ANIME_GIRL, output_dir=tmp_path)

        result = await backend.synthesize(SpeechRequest(text="Hello"))

        assert result.engine == "persona:anime-g"
        assert result.audio_path

    async def test_switching_persona_changes_the_output(self, tmp_path):
        from aera.voice.engine import SpeechRequest

        backend = PersonaTTS(ANIME_GIRL, output_dir=tmp_path)
        first = await backend.synthesize(SpeechRequest(text="Hello"))

        backend.use(ANIME_BOY)
        second = await backend.synthesize(SpeechRequest(text="Hello"))

        assert first.audio_path != second.audio_path

    async def test_without_an_output_dir_no_file_is_written(self):
        from aera.voice.engine import SpeechRequest

        result = await PersonaTTS(ANIME_GIRL).synthesize(SpeechRequest(text="Hello"))

        assert result.audio_path is None
        # Timing and lip-sync still have to work.
        assert result.visemes


class TestVoiceApi:
    @pytest.fixture
    def client(self, config):
        with TestClient(create_app(config)) as c:
            yield c

    def test_lists_personas(self, client):
        data = client.get("/api/v1/voice/personas").json()["data"]

        assert {p["id"] for p in data["personas"]} >= {"anime-g", "anime-b"}

    def test_admits_it_is_not_a_speech_engine(self, client):
        """Audio that sounds like speech but is not must say so."""
        data = client.get("/api/v1/voice/personas").json()["data"]

        assert data["synthesises_speech"] is False
        assert data["note"] == FORMANT_NOTE

    @pytest.mark.parametrize("persona_id", ["anime-g", "anime-b"])
    def test_switching_voice(self, client, persona_id):
        """Exactly two voices are offered. "aera" still resolves internally
        as the fallback, but is no longer something a user picks."""
        response = client.post(f"/api/v1/voice/personas/{persona_id}")

        assert response.status_code == 200
        assert response.json()["data"]["id"] == persona_id
        assert client.get("/api/v1/voice/personas").json()["data"]["active"] == persona_id

    def test_unknown_persona_lists_the_alternatives(self, client):
        response = client.post("/api/v1/voice/personas/nope")

        assert response.status_code == 400
        # The error names the built-in voices and any the user has added,
        # since either is a valid choice.
        assert "anime-g" in response.json()["details"]["builtin"]

    def test_preview_does_not_change_the_active_voice(self, client):
        client.post("/api/v1/voice/personas/anime-b")

        client.post("/api/v1/voice/preview?persona_id=anime-g")

        assert client.get("/api/v1/voice/personas").json()["data"]["active"] == "anime-b"

    def test_preview_reports_pitch_and_timing(self, client):
        data = client.post(
            "/api/v1/voice/preview?persona_id=anime-g&emotion=excited"
        ).json()["data"]

        assert data["pitch_hz"] > ANIME_GIRL.base_pitch_hz
        assert data["visemes"] > 0

    def test_speaking_uses_the_selected_persona(self, client):
        client.post("/api/v1/voice/personas/anime-b")

        result = client.post("/api/v1/voice/speak", json={"text": "Hello"}).json()["data"]

        assert result["engine"] == "persona:anime-b"

    def test_selecting_an_avatar_selects_its_voice(self, client, tmp_path):
        """Choosing anime-g should make AERA sound like anime-g."""
        import json as jsonlib

        library = client.app.state.kernel.avatars
        library.root.mkdir(parents=True, exist_ok=True)
        (library.root / "anime-g.gltf").write_text(
            jsonlib.dumps({"asset": {"version": "2.0"}, "meshes": [], "accessors": []})
        )
        client.post("/api/v1/avatars/scan")
        model = client.get("/api/v1/avatars").json()["data"]["avatars"][0]

        response = client.post(f"/api/v1/avatars/active?model_id={model['id']}")

        assert response.json()["data"]["voice"]["id"] == "anime-g"
        assert client.get("/api/v1/voice/personas").json()["data"]["active"] == "anime-g"


class TestEmotionAcoustics:
    """Emotion changes more than pitch and pace.

    Before this, every feeling was the same voice faster or slower, higher or
    lower. Sadness and confidence differ in steadiness, breath and timbre --
    those are the cues that make an emotion recognisable rather than merely
    transposed.
    """

    def test_every_emotion_has_a_profile(self):
        from aera.voice.personas import EMOTION_ACOUSTICS

        for emotion in Emotion:
            assert emotion in EMOTION_ACOUSTICS

    def test_unknown_input_falls_back_to_neutral(self):
        from aera.voice.personas import EMOTION_ACOUSTICS, acoustics_for

        assert acoustics_for("nonsense") == EMOTION_ACOUSTICS[Emotion.NEUTRAL]

    def test_distress_is_less_steady_than_composure(self):
        from aera.voice.personas import acoustics_for

        # Jitter is the cycle-to-cycle instability of an upset voice.
        assert acoustics_for(Emotion.SAD).jitter > acoustics_for(Emotion.CONFIDENT).jitter

    def test_sadness_is_the_breathiest(self):
        from aera.voice.personas import EMOTION_ACOUSTICS

        breath = {e: a.breathiness for e, a in EMOTION_ACOUSTICS.items()}
        assert max(breath, key=breath.get) is Emotion.SAD

    def test_confidence_and_seriousness_do_not_shake(self):
        from aera.voice.personas import acoustics_for

        # Gravity is controlled; a wavering voice would undercut it.
        assert acoustics_for(Emotion.CONFIDENT).tremor == 0.0
        assert acoustics_for(Emotion.SERIOUS).tremor == 0.0

    def test_arousal_raises_the_vibrato_rate(self):
        from aera.voice.personas import acoustics_for

        assert (
            acoustics_for(Emotion.EXCITED).vibrato_rate
            > acoustics_for(Emotion.NEUTRAL).vibrato_rate
            > acoustics_for(Emotion.SAD).vibrato_rate
        )

    def test_low_mood_darkens_the_timbre(self):
        from aera.voice.personas import acoustics_for

        assert acoustics_for(Emotion.SAD).brightness_scale < 1.0
        assert acoustics_for(Emotion.EXCITED).brightness_scale > 1.0

    def test_urgency_sharpens_the_onset(self):
        from aera.voice.personas import acoustics_for

        assert acoustics_for(Emotion.EXCITED).attack > acoustics_for(Emotion.CALM).attack

    def test_the_profiles_are_genuinely_distinct(self):
        """Nine labels sharing one profile would be nine names for silence."""
        from aera.voice.personas import EMOTION_ACOUSTICS

        signatures = {tuple(a.to_dict().values()) for a in EMOTION_ACOUSTICS.values()}
        assert len(signatures) == len(EMOTION_ACOUSTICS)


class TestAcousticsInTheAudio:
    """The profiles must reach the waveform, not just the dataclass."""

    @staticmethod
    def _samples(path):
        import array
        import wave

        with wave.open(str(path)) as handle:
            rate = handle.getframerate()
            data = array.array("h")
            data.frombytes(handle.readframes(handle.getnframes()))
        return rate, [v / 32768 for v in data[rate // 2 : rate // 2 + 8192]]

    def _noise_ratio(self, path):
        """Residual after smoothing, relative to signal level.

        A raw sample-difference metric conflates breath noise with formant
        brightness, and sadness lowers both -- it measured *smoother* than
        confidence despite carrying three times the breath.
        """
        _, seg = self._samples(path)
        smoothed = [(seg[i - 1] + seg[i] + seg[i + 1]) / 3 for i in range(1, len(seg) - 1)]
        residual = sum(abs(seg[i + 1] - smoothed[i]) for i in range(len(smoothed))) / len(smoothed)
        level = sum(abs(v) for v in seg) / len(seg)
        return residual / max(1e-9, level)

    def _envelope_swing(self, path):
        """How much the loudness wobbles during the steady part of a note.

        Measured as spread about the mean, and with the onset and release
        discarded. A max-minus-min over the whole clip reads the attack and
        decay ramps instead: those run from silence to full amplitude, which
        swamps a 5% tremor, and the metric stayed positive even for a
        profile whose tremor is exactly zero.
        """
        import array
        import statistics
        import wave

        # Read the whole file, not the 8192-frame slice the other metrics
        # use: tremor is a ~4 Hz wobble, so a 0.37 s window holds barely one
        # cycle and there is nothing left to measure once the ramps at each
        # end are discarded.
        with wave.open(str(path)) as handle:
            rate = handle.getframerate()
            data = array.array("h")
            data.frombytes(handle.readframes(handle.getnframes()))

        window = rate // 20
        peaks = [
            max(abs(v) for v in data[i : i + window])
            for i in range(0, len(data) - window, window)
        ]
        core = [p for p in peaks[2:-2] if p > 0]
        if len(core) < 3:
            return 0.0
        return statistics.pstdev(core) / max(1e-9, statistics.mean(core))

    def test_breathiness_is_audible(self, tmp_path):
        sad, _, _ = synthesize_wav("aaa " * 30, ANIME_GIRL, emotion=Emotion.SAD, path=tmp_path / "s.wav")
        firm, _, _ = synthesize_wav(
            "aaa " * 30, ANIME_GIRL, emotion=Emotion.CONFIDENT, path=tmp_path / "c.wav"
        )

        assert self._noise_ratio(sad) > self._noise_ratio(firm)

    def test_tremor_is_audible(self, tmp_path):
        sad, _, _ = synthesize_wav("aaa " * 30, ANIME_GIRL, emotion=Emotion.SAD, path=tmp_path / "s.wav")
        firm, _, _ = synthesize_wav(
            "aaa " * 30, ANIME_GIRL, emotion=Emotion.CONFIDENT, path=tmp_path / "c.wav"
        )

        assert self._envelope_swing(sad) > self._envelope_swing(firm)

    def test_two_emotions_render_differently(self, tmp_path):
        sad, _, _ = synthesize_wav("Hello there", ANIME_GIRL, emotion=Emotion.SAD, path=tmp_path / "s.wav")
        happy, _, _ = synthesize_wav(
            "Hello there", ANIME_GIRL, emotion=Emotion.HAPPY, path=tmp_path / "h.wav"
        )

        assert sad.read_bytes() != happy.read_bytes()

    def test_rendering_is_deterministic_across_processes(self, tmp_path):
        """The seed must not depend on hash(), which Python randomises.

        Seeding from hash() gave renders that were stable within a run but
        differed between runs, and the jitter moved the measured pitch enough
        to fail the pitch test intermittently.
        """
        import subprocess
        import sys

        script = (
            "import hashlib,sys;"
            "from pathlib import Path;"
            "from aera.voice.personas import ANIME_GIRL, synthesize_wav;"
            "from aera.voice.engine import Emotion;"
            f"p,_,_=synthesize_wav('aaa '*20, ANIME_GIRL, emotion=Emotion.SAD, path=Path(r'{tmp_path}')/'x.wav');"
            "sys.stdout.write(hashlib.sha256(p.read_bytes()).hexdigest())"
        )
        digests = {
            subprocess.run(
                [sys.executable, "-c", script], capture_output=True, text=True, check=True
            ).stdout
            for _ in range(2)
        }

        assert len(digests) == 1

    def test_rendering_is_deterministic(self, tmp_path):
        """Noise must be seeded, or the same line differs on every render."""
        first, _, _ = synthesize_wav("Hello", ANIME_GIRL, emotion=Emotion.SAD, path=tmp_path / "a.wav")
        second, _, _ = synthesize_wav("Hello", ANIME_GIRL, emotion=Emotion.SAD, path=tmp_path / "b.wav")

        assert first.read_bytes() == second.read_bytes()

    def test_added_noise_does_not_clip(self, tmp_path):
        """Breath is summed on top of the tone; the total must stay in range."""
        import array
        import wave

        path, _, _ = synthesize_wav(
            "Testing levels", ANIME_GIRL, emotion=Emotion.SAD, path=tmp_path / "o.wav"
        )
        with wave.open(str(path)) as handle:
            data = array.array("h")
            data.frombytes(handle.readframes(handle.getnframes()))

        assert max(abs(v) for v in data) < 32_000
