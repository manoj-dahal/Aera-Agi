# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Plugin runtime: manifests, permissions and the approval lifecycle.

docs/17-PLUGIN-SYSTEM.md specified a full plugin system and none of it
existed. These cover what is now built -- discovery, validation and gating --
and pin the limitation that plugin code is not executed, so that stays an
explicit refusal rather than quietly becoming a silent no-op.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from aera.api.app import create_app
from aera.core.errors import ValidationError
from aera.services.plugins import (
    PERMISSIONS,
    PLUGIN_TYPES,
    PluginRegistry,
    PluginState,
    parse_manifest,
)

VALID = {
    "name": "Docker Assistant",
    "version": "1.0.0",
    "author": "AERA",
    "type": "automation",
    "permissions": ["workspace", "terminal"],
    "dependencies": ["core"],
    "minimumVersion": "1.0.0",
}


def write_plugin(root, folder: str, manifest: dict, *, as_json: bool = False):
    """Create a plugin directory with a manifest."""
    import yaml

    directory = root / folder
    directory.mkdir(parents=True, exist_ok=True)
    if as_json:
        (directory / "plugin.json").write_text(json.dumps(manifest))
    else:
        (directory / "manifest.yaml").write_text(yaml.safe_dump(manifest))
    return directory


@pytest.fixture
def registry(tmp_path):
    return PluginRegistry(tmp_path / "plugins")


class TestManifestValidation:
    def test_accepts_the_documented_example(self):
        """The manifest in docs/17 must parse as written."""
        manifest = parse_manifest(VALID)

        assert manifest.name == "Docker Assistant"
        assert manifest.permissions == ["workspace", "terminal"]

    def test_json_and_yaml_are_equivalent(self, registry):
        write_plugin(registry.root, "a", VALID)
        write_plugin(registry.root, "b", {**VALID, "name": "Other"}, as_json=True)

        plugins = registry.scan()

        assert len(plugins) == 2
        assert all(p.state is not PluginState.INVALID for p in plugins)

    @pytest.mark.parametrize(
        ("field", "value", "expected"),
        [
            ("name", "", "missing 'name'"),
            ("name", "!!bad!!", "invalid plugin name"),
            ("version", "", "missing 'version'"),
            ("version", "not-a-version", "not semantic"),
            ("type", "telepathy", "unknown plugin type"),
        ],
    )
    def test_rejections_name_the_problem(self, field, value, expected):
        """"Invalid manifest" tells an author nothing; be specific."""
        with pytest.raises(ValidationError, match=expected):
            parse_manifest({**VALID, field: value})

    def test_unknown_permissions_are_refused_with_the_valid_set(self):
        with pytest.raises(ValidationError) as excinfo:
            parse_manifest({**VALID, "permissions": ["mind_control"]})

        assert "mind_control" in str(excinfo.value)
        assert excinfo.value.details["supported"] == sorted(PERMISSIONS)

    def test_permissions_must_be_a_list(self):
        with pytest.raises(ValidationError, match="must be a list"):
            parse_manifest({**VALID, "permissions": "workspace"})

    def test_duplicate_permissions_are_collapsed(self):
        manifest = parse_manifest({**VALID, "permissions": ["files", "files", "workspace"]})

        assert manifest.permissions == ["files", "workspace"]

    def test_sensitive_permissions_are_identified(self):
        """The approval dialog needs to highlight the dangerous ones."""
        manifest = parse_manifest({**VALID, "permissions": ["workspace", "terminal", "camera"]})

        assert manifest.sensitive_permissions == ["camera", "terminal"]

    def test_every_documented_type_is_accepted(self):
        for plugin_type in PLUGIN_TYPES:
            assert parse_manifest({**VALID, "type": plugin_type}).type == plugin_type


class TestDiscovery:
    def test_finds_plugins(self, registry):
        write_plugin(registry.root, "docker-assistant", VALID)

        [plugin] = registry.scan()

        assert plugin.name == "Docker Assistant"

    def test_a_broken_plugin_is_listed_with_its_reason(self, registry):
        """Hiding it would leave the author with no idea what went wrong."""
        write_plugin(registry.root, "broken", {"name": "Bad", "version": "x"})

        [plugin] = registry.scan()

        assert plugin.state is PluginState.INVALID
        assert "not semantic" in plugin.error

    def test_one_broken_plugin_does_not_hide_the_others(self, registry):
        write_plugin(registry.root, "good", VALID)
        write_plugin(registry.root, "broken", {"name": "Bad", "version": "x"})

        plugins = registry.scan()

        assert len(plugins) == 2

    def test_a_directory_without_a_manifest_is_invalid(self, registry):
        (registry.root / "empty").mkdir(parents=True)

        [plugin] = registry.scan()

        assert "no manifest" in plugin.error

    def test_hidden_directories_are_skipped(self, registry):
        registry.root.mkdir(parents=True)
        (registry.root / ".git").mkdir()

        assert registry.scan() == []

    def test_a_plugin_wanting_nothing_needs_no_approval(self, registry):
        write_plugin(registry.root, "harmless", {**VALID, "permissions": []})

        [plugin] = registry.scan()

        assert plugin.state is PluginState.APPROVED


class TestApprovalLifecycle:
    @pytest.fixture
    def loaded(self, registry):
        write_plugin(registry.root, "docker-assistant", VALID)
        registry.scan()
        return registry

    def test_starts_pending_when_permissions_are_requested(self, loaded):
        assert loaded.get("docker-assistant").state is PluginState.PENDING_APPROVAL

    def test_cannot_enable_before_approval(self, loaded):
        with pytest.raises(ValidationError, match="must be approved"):
            loaded.enable("docker-assistant")

    def test_approving_everything_requested(self, loaded):
        plugin = loaded.approve("docker-assistant")

        assert plugin.granted == ["terminal", "workspace"]

    def test_a_user_may_approve_only_part(self, loaded):
        """Approving `workspace` while refusing `terminal` must be possible."""
        plugin = loaded.approve("docker-assistant", ["workspace"])

        assert plugin.granted == ["workspace"]

    def test_cannot_grant_what_was_never_requested(self, loaded):
        # Otherwise the dialog shows one thing and stores another.
        with pytest.raises(ValidationError, match="did not request"):
            loaded.approve("docker-assistant", ["workspace", "camera"])

    def test_permission_requires_both_grant_and_enabled(self, loaded):
        loaded.approve("docker-assistant", ["workspace"])

        # Approved but not enabled: the grant exists, the plugin must not act.
        assert loaded.has_permission("docker-assistant", "workspace") is False

        loaded.enable("docker-assistant")
        assert loaded.has_permission("docker-assistant", "workspace") is True
        assert loaded.has_permission("docker-assistant", "terminal") is False

    def test_disabling_stops_a_granted_permission_taking_effect(self, loaded):
        loaded.approve("docker-assistant")
        loaded.enable("docker-assistant")

        loaded.disable("docker-assistant")

        assert loaded.has_permission("docker-assistant", "workspace") is False

    def test_revoking_returns_it_to_pending(self, loaded):
        loaded.approve("docker-assistant")

        plugin = loaded.revoke("docker-assistant")

        assert plugin.granted == []
        assert plugin.state is PluginState.PENDING_APPROVAL

    def test_approvals_survive_a_rescan(self, loaded, tmp_path):
        """A restart must not silently re-prompt or silently re-grant."""
        loaded.approve("docker-assistant", ["workspace"])
        loaded.enable("docker-assistant")

        fresh = PluginRegistry(tmp_path / "plugins")
        fresh.scan()

        plugin = fresh.get("docker-assistant")
        assert plugin.granted == ["workspace"]
        assert plugin.state is PluginState.ENABLED

    def test_a_corrupt_approvals_file_grants_nothing(self, loaded, tmp_path):
        """Failing open here would silently re-enable a revoked plugin."""
        (tmp_path / "plugins" / ".approvals.json").write_text("{ broken")

        fresh = PluginRegistry(tmp_path / "plugins")
        fresh.scan()

        assert fresh.get("docker-assistant").state is PluginState.PENDING_APPROVAL

    def test_an_unknown_plugin_is_reported(self, loaded):
        with pytest.raises(ValidationError, match="no such plugin"):
            loaded.get("ghost")


class TestExecutionIsRefused:
    def test_no_plugin_claims_to_be_runnable(self, registry):
        write_plugin(registry.root, "p", VALID)

        [plugin] = registry.scan()

        assert plugin.runnable is False

    def test_the_reason_is_specific(self, registry):
        write_plugin(registry.root, "p", VALID)
        registry.scan()

        reason = registry.load_error("p")

        assert "does not execute plugin code" in reason

    def test_stats_admit_the_limitation(self, registry):
        assert registry.stats()["execution_supported"] is False


class TestPluginApi:
    @pytest.fixture
    def client(self, config, tmp_path):
        with TestClient(create_app(config)) as c:
            kernel = c.app.state.kernel
            kernel.plugins = PluginRegistry(tmp_path / "plugins")
            write_plugin(kernel.plugins.root, "docker-assistant", VALID)
            kernel.plugins.scan()
            yield c

    def test_lists_plugins(self, client):
        data = client.get("/api/v1/plugins").json()["data"]

        assert data["count"] == 1
        assert data["plugins"][0]["state"] == "pending_approval"

    def test_capabilities_are_discoverable(self, client):
        data = client.get("/api/v1/plugins/capabilities").json()["data"]

        assert set(data["permissions"]) == PERMISSIONS
        assert data["execution_supported"] is False

    def test_approve_then_enable(self, client):
        client.post(
            "/api/v1/plugins/docker-assistant/approve",
            json={"permissions": ["workspace"]},
        )

        response = client.post("/api/v1/plugins/docker-assistant/enable")

        assert response.json()["data"]["state"] == "enabled"

    def test_enable_before_approval_is_refused(self, client):
        response = client.post("/api/v1/plugins/docker-assistant/enable")

        assert response.status_code == 400
        assert "approved" in response.json()["error"]

    def test_over_granting_is_refused_over_http(self, client):
        response = client.post(
            "/api/v1/plugins/docker-assistant/approve",
            json={"permissions": ["workspace", "camera"]},
        )

        assert response.status_code == 400

    def test_loading_refuses_with_a_reason(self, client):
        response = client.post("/api/v1/plugins/docker-assistant/load")

        assert response.status_code == 400
        assert response.json()["details"]["execution_supported"] is False

    def test_filter_by_state(self, client):
        data = client.get("/api/v1/plugins?state=pending_approval").json()["data"]

        assert data["count"] == 1

    def test_unknown_plugin_is_reported(self, client):
        assert client.get("/api/v1/plugins/ghost").status_code == 400
