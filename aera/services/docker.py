# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Docker Engine API client (docs/27-DOCKER.md).

Talks to the Engine directly over its Unix socket rather than shelling out to
the ``docker`` CLI, so the output is structured JSON instead of text that has
to be scraped, and no CLI install is required -- only the daemon.

``httpx`` already supports Unix-socket transports, so this adds no dependency.

Every method raises :class:`DockerUnavailable` with a reason the user can act
on when the daemon cannot be reached. Nothing here invents data: if Docker is
not running, the caller is told so explicitly.

Read operations are unrestricted. State-changing ones (start, stop, restart,
remove) are gated behind :attr:`DockerClient.allow_control`, which follows the
same default-deny posture as the terminal agent.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

import httpx

from ..core.errors import AeraError
from ..core.logging import get_logger

logger = get_logger("services.docker")

#: Engine API version to negotiate. 1.41 ships with Docker 20.10 (2020), which
#: is old enough to be near-universal and new enough for everything used here.
API_VERSION = "v1.41"

#: Socket locations, in probe order. Docker Desktop on macOS and rootless
#: installs on Linux both put the socket under the user's home directory.
SOCKET_CANDIDATES = (
    "/var/run/docker.sock",
    "/run/docker.sock",
    "~/.docker/run/docker.sock",
    "~/.docker/desktop/docker.sock",
    "~/.colima/default/docker.sock",
)


class DockerUnavailable(AeraError):
    """The Docker daemon could not be reached."""

    status_code = 503
    code = "docker_unavailable"


class DockerControlDenied(AeraError):
    """A state-changing operation was attempted while control is disabled."""

    status_code = 403
    code = "docker_control_denied"


def find_socket(candidates: tuple[str, ...] = SOCKET_CANDIDATES) -> Path | None:
    """Return the first Docker socket that exists.

    ``DOCKER_HOST`` wins when it names a unix:// path, matching the CLI.
    """
    host = os.environ.get("DOCKER_HOST", "").strip()
    if host.startswith("unix://"):
        path = Path(host[len("unix://") :]).expanduser()
        return path if path.exists() else None
    if host:
        # tcp:// and ssh:// are real Docker setups but need TLS material and
        # an SSH agent respectively; say so rather than silently ignoring it.
        return None

    for candidate in candidates:
        path = Path(candidate).expanduser()
        if path.exists():
            return path
    return None


def _short_id(value: str) -> str:
    """Docker's own 12-character display form."""
    return value[:12]


def _container_name(names: list[str] | None) -> str:
    """Engine returns names with a leading slash; the UI wants them without."""
    if not names:
        return ""
    return names[0].lstrip("/")


class DockerClient:
    """Thin async client over the Engine API.

    Deliberately narrow: containers, images, volumes, networks and a version
    probe. Anything beyond that belongs to the CLI.
    """

    def __init__(
        self,
        *,
        socket: Path | None = None,
        allow_control: bool = False,
        timeout: float = 10.0,
    ) -> None:
        self.socket = socket if socket is not None else find_socket()
        self.allow_control = allow_control
        self.timeout = timeout

    # ------------------------------------------------------------------ #
    # availability
    # ------------------------------------------------------------------ #
    @property
    def available(self) -> bool:
        return self.socket is not None and Path(self.socket).exists()

    def unavailable_reason(self) -> str | None:
        """Why Docker cannot be used, phrased for a user, or None if it can."""
        host = os.environ.get("DOCKER_HOST", "").strip()
        if host and not host.startswith("unix://"):
            return (
                f"DOCKER_HOST is set to {host!r}; AERA talks to the Engine over a "
                "Unix socket only. Remote and TLS endpoints are not supported."
            )
        if self.available:
            return None
        if shutil.which("docker"):
            return (
                "the Docker CLI is installed but the daemon is not running "
                "(no socket at " + ", ".join(SOCKET_CANDIDATES[:2]) + ")"
            )
        return "Docker is not installed on this machine"

    def status(self) -> dict[str, Any]:
        """A snapshot safe to render before any request is made."""
        return {
            "available": self.available,
            "socket": str(self.socket) if self.socket else None,
            "reason": self.unavailable_reason(),
            "control_enabled": self.allow_control,
            "api_version": API_VERSION,
        }

    # ------------------------------------------------------------------ #
    # transport
    # ------------------------------------------------------------------ #
    def _client(self) -> httpx.AsyncClient:
        if not self.available:
            raise DockerUnavailable(self.unavailable_reason() or "Docker is unavailable")
        transport = httpx.AsyncHTTPTransport(uds=str(self.socket))
        # The host in the URL is ignored for a UDS transport but must parse.
        return httpx.AsyncClient(
            transport=transport, base_url="http://docker", timeout=self.timeout
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"/{API_VERSION}{path}"
        try:
            async with self._client() as client:
                response = await client.request(method, url, **kwargs)
        except DockerUnavailable:
            raise
        except (httpx.ConnectError, httpx.ReadTimeout, OSError) as exc:
            raise DockerUnavailable(f"could not reach the Docker daemon: {exc}") from exc

        if response.status_code >= 400:
            # The Engine returns {"message": "..."} for errors.
            detail = response.text.strip()
            try:
                detail = response.json().get("message", detail)
            except ValueError:
                pass
            raise DockerUnavailable(f"Docker API error {response.status_code}: {detail}")

        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text

    def _require_control(self, action: str) -> None:
        if not self.allow_control:
            raise DockerControlDenied(
                f"{action} is disabled. Enable Docker control in Settings to allow "
                "AERA to change container state."
            )

    # ------------------------------------------------------------------ #
    # reads
    # ------------------------------------------------------------------ #
    async def version(self) -> dict[str, Any]:
        data = await self._request("GET", "/version")
        return {
            "version": data.get("Version"),
            "api_version": data.get("ApiVersion"),
            "os": data.get("Os"),
            "arch": data.get("Arch"),
            "kernel": data.get("KernelVersion"),
        }

    async def info(self) -> dict[str, Any]:
        data = await self._request("GET", "/info")
        return {
            "name": data.get("Name"),
            "containers": data.get("Containers"),
            "containers_running": data.get("ContainersRunning"),
            "containers_paused": data.get("ContainersPaused"),
            "containers_stopped": data.get("ContainersStopped"),
            "images": data.get("Images"),
            "server_version": data.get("ServerVersion"),
            "driver": data.get("Driver"),
            "memory_total": data.get("MemTotal"),
            "cpus": data.get("NCPU"),
        }

    async def containers(self, *, all_containers: bool = True) -> list[dict[str, Any]]:
        params = {"all": "true" if all_containers else "false"}
        data = await self._request("GET", "/containers/json", params=params)
        return [
            {
                "id": _short_id(c.get("Id", "")),
                "name": _container_name(c.get("Names")),
                "image": c.get("Image"),
                "state": c.get("State"),
                "status": c.get("Status"),
                "created": c.get("Created"),
                "ports": [
                    {
                        "private": p.get("PrivatePort"),
                        "public": p.get("PublicPort"),
                        "type": p.get("Type"),
                    }
                    for p in c.get("Ports") or []
                ],
            }
            for c in data or []
        ]

    async def images(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/images/json")
        return [
            {
                "id": _short_id((i.get("Id") or "").removeprefix("sha256:")),
                # An image with no tags is <none>:<none> in the CLI too.
                "tags": i.get("RepoTags") or [],
                "size": i.get("Size"),
                "created": i.get("Created"),
            }
            for i in data or []
        ]

    async def volumes(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/volumes")
        return [
            {
                "name": v.get("Name"),
                "driver": v.get("Driver"),
                "mountpoint": v.get("Mountpoint"),
                "created": v.get("CreatedAt"),
            }
            for v in (data or {}).get("Volumes") or []
        ]

    async def networks(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/networks")
        return [
            {
                "id": _short_id(n.get("Id", "")),
                "name": n.get("Name"),
                "driver": n.get("Driver"),
                "scope": n.get("Scope"),
            }
            for n in data or []
        ]

    async def logs(self, container: str, *, tail: int = 200) -> str:
        """Recent log output for one container.

        Without a TTY the Engine multiplexes stdout and stderr into a framed
        stream: each frame is an 8-byte header followed by the payload. The
        headers are stripped here so callers get readable text.
        """
        params = {"stdout": "true", "stderr": "true", "tail": str(max(1, tail))}
        raw = await self._request(
            "GET", f"/containers/{container}/logs", params=params
        )
        if isinstance(raw, str):
            return _demultiplex(raw.encode("utf-8", "replace"))
        return ""

    async def stats(self, container: str) -> dict[str, Any]:
        """A single stats sample (``stream=false``), reduced to percentages."""
        data = await self._request(
            "GET", f"/containers/{container}/stats", params={"stream": "false"}
        )
        return _reduce_stats(data or {})

    # ------------------------------------------------------------------ #
    # state changes
    # ------------------------------------------------------------------ #
    async def start(self, container: str) -> dict[str, Any]:
        self._require_control("starting a container")
        await self._request("POST", f"/containers/{container}/start")
        logger.info("docker: started %s", container)
        return {"container": container, "action": "start"}

    async def stop(self, container: str, *, timeout: int = 10) -> dict[str, Any]:
        self._require_control("stopping a container")
        await self._request(
            "POST", f"/containers/{container}/stop", params={"t": str(timeout)}
        )
        logger.info("docker: stopped %s", container)
        return {"container": container, "action": "stop"}

    async def restart(self, container: str, *, timeout: int = 10) -> dict[str, Any]:
        self._require_control("restarting a container")
        await self._request(
            "POST", f"/containers/{container}/restart", params={"t": str(timeout)}
        )
        logger.info("docker: restarted %s", container)
        return {"container": container, "action": "restart"}

    async def remove(self, container: str, *, force: bool = False) -> dict[str, Any]:
        self._require_control("removing a container")
        await self._request(
            "DELETE",
            f"/containers/{container}",
            params={"force": "true" if force else "false"},
        )
        logger.info("docker: removed %s", container)
        return {"container": container, "action": "remove"}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _demultiplex(raw: bytes) -> str:
    """Strip Docker's 8-byte stream frame headers.

    Frame layout: [stream_type, 0, 0, 0, len(4, big-endian)] then the payload.
    Logs from a TTY container are not framed, so fall back to plain decoding
    when the bytes do not look like frames.
    """
    out: list[str] = []
    index = 0
    total = len(raw)
    while index + 8 <= total:
        stream_type = raw[index]
        if stream_type not in (0, 1, 2):
            # Not a frame header: treat the remainder as plain text.
            return raw.decode("utf-8", "replace")
        length = int.from_bytes(raw[index + 4 : index + 8], "big")
        start = index + 8
        end = start + length
        if end > total:
            break
        out.append(raw[start:end].decode("utf-8", "replace"))
        index = end
    if not out:
        return raw.decode("utf-8", "replace")
    return "".join(out)


def _reduce_stats(data: dict[str, Any]) -> dict[str, Any]:
    """Turn a raw stats frame into CPU/memory percentages.

    Docker reports cumulative CPU counters, so a percentage needs the delta
    against the previous sample, which the Engine includes in the same frame.
    """
    cpu_percent: float | None = None
    try:
        cpu = data["cpu_stats"]
        pre = data["precpu_stats"]
        cpu_delta = cpu["cpu_usage"]["total_usage"] - pre["cpu_usage"]["total_usage"]
        system_delta = cpu.get("system_cpu_usage", 0) - pre.get("system_cpu_usage", 0)
        if system_delta > 0 and cpu_delta >= 0:
            cores = cpu.get("online_cpus") or len(
                cpu["cpu_usage"].get("percpu_usage") or []
            ) or 1
            cpu_percent = round((cpu_delta / system_delta) * cores * 100.0, 2)
    except (KeyError, TypeError, ZeroDivisionError):
        cpu_percent = None

    memory = data.get("memory_stats") or {}
    usage = memory.get("usage")
    limit = memory.get("limit")
    # The Engine counts page cache in usage; the CLI subtracts it.
    cache = (memory.get("stats") or {}).get("cache", 0)
    if isinstance(usage, int) and isinstance(cache, int):
        usage = max(0, usage - cache)

    memory_percent = None
    if isinstance(usage, int) and isinstance(limit, int) and limit > 0:
        memory_percent = round(usage / limit * 100.0, 2)

    return {
        "cpu_percent": cpu_percent,
        "memory_usage": usage,
        "memory_limit": limit,
        "memory_percent": memory_percent,
    }
