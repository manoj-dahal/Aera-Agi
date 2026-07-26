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
            assert persona_for_variant(variant.value) in PERSONAS.values()


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

    @pytest.mark.parametrize("persona_id", ["anime-g", "anime-b", "aera"])
    def test_switching_voice(self, client, persona_id):
        response = client.post(f"/api/v1/voice/personas/{persona_id}")

        assert response.status_code == 200
        assert response.json()["data"]["id"] == persona_id
        assert client.get("/api/v1/voice/personas").json()["data"]["active"] == persona_id

    def test_unknown_persona_lists_the_alternatives(self, client):
        response = client.post("/api/v1/voice/personas/nope")

        assert response.status_code == 400
        assert "anime-g" in response.json()["details"]["available"]

    def test_preview_does_not_change_the_active_voice(self, client):
        client.post("/api/v1/voice/personas/aera")

        client.post("/api/v1/voice/preview?persona_id=anime-g")

        assert client.get("/api/v1/voice/personas").json()["data"]["active"] == "aera"

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
        rate, seg = self._samples(path)
        window = rate // 20
        peaks = [max(abs(v) for v in seg[i : i + window]) for i in range(0, len(seg) - window, window)]
        if not peaks:
            return 0.0
        return (max(peaks) - min(peaks)) / max(1e-9, sum(peaks) / len(peaks))

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
