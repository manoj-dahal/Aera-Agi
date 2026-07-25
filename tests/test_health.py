"""Smoke tests for the AERA Core API."""

from fastapi.testclient import TestClient

from services.core.main import app

client = TestClient(app)


def test_health() -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_system_info() -> None:
    res = client.get("/api/system/info")
    assert res.status_code == 200
    assert res.json()["name"] == "AERA"
