"""Tests for the Docker Engine connector.

The client is exercised against a fake Engine served on a real Unix socket,
so the transport itself is covered rather than mocked away. Docker is not
installed in CI, which is exactly the condition the availability probe has to
report honestly.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from aera.services.docker import (
    DockerClient,
    DockerControlDenied,
    DockerUnavailable,
    _demultiplex,
    _reduce_stats,
    find_socket,
)

CONTAINER = {
    "Id": "abc123def4567890abcdef",
    "Names": ["/aera-ci"],
    "Image": "aera:ci",
    "State": "running",
    "Status": "Up 2 minutes",
    "Created": 1_700_000_000,
    "Ports": [{"PrivatePort": 8080, "PublicPort": 8080, "Type": "tcp"}],
}

ROUTES: dict[str, object] = {
    "/v1.41/version": {
        "Version": "24.0.7",
        "ApiVersion": "1.43",
        "Os": "linux",
        "Arch": "amd64",
        "KernelVersion": "6.1.0",
    },
    "/v1.41/info": {
        "Name": "builder",
        "Containers": 3,
        "ContainersRunning": 1,
        "ContainersPaused": 0,
        "ContainersStopped": 2,
        "Images": 7,
        "ServerVersion": "24.0.7",
        "Driver": "overlay2",
        "MemTotal": 8_000_000_000,
        "NCPU": 4,
    },
    "/v1.41/containers/json": [CONTAINER],
    "/v1.41/images/json": [
        {
            "Id": "sha256:ffee1234567890abcdef",
            "RepoTags": ["aera:ci"],
            "Size": 123_456_789,
            "Created": 1_700_000_000,
        },
        # An untagged image: RepoTags comes back null, not [].
        {"Id": "sha256:0011223344556677", "RepoTags": None, "Size": 10, "Created": 1},
    ],
    "/v1.41/volumes": {"Volumes": [{"Name": "aera-data", "Driver": "local", "Mountpoint": "/v", "CreatedAt": "now"}]},
    "/v1.41/networks": [{"Id": "netid1234567890", "Name": "bridge", "Driver": "bridge", "Scope": "local"}],
    "/v1.41/containers/aera-ci/start": None,
    "/v1.41/containers/aera-ci/stop": None,
    "/v1.41/containers/aera-ci/restart": None,
    "/v1.41/containers/aera-ci": None,
}


class FakeEngine:
    """A minimal Docker Engine over a Unix socket."""

    def __init__(self, socket: Path) -> None:
        self.socket = socket
        self.requests: list[tuple[str, str]] = []
        self._server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_unix_server(self._handle, path=str(self.socket))

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        request = await reader.read(65_536)
        method, target, _ = request.split(b"\r\n")[0].decode().split(" ")
        path = target.split("?")[0]
        self.requests.append((method, target))

        if path == "/v1.41/containers/aera-ci/logs":
            # Two framed messages: stdout then stderr.
            payload = _frame(1, b"hello\n") + _frame(2, b"warning\n")
            self._write(writer, 200, payload, "application/octet-stream")
        elif path == "/v1.41/containers/aera-ci/stats":
            self._write(writer, 200, json.dumps(STATS).encode())
        elif path in ROUTES:
            body = ROUTES[path]
            self._write(writer, 200, b"" if body is None else json.dumps(body).encode())
        else:
            self._write(writer, 404, json.dumps({"message": "no such container"}).encode())
        writer.close()

    @staticmethod
    def _write(writer, code: int, body: bytes, content_type: str = "application/json") -> None:
        head = (
            f"HTTP/1.1 {code} OK\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(body)}\r\n\r\n"
        )
        writer.write(head.encode() + body)


STATS = {
    "cpu_stats": {
        "cpu_usage": {"total_usage": 2_000_000},
        "system_cpu_usage": 20_000_000,
        "online_cpus": 2,
    },
    "precpu_stats": {"cpu_usage": {"total_usage": 1_000_000}, "system_cpu_usage": 10_000_000},
    "memory_stats": {"usage": 300, "limit": 1000, "stats": {"cache": 100}},
}


def _frame(stream: int, payload: bytes) -> bytes:
    return bytes([stream, 0, 0, 0]) + len(payload).to_bytes(4, "big") + payload


@pytest.fixture
async def engine(tmp_path):
    # Unix sockets have a ~104 character path limit; tmp_path is short enough.
    server = FakeEngine(tmp_path / "docker.sock")
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
def client(engine):
    return DockerClient(socket=engine.socket, allow_control=True)


class TestAvailability:
    def test_reports_unavailable_without_a_socket(self, tmp_path):
        client = DockerClient(socket=tmp_path / "absent.sock")
        assert client.available is False
        assert client.unavailable_reason()

    def test_reason_is_actionable(self, tmp_path, monkeypatch):
        monkeypatch.delenv("DOCKER_HOST", raising=False)
        monkeypatch.setattr("aera.services.docker.shutil.which", lambda _: None)
        client = DockerClient(socket=tmp_path / "absent.sock")
        assert "not installed" in client.unavailable_reason()

    def test_distinguishes_installed_but_stopped(self, tmp_path, monkeypatch):
        """A stopped daemon and a missing install need different fixes."""
        monkeypatch.delenv("DOCKER_HOST", raising=False)
        monkeypatch.setattr("aera.services.docker.shutil.which", lambda _: "/usr/bin/docker")
        client = DockerClient(socket=tmp_path / "absent.sock")
        assert "not running" in client.unavailable_reason()

    def test_rejects_remote_docker_host(self, monkeypatch):
        """tcp:// needs TLS material; say so instead of failing obscurely."""
        monkeypatch.setenv("DOCKER_HOST", "tcp://10.0.0.5:2376")
        client = DockerClient()
        assert client.available is False
        assert "Unix socket only" in client.unavailable_reason()

    def test_honours_a_unix_docker_host(self, tmp_path, monkeypatch):
        socket = tmp_path / "custom.sock"
        socket.touch()
        monkeypatch.setenv("DOCKER_HOST", f"unix://{socket}")
        assert find_socket() == socket

    def test_status_never_raises_when_unavailable(self, tmp_path):
        """The UI calls status() first; it must describe, not explode."""
        status = DockerClient(socket=tmp_path / "absent.sock").status()
        assert status["available"] is False
        assert status["reason"]

    async def test_requests_fail_clearly_when_unavailable(self, tmp_path):
        client = DockerClient(socket=tmp_path / "absent.sock")
        with pytest.raises(DockerUnavailable):
            await client.containers()


class TestReads:
    async def test_version(self, client):
        assert (await client.version())["version"] == "24.0.7"

    async def test_info_summarises_the_daemon(self, client):
        info = await client.info()
        assert info["containers_running"] == 1
        assert info["cpus"] == 4

    async def test_containers_are_normalised(self, client):
        [container] = await client.containers()
        # Docker's display form is the 12-character short id.
        assert container["id"] == "abc123def456"
        # Names arrive with a leading slash.
        assert container["name"] == "aera-ci"
        assert container["ports"] == [{"private": 8080, "public": 8080, "type": "tcp"}]

    async def test_images_handle_missing_tags(self, client):
        """RepoTags is null for untagged images, not an empty list."""
        images = await client.images()
        assert images[0]["id"] == "ffee12345678"
        assert images[1]["tags"] == []

    async def test_volumes_and_networks(self, client):
        assert (await client.volumes())[0]["name"] == "aera-data"
        assert (await client.networks())[0]["name"] == "bridge"

    async def test_logs_are_demultiplexed(self, client):
        """Without a TTY the Engine frames stdout and stderr together."""
        logs = await client.logs("aera-ci")
        assert logs == "hello\nwarning\n"

    async def test_logs_tail_is_passed_through(self, client, engine):
        await client.logs("aera-ci", tail=42)
        assert any("tail=42" in target for _, target in engine.requests)

    async def test_stats_are_reduced_to_percentages(self, client):
        stats = await client.stats("aera-ci")
        # 1e6 delta over 1e7 system delta, 2 cores => 20%.
        assert stats["cpu_percent"] == 20.0
        # Page cache is excluded, matching the CLI: (300-100)/1000.
        assert stats["memory_percent"] == 20.0

    async def test_unknown_container_reports_the_engine_message(self, client):
        with pytest.raises(DockerUnavailable) as excinfo:
            await client.logs("ghost")
        assert "no such container" in str(excinfo.value)


class TestControlGate:
    @pytest.mark.parametrize("action", ["start", "stop", "restart", "remove"])
    async def test_state_changes_are_denied_by_default(self, engine, action):
        client = DockerClient(socket=engine.socket)  # allow_control defaults off
        with pytest.raises(DockerControlDenied):
            await getattr(client, action)("aera-ci")

    @pytest.mark.parametrize("action", ["start", "stop", "restart"])
    async def test_state_changes_work_when_enabled(self, client, action):
        assert (await getattr(client, action)("aera-ci"))["action"] == action

    async def test_reads_are_never_gated(self, engine):
        """Inspecting containers is safe, so it must work with control off."""
        client = DockerClient(socket=engine.socket)
        assert await client.containers()

    async def test_denial_names_the_setting_to_change(self, engine):
        client = DockerClient(socket=engine.socket)
        with pytest.raises(DockerControlDenied) as excinfo:
            await client.stop("aera-ci")
        assert "Settings" in str(excinfo.value)

    async def test_stop_sends_a_timeout(self, client, engine):
        await client.stop("aera-ci", timeout=3)
        assert any("t=3" in target for _, target in engine.requests)

    async def test_remove_uses_delete(self, client, engine):
        await client.remove("aera-ci")
        assert any(method == "DELETE" for method, _ in engine.requests)


class TestHelpers:
    def test_demultiplex_strips_frame_headers(self):
        assert _demultiplex(_frame(1, b"out") + _frame(2, b"err")) == "outerr"

    def test_demultiplex_passes_through_tty_output(self):
        """TTY containers emit unframed text; it must not be mangled."""
        assert _demultiplex(b"plain log line\n") == "plain log line\n"

    def test_demultiplex_tolerates_a_truncated_frame(self):
        # A partial trailing frame should not lose the complete one before it.
        assert _demultiplex(_frame(1, b"kept") + b"\x01\x00\x00") == "kept"

    def test_reduce_stats_handles_a_missing_sample(self):
        """Docker omits precpu on the first frame; report None, not zero."""
        assert _reduce_stats({})["cpu_percent"] is None

    def test_reduce_stats_survives_a_zero_system_delta(self):
        stats = _reduce_stats(
            {
                "cpu_stats": {"cpu_usage": {"total_usage": 5}, "system_cpu_usage": 10},
                "precpu_stats": {"cpu_usage": {"total_usage": 5}, "system_cpu_usage": 10},
                "memory_stats": {},
            }
        )
        assert stats["cpu_percent"] is None
        assert stats["memory_percent"] is None
