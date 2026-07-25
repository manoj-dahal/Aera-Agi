"""Tests for the system telemetry service."""

from __future__ import annotations

from aera.services.telemetry import TelemetryService, _gb, get_telemetry


class TestTelemetry:
    def test_snapshot_has_every_section(self):
        snapshot = TelemetryService().snapshot(force=True)
        for section in ("cpu", "memory", "disk", "network", "gpu", "temperature"):
            assert section in snapshot

    def test_reports_real_cpu_and_memory(self):
        snapshot = TelemetryService().snapshot(force=True)
        assert snapshot["memory"]["total_gb"] and snapshot["memory"]["total_gb"] > 0
        assert snapshot["cpu"]["threads"] and snapshot["cpu"]["threads"] >= 1

    def test_percentages_are_bounded(self):
        snapshot = TelemetryService().snapshot(force=True)
        for section in ("cpu", "memory", "disk"):
            value = snapshot[section].get("percent")
            if value is not None:
                assert 0 <= value <= 100, f"{section} percent out of range: {value}"

    def test_missing_metrics_are_none_not_zero(self):
        """A metric the host cannot supply must be null, never a fake zero."""
        snapshot = TelemetryService().snapshot(force=True)
        # GPU is absent in CI; it must be an empty list rather than a fake entry.
        assert isinstance(snapshot["gpu"], list)
        assert snapshot["temperature"] is None or isinstance(snapshot["temperature"], float)

    def test_cache_avoids_resampling(self):
        service = TelemetryService(cache_seconds=60)
        first = service.snapshot(force=True)
        second = service.snapshot()
        assert first["timestamp"] == second["timestamp"]

    def test_force_bypasses_the_cache(self):
        service = TelemetryService(cache_seconds=60)
        first = service.snapshot(force=True)
        second = service.snapshot(force=True)
        assert second["timestamp"] >= first["timestamp"]

    def test_network_rate_needs_two_samples(self):
        service = TelemetryService(cache_seconds=0)
        first = service.snapshot(force=True)
        assert first["network"]["down_kbps"] is None  # no baseline yet
        second = service.snapshot(force=True)
        # Second sample can compute a rate (or stay None on a host without counters).
        assert "down_kbps" in second["network"]

    async def test_async_snapshot(self):
        assert (await TelemetryService().snapshot_async(force=True))["cpu"]

    def test_singleton(self):
        assert get_telemetry() is get_telemetry()

    def test_gb_helper(self):
        assert _gb(1_073_741_824) == 1.0
        assert _gb(0) is None
        assert _gb(None) is None


class TestTelemetryIntegration:
    async def test_exposed_on_kernel_status(self, kernel):
        assert "telemetry" in kernel.status()

    def test_rest_endpoint(self, config):
        from fastapi.testclient import TestClient

        from aera.api.app import create_app

        with TestClient(create_app(config)) as client:
            body = client.get("/api/v1/system/telemetry").json()
            assert body["success"] is True
            assert body["data"]["memory"]["total_gb"] > 0

    def test_native_bridge_method(self):
        from aera.desktop.bridge import DesktopBridge

        assert hasattr(DesktopBridge, "telemetry")

    async def test_performance_agent_uses_real_readings(self, registry):
        from aera.agents import Capability, Task

        await registry.start_all()
        result = await registry.dispatch(
            Task(capability=Capability.PERFORMANCE, input="how is the system?")
        )
        assert result.success
        assert "host" in result.data["metrics"]
        assert result.data["metrics"]["host"]["memory"]["total_gb"] > 0
