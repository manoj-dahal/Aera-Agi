"""Shared pytest fixtures for the AERA test suite."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    """API client backed by a throwaway database and no local LLM."""
    monkeypatch.setenv("AERA_MEMORY_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("LOCAL_LLM_ENABLED", "false")
    from services.core.main import app

    with TestClient(app) as c:
        yield c
