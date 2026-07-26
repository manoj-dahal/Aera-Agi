# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Config, event bus, errors and security tests."""

from __future__ import annotations

import asyncio

import pytest

from aera.core.config import AeraConfig, load_config
from aera.core.errors import ConfigError, NotFoundError, PermissionDeniedError
from aera.core.events import EventBus, Topics
from aera.security import AuditLog, Permission, PermissionManager, SecretVault, generate_api_key


class TestConfig:
    def test_defaults(self):
        cfg = AeraConfig()
        assert cfg.system.name == "AERA"
        assert cfg.api.port == 8080
        assert cfg.api.prefix == "/api/v1"

    def test_loads_yaml(self, tmp_path):
        (tmp_path / "system.yaml").write_text("system:\n  environment: production\n  debug: true\n")
        (tmp_path / "api.yaml").write_text("api:\n  port: 9999\n")
        cfg = load_config(tmp_path, use_env=False)
        assert cfg.system.environment == "production"
        assert cfg.system.debug is True
        assert cfg.api.port == 9999

    def test_flat_yaml_also_supported(self, tmp_path):
        (tmp_path / "api.yaml").write_text("port: 7777\n")
        assert load_config(tmp_path, use_env=False).api.port == 7777

    def test_env_overrides_file(self, tmp_path, monkeypatch):
        (tmp_path / "api.yaml").write_text("api:\n  port: 1111\n")
        monkeypatch.setenv("AERA_API__PORT", "2222")
        assert load_config(tmp_path).api.port == 2222

    def test_explicit_overrides_win(self, tmp_path):
        cfg = load_config(tmp_path, overrides={"api": {"port": 3333}}, use_env=False)
        assert cfg.api.port == 3333

    def test_env_coercion(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AERA_SYSTEM__DEBUG", "true")
        monkeypatch.setenv("AERA_API__RATE_LIMIT_PER_MINUTE", "42")
        cfg = load_config(tmp_path)
        assert cfg.system.debug is True
        assert cfg.api.rate_limit_per_minute == 42

    def test_invalid_yaml_raises(self, tmp_path):
        (tmp_path / "api.yaml").write_text("api:\n  port: [unclosed\n")
        with pytest.raises(ConfigError):
            load_config(tmp_path, use_env=False)

    def test_invalid_value_raises(self, tmp_path):
        (tmp_path / "api.yaml").write_text("api:\n  port: 99999\n")
        with pytest.raises(ConfigError):
            load_config(tmp_path, use_env=False)

    def test_missing_dir_uses_defaults(self, tmp_path):
        assert load_config(tmp_path / "nope", use_env=False).api.port == 8080

    def test_enabled_agents(self):
        cfg = AeraConfig()
        cfg.agents.coding = False
        enabled = cfg.agents.enabled_agents()
        assert "core" in enabled and "coding" not in enabled

    def test_paths_expand(self, tmp_path):
        cfg = AeraConfig()
        cfg.system.storage = str(tmp_path / "s")
        cfg.ensure_dirs()
        assert cfg.storage_dir.exists()


class TestEventBus:
    async def test_publish_subscribe(self):
        bus = EventBus()
        got = []
        await bus.subscribe("test.topic", lambda e: got.append(e.payload))
        await bus.publish("test.topic", {"v": 1})
        assert got == [{"v": 1}]

    async def test_wildcard(self):
        bus = EventBus()
        got = []
        await bus.subscribe("agent.*", lambda e: got.append(e.topic))
        await bus.publish("agent.started", {})
        await bus.publish("memory.stored", {})
        assert got == ["agent.started"]

    async def test_catch_all(self):
        bus = EventBus()
        got = []
        await bus.subscribe("*", lambda e: got.append(e.topic))
        await bus.publish("a.b", {})
        await bus.publish("c.d", {})
        assert len(got) == 2

    async def test_async_handler(self):
        bus = EventBus()
        got = []

        async def handler(event):
            await asyncio.sleep(0)
            got.append(event.topic)

        await bus.subscribe("x", handler)
        await bus.publish("x", {})
        assert got == ["x"]

    async def test_failing_handler_is_isolated(self):
        bus = EventBus()
        got = []

        def bad(_):
            raise RuntimeError("boom")

        await bus.subscribe("t", bad)
        await bus.subscribe("t", lambda e: got.append(1))
        await bus.publish("t", {})
        assert got == [1]  # the good handler still ran

    async def test_unsubscribe(self):
        bus = EventBus()
        got = []
        sub = await bus.subscribe("t", lambda e: got.append(1))
        await bus.unsubscribe(sub)
        await bus.publish("t", {})
        assert got == []

    async def test_history(self):
        bus = EventBus()
        await bus.publish("a.1", {})
        await bus.publish("b.1", {})
        assert len(bus.history("a.*")) == 1
        assert len(bus.history()) == 2

    async def test_stream(self):
        bus = EventBus()
        stream = bus.stream("s.*")
        task = asyncio.create_task(stream.__anext__())
        await asyncio.sleep(0.01)
        await bus.publish("s.one", {"n": 1})
        event = await asyncio.wait_for(task, timeout=1)
        assert event.payload == {"n": 1}
        await stream.aclose()

    def test_topics_are_strings(self):
        assert Topics.AGENT_STARTED == "agent.started"


class TestSecurity:
    def test_vault_round_trip(self, tmp_path):
        vault = SecretVault(tmp_path / "key", tmp_path / "secrets.enc")
        vault.set("openai_api_key", "sk-secret-value")
        assert vault.get("openai_api_key") == "sk-secret-value"

    def test_vault_persists(self, tmp_path):
        SecretVault(tmp_path / "key", tmp_path / "s.enc").set("k", "v1")
        assert SecretVault(tmp_path / "key", tmp_path / "s.enc").get("k") == "v1"

    def test_vault_encrypts_on_disk(self, tmp_path):
        store = tmp_path / "s.enc"
        SecretVault(tmp_path / "key", store).set("k", "plaintext-secret")
        assert "plaintext-secret" not in store.read_text()

    def test_vault_masks(self, tmp_path):
        vault = SecretVault(tmp_path / "key", tmp_path / "s.enc")
        vault.set("k", "abcdefghijklmnop")
        masked = vault.masked()["k"]
        assert masked.startswith("abcd") and masked.endswith("mnop") and "*" in masked

    def test_vault_env_fallback(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MY_KEY", "from-env")
        assert SecretVault(tmp_path / "k", tmp_path / "s.enc").get("my_key") == "from-env"

    def test_vault_delete(self, tmp_path):
        vault = SecretVault(tmp_path / "key", tmp_path / "s.enc")
        vault.set("k", "v")
        vault.delete("k")
        assert vault.get("k") is None

    def test_permissions_by_role(self):
        pm = PermissionManager()
        pm.assign_role("alice", "administrator")
        pm.assign_role("bob", "guest")
        assert pm.check("alice", Permission.EXECUTE_TERMINAL)
        assert not pm.check("bob", Permission.READ_FILES)

    def test_admin_implies_everything(self):
        pm = PermissionManager()
        pm.assign_role("root", "administrator")
        assert pm.check("root", "some_future_permission")

    def test_grant_and_revoke(self):
        pm = PermissionManager()
        pm.assign_role("u", "user")
        assert not pm.check("u", Permission.EXECUTE_TERMINAL)
        pm.grant("u", Permission.EXECUTE_TERMINAL)
        assert pm.check("u", Permission.EXECUTE_TERMINAL)
        pm.revoke("u", Permission.EXECUTE_TERMINAL)
        assert not pm.check("u", Permission.EXECUTE_TERMINAL)

    def test_require_raises(self):
        pm = PermissionManager()
        pm.assign_role("g", "guest")
        with pytest.raises(PermissionDeniedError):
            pm.require("g", Permission.WRITE_FILES)

    def test_unknown_role_rejected(self):
        with pytest.raises(PermissionDeniedError):
            PermissionManager().assign_role("x", "wizard")

    def test_audit_log(self, tmp_path):
        log = AuditLog(file=tmp_path / "audit.log")
        log.record("login", principal="alice", outcome="allowed")
        entries = log.entries()
        assert len(entries) == 1 and entries[0]["principal"] == "alice"
        assert (tmp_path / "audit.log").exists()

    def test_audit_ring_buffer(self):
        log = AuditLog(capacity=5)
        for i in range(10):
            log.record(f"action-{i}")
        assert len(log.entries()) == 5

    def test_api_key_generation(self):
        key = generate_api_key()
        assert key.startswith("aera_") and len(key) > 20
        assert key != generate_api_key()


class TestErrors:
    def test_envelope(self):
        err = NotFoundError("missing thing", details={"id": "x"})
        payload = err.to_dict()
        assert payload["success"] is False
        assert payload["code"] == 404
        assert payload["details"] == {"id": "x"}

    def test_status_codes(self):
        assert PermissionDeniedError("x").status_code == 403
        assert ConfigError("x").status_code == 500
