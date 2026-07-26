# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Tests for user file uploads.

Before this existed, the only upload endpoint was the avatar library, so a
file dropped on the dashboard could not reach the backend at all -- the UI
sent the filename as chat text and the model was asked about a path it could
not open.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from aera.api.app import create_app
from aera.core.errors import ValidationError
from aera.services.uploads import (
    UploadStore,
    agent_for,
    classify,
    safe_name,
)


@pytest.fixture
def store(tmp_path):
    return UploadStore(tmp_path / "uploads")


@pytest.fixture
def client(config):
    with TestClient(create_app(config)) as c:
        yield c


class TestClassification:
    @pytest.mark.parametrize(
        ("filename", "kind"),
        [
            ("photo.PNG", "image"),
            ("clip.mp4", "video"),
            ("voice.wav", "audio"),
            ("report.pdf", "document"),
            ("notes.md", "text"),
            ("main.py", "code"),
            ("bundle.zip", "archive"),
            ("anime-g.glb", "model"),
            ("mystery.qqq", "unknown"),
        ],
    )
    def test_kind_from_extension(self, filename, kind):
        assert classify(filename) == kind

    @pytest.mark.parametrize(
        ("filename", "agent"),
        [
            ("photo.png", "vision"),
            ("voice.wav", "audio"),
            ("report.pdf", "document"),
            ("main.py", "code_review"),
        ],
    )
    def test_routes_to_the_right_agent(self, filename, agent):
        assert agent_for(filename) == agent

    def test_unknown_types_still_get_an_agent(self):
        """The document agent reports honestly when it cannot parse."""
        assert agent_for("mystery.qqq") == "document"


class TestSafeName:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("report.pdf", "report.pdf"),
            # Directory components must never survive.
            ("../../etc/passwd", "passwd"),
            ("/absolute/path/file.txt", "file.txt"),
            ("C:\\Users\\me\\notes.md", "notes.md"),
            ("with spaces.txt", "with_spaces.txt"),
        ],
    )
    def test_sanitises(self, raw, expected):
        assert safe_name(raw) == expected

    def test_a_name_that_reduces_to_nothing_gets_a_default(self):
        assert safe_name("...") == "upload"
        assert safe_name("///") == "upload"

    def test_long_names_are_truncated(self):
        assert len(safe_name("a" * 400 + ".txt")) <= 120


class TestStore:
    def test_stores_and_retrieves(self, store):
        record = store.store_bytes("notes.md", b"hello")

        assert store.get(record.id).name == "notes.md"
        assert record.path.read_bytes() == b"hello"

    def test_identical_bytes_are_not_duplicated(self, store):
        """Dragging the same file in twice should not leave two copies."""
        first = store.store_bytes("notes.md", b"same")
        second = store.store_bytes("notes.md", b"same")

        assert first.id == second.id
        assert len(list(store.root.iterdir())) == 1

    def test_different_bytes_get_different_ids(self, store):
        assert store.store_bytes("a.txt", b"one").id != store.store_bytes("a.txt", b"two").id

    def test_rejects_oversized_input(self, store, monkeypatch):
        from aera.services import uploads as module

        monkeypatch.setattr(module, "MAX_UPLOAD_BYTES", 8)

        with pytest.raises(ValidationError, match="upload limit"):
            store.store_bytes("big.bin", b"\0" * 64)

    def test_adopting_a_local_file_does_not_copy_it(self, store, tmp_path):
        """The desktop shell has a real path; duplicating it is wasteful."""
        source = tmp_path / "local.md"
        source.write_text("content")

        record = store.adopt(source)

        assert record.path == source
        assert not (store.root / "local.md").exists()

    def test_adopting_a_missing_file_fails(self, store, tmp_path):
        with pytest.raises(ValidationError, match="not found"):
            store.adopt(tmp_path / "ghost.md")

    def test_removing_an_adopted_file_leaves_the_original(self, store, tmp_path):
        """AERA only deletes files it owns."""
        source = tmp_path / "local.md"
        source.write_text("content")
        record = store.adopt(source)

        store.remove(record.id)

        assert source.is_file()

    def test_removing_a_stored_file_deletes_it(self, store):
        record = store.store_bytes("gone.md", b"x")

        store.remove(record.id)

        assert not record.path.exists()
        with pytest.raises(ValidationError):
            store.get(record.id)

    def test_scan_rebuilds_the_index(self, store):
        """The index is in memory, so a restart has to recover from disk."""
        record = store.store_bytes("notes.md", b"hello")
        store._uploads.clear()

        restored = store.scan()

        assert [u.id for u in restored] == [record.id]

    def test_scan_ignores_partial_writes(self, store):
        store.root.mkdir(parents=True, exist_ok=True)
        (store.root / ".incoming-123-half.bin").write_bytes(b"partial")

        assert store.scan() == []

    def test_a_file_deleted_underneath_is_not_handed_back(self, store):
        record = store.store_bytes("notes.md", b"hello")
        record.path.unlink()

        with pytest.raises(ValidationError, match="no longer on disk"):
            store.get(record.id)

    def test_stats_group_by_kind(self, store):
        store.store_bytes("a.png", b"1")
        store.store_bytes("b.png", b"2")
        store.store_bytes("c.md", b"3")

        assert store.stats()["by_kind"] == {"image": 2, "text": 1}


class TestUploadApi:
    def test_upload_and_list(self, client):
        response = client.post(
            "/api/v1/uploads",
            files={"file": ("notes.md", io.BytesIO(b"# Title"), "text/markdown")},
        )

        assert response.status_code == 200
        record = response.json()["data"]
        assert record["kind"] == "text"
        assert record["suggested_agent"] == "document"
        assert client.get("/api/v1/uploads").json()["data"]["count"] == 1

    def test_empty_files_are_refused(self, client):
        """A zero-byte upload is a mistake, not a document."""
        response = client.post(
            "/api/v1/uploads", files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
        )

        assert response.status_code == 400
        assert "empty" in response.json()["error"]

    def test_oversized_uploads_leave_nothing_behind(self, client, monkeypatch):
        from aera.api.routers import uploads as router

        monkeypatch.setattr(router, "MAX_UPLOAD_BYTES", 4096)

        response = client.post(
            "/api/v1/uploads",
            files={"file": ("big.bin", io.BytesIO(b"\0" * 200_000), "application/octet-stream")},
        )

        assert response.status_code == 400
        assert "4 kB" in response.json()["error"]
        assert client.get("/api/v1/uploads").json()["data"]["count"] == 0

    def test_filter_by_kind(self, client):
        client.post("/api/v1/uploads", files={"file": ("a.png", b"\x89PNG", "image/png")})
        client.post("/api/v1/uploads", files={"file": ("b.md", b"text", "text/markdown")})

        data = client.get("/api/v1/uploads?kind=image").json()["data"]

        assert data["count"] == 1
        assert data["uploads"][0]["name"] == "a.png"

    def test_routing_table_matches_the_backend(self, client):
        """The drop indicator shows this before a file is released."""
        table = client.get("/api/v1/uploads/routing").json()["data"]

        assert table["by_extension"]["png"] == "image"
        assert table["by_kind"]["image"] == "vision"

    def test_download_returns_the_bytes(self, client):
        upload = client.post(
            "/api/v1/uploads", files={"file": ("notes.md", b"exact bytes", "text/markdown")}
        ).json()["data"]

        response = client.get(f"/api/v1/uploads/{upload['id']}/file")

        assert response.content == b"exact bytes"

    def test_analyse_runs_a_real_agent(self, client):
        upload = client.post(
            "/api/v1/uploads",
            files={"file": ("notes.md", b"The API listens on port 8080.", "text/markdown")},
        ).json()["data"]

        response = client.post(f"/api/v1/uploads/{upload['id']}/analyse")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["agent"] == "document"
        # The agent must have been given the stored path, not just a name.
        assert data["upload"]["id"] == upload["id"]

    def test_analyse_accepts_an_explicit_agent(self, client):
        upload = client.post(
            "/api/v1/uploads", files={"file": ("notes.md", b"content", "text/markdown")}
        ).json()["data"]

        response = client.post(f"/api/v1/uploads/{upload['id']}/analyse?agent=document")

        assert response.json()["data"]["agent"] == "document"

    def test_unknown_upload_is_reported(self, client):
        assert client.get("/api/v1/uploads/deadbeef").status_code == 400

    def test_delete(self, client):
        upload = client.post(
            "/api/v1/uploads", files={"file": ("gone.md", b"x", "text/markdown")}
        ).json()["data"]

        assert client.delete(f"/api/v1/uploads/{upload['id']}").status_code == 200
        assert client.get("/api/v1/uploads").json()["data"]["count"] == 0
