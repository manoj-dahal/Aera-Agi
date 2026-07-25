"""Smoke tests for the AERA Core API."""


def test_health(client) -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_system_info(client) -> None:
    res = client.get("/api/system/info")
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "AERA"
    assert body["modules"]["memory_graph"] == "active"
