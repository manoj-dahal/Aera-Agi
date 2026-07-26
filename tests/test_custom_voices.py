# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Two default voices, plus whatever the user supplies.

AERA shipped three personas, one of which was an unnamed "AERA" that nobody
could meaningfully choose. The requirement is exactly two -- Girl and Boy --
and a way to add your own, which is the honest answer to "I want a different
voice" rather than guessing at a third.

A custom voice is a Piper ``.onnx`` model plus its ``.onnx.json`` config.
Unlike the two bundled personas it produces real articulated speech, so the
distinction has to survive into the API and the picker.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from aera.api.app import create_app
from aera.core.errors import ValidationError
from aera.services.voices import MIN_MODEL_BYTES, VoiceLibrary, inspect_model
from aera.voice.personas import ALL_PERSONAS, PERSONAS, get_persona


@pytest.fixture
def model(tmp_path):
    """A file that passes every validation check."""
    path = tmp_path / "my-voice.onnx"
    path.write_bytes(b"\x08" + b"\x00" * (MIN_MODEL_BYTES + 1000))
    (tmp_path / "my-voice.onnx.json").write_text(
        json.dumps(
            {
                "audio": {"sample_rate": 22050},
                "language": {"code": "en"},
                "num_speakers": 1,
            }
        )
    )
    return path


@pytest.fixture
def library(tmp_path):
    return VoiceLibrary(tmp_path / "voices")


class TestExactlyTwoDefaults:
    def test_the_picker_offers_two_voices(self):
        """Three was the bug: a list where one entry is an unnamed default
        is not a choice."""
        assert len(PERSONAS) == 2

    def test_they_are_girl_and_boy(self):
        labels = {p.label for p in PERSONAS.values()}

        assert labels == {"Girl (voice)", "Boy (voice)"}

    def test_the_neutral_fallback_is_not_offered(self):
        assert "aera" not in PERSONAS

    def test_but_it_still_resolves(self):
        """An existing config naming "aera" must keep working, and an unknown
        id has to land somewhere."""
        assert "aera" in ALL_PERSONAS
        assert get_persona("aera").id == "aera"
        assert get_persona("nonsense").id == "aera"


class TestModelValidation:
    """Validation happens at registration, while the user is watching.

    Deferring it to the first attempt to speak turns a clear "your download
    was truncated" into an opaque ONNX error at an unrelated moment.
    """

    def test_a_good_model_is_accepted(self, model):
        details = inspect_model(model)

        assert details["sample_rate"] == 22050
        assert details["language"] == "en"

    def test_an_audio_recording_is_refused_by_name(self, tmp_path):
        """Cloning a voice from a sample needs a training pipeline that is
        not bundled. Storing the file and ignoring it would be worse."""
        recording = tmp_path / "me.mp3"
        recording.write_bytes(b"ID3" + b"\x00" * 500)

        with pytest.raises(ValidationError, match="audio recording, not a voice model"):
            inspect_model(recording)

    def test_the_refusal_says_what_to_supply_instead(self, tmp_path):
        recording = tmp_path / "me.wav"
        recording.write_bytes(b"RIFF" + b"\x00" * 500)

        with pytest.raises(ValidationError) as caught:
            inspect_model(recording)

        assert "piper-voices" in caught.value.details["remedy"]

    def test_a_truncated_download_is_caught(self, tmp_path):
        small = tmp_path / "half.onnx"
        small.write_bytes(b"\x08" + b"\x00" * 100)

        with pytest.raises(ValidationError, match="too small"):
            inspect_model(small)

    def test_a_file_that_is_not_onnx_is_caught(self, tmp_path):
        """An HTML error page saved as .onnx is a common failed download."""
        fake = tmp_path / "oops.onnx"
        fake.write_bytes(b"<html>404</html>" + b"\x00" * MIN_MODEL_BYTES)

        with pytest.raises(ValidationError, match="does not look like an ONNX model"):
            inspect_model(fake)

    def test_a_missing_config_is_caught(self, tmp_path):
        lonely = tmp_path / "lonely.onnx"
        lonely.write_bytes(b"\x08" + b"\x00" * MIN_MODEL_BYTES)

        with pytest.raises(ValidationError, match="config is missing"):
            inspect_model(lonely)

    def test_a_config_without_a_sample_rate_is_caught(self, tmp_path):
        path = tmp_path / "v.onnx"
        path.write_bytes(b"\x08" + b"\x00" * MIN_MODEL_BYTES)
        (tmp_path / "v.onnx.json").write_text(json.dumps({"language": {"code": "en"}}))

        with pytest.raises(ValidationError, match="no sample rate"):
            inspect_model(path)

    def test_unparseable_json_is_caught(self, tmp_path):
        path = tmp_path / "v.onnx"
        path.write_bytes(b"\x08" + b"\x00" * MIN_MODEL_BYTES)
        (tmp_path / "v.onnx.json").write_text("{not json")

        with pytest.raises(ValidationError, match="not readable JSON"):
            inspect_model(path)

    def test_a_missing_file_is_named(self, tmp_path):
        with pytest.raises(ValidationError, match="no such model"):
            inspect_model(tmp_path / "absent.onnx")


class TestLibrary:
    def test_registering_makes_it_selectable(self, library, model):
        voice = library.add("My Voice", model)

        assert voice.id == "my-voice"
        assert library.get("my-voice") is not None

    def test_a_built_in_name_is_reserved(self, library, model):
        """Shadowing a bundled voice would make the picker ambiguous."""
        with pytest.raises(ValidationError, match="built-in voice"):
            library.add("anime-g", model)

    def test_a_duplicate_name_is_refused(self, library, model):
        library.add("My Voice", model)

        with pytest.raises(ValidationError, match="already registered"):
            library.add("My Voice", model)

    def test_a_voice_needs_a_name(self, library, model):
        with pytest.raises(ValidationError, match="needs a name"):
            library.add("   ", model)

    def test_an_unknown_variant_is_refused(self, library, model):
        with pytest.raises(ValidationError, match="unknown variant"):
            library.add("X", model, variant="alien")

    def test_it_survives_a_restart(self, tmp_path, model):
        root = tmp_path / "store"
        VoiceLibrary(root).add("Persisted", model)

        assert VoiceLibrary(root).get("persisted") is not None

    def test_a_corrupt_registry_does_not_break_startup(self, tmp_path):
        """The voice engine must still start; a broken file is not fatal."""
        root = tmp_path / "store"
        root.mkdir()
        (root / "voices.json").write_text("{{{ not json")

        assert VoiceLibrary(root).all() == []

    def test_a_missing_model_is_reported_not_deleted(self, tmp_path, model):
        """A model on an unmounted drive should reappear when it is mounted,
        so the entry is kept and flagged rather than removed."""
        root = tmp_path / "store"
        library = VoiceLibrary(root)
        library.add("Removable", model)
        model.unlink()

        reloaded = VoiceLibrary(root)

        assert reloaded.get("removable") is not None
        assert reloaded.get("removable").exists is False
        assert reloaded.available() == []

    def test_removing_leaves_the_model_file_alone(self, library, model):
        """The user chose where that file lives; deleting it is not ours."""
        library.add("Temp", model)

        assert library.remove("temp") is True
        assert model.is_file()

    def test_removing_something_absent_is_false_not_an_error(self, library):
        assert library.remove("never-existed") is False

    def test_it_becomes_a_persona(self, library, model):
        """So the rest of the voice engine needs no special case."""
        persona = library.add("Narrator", model, variant="masculine").to_persona()

        assert persona.id == "narrator"
        assert persona.variant == "masculine"
        assert persona.engine_hints["piper"]["model"].endswith(".onnx")

    def test_a_rejected_import_leaves_nothing_behind(self, tmp_path):
        """import_file copies before validating, so a rejection must clean
        up rather than leave a bad model in the store."""
        root = tmp_path / "store"
        library = VoiceLibrary(root)
        bad = tmp_path / "bad.onnx"
        bad.write_bytes(b"\x08" + b"\x00" * 100)

        with pytest.raises(ValidationError):
            library.import_file(bad, "Bad")

        assert not (root / "models" / "bad.onnx").exists()


class TestVoiceApi:
    @pytest.fixture
    def client(self, config):
        with TestClient(create_app(config)) as c:
            yield c

    def test_two_voices_are_listed_by_default(self, client):
        data = client.get("/api/v1/voice/personas").json()["data"]

        assert len(data["builtin"]) == 2
        assert data["custom"] == []

    def test_the_labels_are_girl_and_boy(self, client):
        data = client.get("/api/v1/voice/personas").json()["data"]
        labels = {p["label"] for p in data["personas"]}

        assert labels == {"Girl (voice)", "Boy (voice)"}

    def test_it_says_the_bundled_voices_do_not_speak(self, client):
        """The single most important honest claim in this feature."""
        data = client.get("/api/v1/voice/personas").json()["data"]

        assert data["synthesises_speech"] is False
        assert "add_your_own" in data

    def test_adding_a_voice(self, client, model):
        response = client.post(
            "/api/v1/voice/voices",
            json={"label": "My Voice", "model_path": str(model)},
        )

        assert response.status_code == 200
        assert response.json()["data"]["id"] == "my-voice"

    def test_an_added_voice_appears_in_the_picker(self, client, model):
        client.post(
            "/api/v1/voice/voices", json={"label": "My Voice", "model_path": str(model)}
        )
        data = client.get("/api/v1/voice/personas").json()["data"]

        assert "my-voice" in data["custom"]
        assert len(data["personas"]) == 3

    def test_an_added_voice_can_be_selected(self, client, model):
        client.post(
            "/api/v1/voice/voices", json={"label": "My Voice", "model_path": str(model)}
        )
        response = client.post("/api/v1/voice/personas/my-voice")

        assert response.status_code == 200
        assert response.json()["data"]["id"] == "my-voice"

    def test_a_label_is_required(self, client, model):
        response = client.post("/api/v1/voice/voices", json={"model_path": str(model)})

        assert response.status_code == 400
        assert "label" in response.json()["error"]

    def test_a_model_path_is_required(self, client):
        response = client.post("/api/v1/voice/voices", json={"label": "X"})

        assert response.status_code == 400

    def test_a_bad_model_is_refused_with_a_reason(self, client, tmp_path):
        recording = tmp_path / "voice.mp3"
        recording.write_bytes(b"ID3" + b"\x00" * 500)

        response = client.post(
            "/api/v1/voice/voices",
            json={"label": "Mine", "model_path": str(recording)},
        )

        assert response.status_code == 400
        assert "audio recording" in response.json()["error"]

    def test_inspect_validates_without_registering(self, client, model):
        """So a picker can check a path before committing to it."""
        data = client.post(
            "/api/v1/voice/voices/inspect", json={"model_path": str(model)}
        ).json()["data"]

        assert data["sample_rate"] == 22050
        assert client.get("/api/v1/voice/personas").json()["data"]["custom"] == []

    def test_removing_a_voice(self, client, model):
        client.post(
            "/api/v1/voice/voices", json={"label": "Temp", "model_path": str(model)}
        )
        response = client.delete("/api/v1/voice/voices/temp")

        assert response.status_code == 200
        assert client.get("/api/v1/voice/personas").json()["data"]["custom"] == []

    def test_removing_the_active_voice_falls_back(self, client, model):
        """Otherwise the engine points at a voice that no longer exists."""
        client.post(
            "/api/v1/voice/voices", json={"label": "Temp", "model_path": str(model)}
        )
        client.post("/api/v1/voice/personas/temp")

        data = client.delete("/api/v1/voice/voices/temp").json()["data"]

        assert data["active"] == "anime-g"

    def test_removing_something_absent_is_refused(self, client):
        assert client.delete("/api/v1/voice/voices/nope").status_code == 400

    def test_an_unknown_voice_lists_both_kinds(self, client):
        details = client.post("/api/v1/voice/personas/nope").json()["details"]

        assert "builtin" in details
        assert "custom" in details

    def test_a_voice_whose_model_vanished_cannot_be_selected(self, client, model):
        """Better than switching to it and failing at the first word."""
        client.post(
            "/api/v1/voice/voices", json={"label": "Gone", "model_path": str(model)}
        )
        model.unlink()

        response = client.post("/api/v1/voice/personas/gone")

        assert response.status_code == 400
        assert "missing" in response.json()["error"]
