"""Real TTS backend adapters.

For several turns the answer to "how do I get actual speech?" was "implement
TTSBackend yourself". The persona-to-engine mapping was documented but never
written, so a user had to work out how pitch and intensity translate into
Piper's length scale by reading a dataclass. These cover the adapters that
close that gap.

No voice model ships with AERA, so the Piper adapter is exercised against a
stubbed model. That still verifies the part that can be wrong: whether the
adapter calls Piper's real API with correctly derived parameters.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from aera.api.app import create_app
from aera.core.errors import ValidationError
from aera.voice.backends import (
    PiperTTS,
    SystemTTS,
    _length_scale,
    _noise_scale,
    best_available,
    probe_all,
)
from aera.voice.engine import Emotion, SpeechRequest
from aera.voice.personas import ANIME_BOY, ANIME_GIRL, PersonaTTS


@pytest.fixture
def stub_model(tmp_path):
    """A Piper model that exists on disk but is never really loaded."""
    model = tmp_path / "voice.onnx"
    model.write_bytes(b"stub")
    (tmp_path / "voice.onnx.json").write_text("{}")
    return model


def _fake_voice(frames: int = 44_100):
    """A PiperVoice whose synthesize_wav writes a real WAV header."""

    def synthesize_wav(text, handle, syn_config=None, **kwargs):
        synthesize_wav.calls.append({"text": text, "config": syn_config})
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(22_050)
        handle.writeframes(b"\0" * frames)

    synthesize_wav.calls = []
    voice = MagicMock()
    voice.synthesize_wav = synthesize_wav
    return voice


class TestParameterMapping:
    """Persona and emotion have to become engine parameters correctly."""

    def test_length_scale_inverts_speed(self):
        """Piper's length scale is the inverse of a speed multiplier."""
        fast = _length_scale(ANIME_GIRL, Emotion.EXCITED)
        slow = _length_scale(ANIME_GIRL, Emotion.SAD)

        assert fast < slow

    def test_length_scale_respects_the_persona_hint(self):
        # anime-g carries length_scale 0.94; anime-b carries 1.0.
        girl = _length_scale(ANIME_GIRL, Emotion.NEUTRAL)
        boy = _length_scale(ANIME_BOY, Emotion.NEUTRAL)

        assert girl < boy

    def test_length_scale_stays_in_a_sane_range(self):
        for emotion in Emotion:
            assert 0.4 <= _length_scale(ANIME_GIRL, emotion) <= 2.5

    def test_noise_scale_rises_with_distress(self):
        """Piper has no breathiness control; noise is the nearest proxy."""
        assert _noise_scale(Emotion.SAD) > _noise_scale(Emotion.CONFIDENT)

    def test_noise_scale_stays_in_a_sane_range(self):
        for emotion in Emotion:
            assert 0.2 <= _noise_scale(emotion) <= 1.2


class TestPiperProbe:
    def test_reports_a_missing_model(self):
        status = PiperTTS.probe(None)

        assert status.available is False
        assert "no voice model" in status.detail

    def test_the_remedy_names_where_to_get_one(self):
        """"Not configured" without a source leaves the user stuck."""
        status = PiperTTS.probe(None)

        assert "huggingface.co/rhasspy/piper-voices" in status.remedy

    def test_reports_a_path_that_does_not_exist(self, tmp_path):
        status = PiperTTS.probe(tmp_path / "absent.onnx")

        assert status.available is False
        assert "not found" in status.detail

    def test_reports_a_model_missing_its_config(self, tmp_path):
        """A .onnx without its .onnx.json fails deep inside Piper otherwise."""
        model = tmp_path / "voice.onnx"
        model.write_bytes(b"stub")

        status = PiperTTS.probe(model)

        assert status.available is False
        assert "config" in status.detail

    def test_a_complete_model_is_available(self, stub_model):
        assert PiperTTS.probe(stub_model).available is True

    def test_loading_without_a_model_raises_with_the_remedy(self):
        with pytest.raises(ValidationError) as excinfo:
            PiperTTS("").load()

        assert excinfo.value.details["remedy"]


class TestPiperSynthesis:
    async def test_writes_audio_and_reports_true_duration(self, stub_model, tmp_path):
        voice = _fake_voice()

        with patch("piper.PiperVoice.load", return_value=voice):
            backend = PiperTTS(stub_model, persona=ANIME_GIRL, output_dir=tmp_path)
            result = await backend.synthesize(SpeechRequest(text="Hello"))

        assert result.audio_path
        # 44100 bytes of 16-bit mono at 22050 Hz is exactly one second.
        assert result.duration_ms == pytest.approx(1000.0, abs=1)

    async def test_passes_derived_parameters_to_piper(self, stub_model, tmp_path):
        """The adapter must send a real SynthesisConfig, not defaults."""
        voice = _fake_voice()

        with patch("piper.PiperVoice.load", return_value=voice):
            backend = PiperTTS(stub_model, persona=ANIME_GIRL, output_dir=tmp_path)
            await backend.synthesize(SpeechRequest(text="Hi", emotion=Emotion.SAD))

        config = voice.synthesize_wav.calls[0]["config"]
        assert config.length_scale == pytest.approx(
            _length_scale(ANIME_GIRL, Emotion.SAD), abs=1e-6
        )
        assert config.noise_scale == pytest.approx(_noise_scale(Emotion.SAD), abs=1e-6)

    async def test_emotion_changes_the_parameters(self, stub_model, tmp_path):
        voice = _fake_voice()

        with patch("piper.PiperVoice.load", return_value=voice):
            backend = PiperTTS(stub_model, persona=ANIME_GIRL, output_dir=tmp_path)
            await backend.synthesize(SpeechRequest(text="Hi", emotion=Emotion.EXCITED))
            await backend.synthesize(SpeechRequest(text="Hi", emotion=Emotion.SAD))

        first, second = (call["config"] for call in voice.synthesize_wav.calls)
        assert first.length_scale != second.length_scale

    async def test_reports_the_persona_in_the_engine_name(self, stub_model, tmp_path):
        voice = _fake_voice()

        with patch("piper.PiperVoice.load", return_value=voice):
            backend = PiperTTS(stub_model, persona=ANIME_BOY, output_dir=tmp_path)
            result = await backend.synthesize(SpeechRequest(text="Hi"))

        assert result.engine == "piper:anime-b"

    async def test_switching_persona_changes_the_output(self, stub_model, tmp_path):
        voice = _fake_voice()

        with patch("piper.PiperVoice.load", return_value=voice):
            backend = PiperTTS(stub_model, persona=ANIME_GIRL, output_dir=tmp_path)
            first = await backend.synthesize(SpeechRequest(text="Hi"))
            backend.use(ANIME_BOY)
            second = await backend.synthesize(SpeechRequest(text="Hi"))

        assert first.audio_path != second.audio_path

    async def test_still_produces_visemes(self, stub_model, tmp_path):
        """The hologram animates regardless of which engine speaks."""
        voice = _fake_voice()

        with patch("piper.PiperVoice.load", return_value=voice):
            backend = PiperTTS(stub_model, persona=ANIME_GIRL, output_dir=tmp_path)
            result = await backend.synthesize(SpeechRequest(text="Hello there"))

        assert result.visemes


class TestSystemBackend:
    def test_probe_is_honest_when_nothing_is_installed(self):
        status = SystemTTS.probe()

        # This sandbox has no speech binary; the probe must say so rather
        # than claiming availability and failing at synthesis.
        if not status.available:
            assert "no system speech binary" in status.detail
            assert "espeak-ng" in status.remedy

    def test_espeak_command_carries_pitch_and_rate(self):
        backend = SystemTTS(persona=ANIME_GIRL, binary="espeak-ng")

        command = backend._command(SpeechRequest(text="Hi"), Path("/tmp/o.wav"))

        assert "-p" in command and "-s" in command
        pitch = int(command[command.index("-p") + 1])
        assert 0 <= pitch <= 99

    def test_a_higher_persona_maps_to_a_higher_espeak_pitch(self):
        girl = SystemTTS(persona=ANIME_GIRL, binary="espeak-ng")
        boy = SystemTTS(persona=ANIME_BOY, binary="espeak-ng")
        request = SpeechRequest(text="Hi")

        girl_cmd = girl._command(request, Path("/tmp/a.wav"))
        boy_cmd = boy._command(request, Path("/tmp/b.wav"))

        assert int(girl_cmd[girl_cmd.index("-p") + 1]) > int(boy_cmd[boy_cmd.index("-p") + 1])

    def test_macos_say_uses_its_own_flags(self):
        """`say` takes no pitch argument; passing espeak's would fail."""
        backend = SystemTTS(persona=ANIME_GIRL, binary="say")

        command = backend._command(SpeechRequest(text="Hi"), Path("/tmp/o.wav"))

        assert "-p" not in command
        assert "-o" in command

    async def test_synthesising_without_a_binary_explains_itself(self):
        backend = SystemTTS(persona=ANIME_GIRL, binary=None)

        with pytest.raises(ValidationError) as excinfo:
            await backend.synthesize(SpeechRequest(text="Hi"))

        assert excinfo.value.details["remedy"]


class TestSelection:
    def test_probe_all_lists_every_backend(self):
        names = {status.name for status in probe_all()}

        assert names == {"piper", "system", "persona"}

    def test_the_bundled_synthesiser_is_always_available(self):
        """The list must never be empty, or the voice has nowhere to go."""
        persona = next(s for s in probe_all() if s.name == "persona")

        assert persona.available is True

    def test_it_admits_the_bundled_engine_is_not_speech(self):
        persona = next(s for s in probe_all() if s.name == "persona")

        assert "lip-sync only" in persona.detail

    def test_falls_back_when_nothing_real_is_installed(self):
        backend = best_available(ANIME_GIRL)

        assert isinstance(backend, PersonaTTS)

    def test_prefers_piper_when_a_model_exists(self, stub_model):
        backend = best_available(ANIME_GIRL, piper_model=stub_model)

        assert isinstance(backend, PiperTTS)


class TestBackendApi:
    @pytest.fixture
    def client(self, config):
        with TestClient(create_app(config)) as c:
            yield c

    def test_lists_backends_with_their_status(self, client):
        data = client.get("/api/v1/voice/backends").json()["data"]

        assert len(data["backends"]) == 3
        assert data["active"]

    def test_says_whether_it_is_producing_real_speech(self, client):
        """A caller must not have to guess which engine answered."""
        data = client.get("/api/v1/voice/backends").json()["data"]

        assert data["synthesises_speech"] is False

    def test_every_unavailable_backend_offers_a_remedy(self, client):
        data = client.get("/api/v1/voice/backends").json()["data"]

        for backend in data["backends"]:
            if not backend["available"]:
                assert backend["remedy"], f"{backend['name']} says no with no way forward"
