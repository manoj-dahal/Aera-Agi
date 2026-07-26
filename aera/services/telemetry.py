# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""System telemetry for the PC Information panel (docs/04-DASHBOARD.md).

Reports CPU, GPU, RAM, VRAM, disk, network and temperature. Uses ``psutil``
when it is installed and falls back to reading ``/proc`` and shelling out to
``nvidia-smi``. Every field is optional: a metric the host cannot supply is
reported as ``None`` rather than invented.
"""

from __future__ import annotations

import asyncio
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from ..core.logging import get_logger

logger = get_logger("services.telemetry")

try:  # pragma: no cover - availability differs per host
    import psutil

    HAVE_PSUTIL = True
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore[assignment]
    HAVE_PSUTIL = False


class TelemetryService:
    """Samples host metrics on demand, with a short cache.

    The dashboard polls this a few times a minute; sampling is cheap but not
    free, so results are cached briefly to keep the UI responsive.
    """

    def __init__(self, *, cache_seconds: float = 1.5) -> None:
        self.cache_seconds = cache_seconds
        self._cached: dict[str, Any] | None = None
        self._sampled_at = 0.0
        self._last_net: tuple[float, int, int] | None = None
        # psutil's first cpu_percent() call always returns 0.0; prime it.
        if HAVE_PSUTIL:
            try:
                psutil.cpu_percent(interval=None)
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def snapshot(self, *, force: bool = False) -> dict[str, Any]:
        """Return the current metrics, using the cache when it is fresh."""
        now = time.time()
        if not force and self._cached and (now - self._sampled_at) < self.cache_seconds:
            return self._cached

        data: dict[str, Any] = {
            "timestamp": now,
            "host": platform.node(),
            "platform": f"{platform.system()} {platform.release()}",
            "cpu": self._cpu(),
            "memory": self._memory(),
            "disk": self._disk(),
            "network": self._network(now),
            "gpu": self._gpu(),
            "temperature": self._temperature(),
            "source": "psutil" if HAVE_PSUTIL else "procfs",
        }
        self._cached = data
        self._sampled_at = now
        return data

    async def snapshot_async(self, *, force: bool = False) -> dict[str, Any]:
        """Sample off the event loop so a slow nvidia-smi cannot block it."""
        return await asyncio.to_thread(self.snapshot, force=force)

    # ------------------------------------------------------------------ #
    # CPU
    # ------------------------------------------------------------------ #
    def _cpu(self) -> dict[str, Any]:
        info: dict[str, Any] = {
            "percent": None,
            "cores": None,
            "threads": None,
            "frequency_mhz": None,
            "load_average": None,
            "model": platform.processor() or None,
        }

        if HAVE_PSUTIL:
            try:
                info["percent"] = round(psutil.cpu_percent(interval=None), 1)
                info["cores"] = psutil.cpu_count(logical=False)
                info["threads"] = psutil.cpu_count(logical=True)
                freq = psutil.cpu_freq()
                if freq:
                    info["frequency_mhz"] = round(freq.current)
            except Exception:  # noqa: BLE001
                logger.debug("psutil cpu sampling failed", exc_info=True)
        else:
            info["threads"] = _cpu_count_procfs()
            info["percent"] = _cpu_percent_procfs()

        try:
            import os

            load = os.getloadavg()
            info["load_average"] = [round(v, 2) for v in load]
            # Approximate utilisation from load when no direct reading exists.
            if info["percent"] is None and info["threads"]:
                info["percent"] = round(min(100.0, load[0] / info["threads"] * 100), 1)
        except (OSError, AttributeError):
            pass

        return info

    # ------------------------------------------------------------------ #
    # memory
    # ------------------------------------------------------------------ #
    def _memory(self) -> dict[str, Any]:
        if HAVE_PSUTIL:
            try:
                vm = psutil.virtual_memory()
                swap = psutil.swap_memory()
                return {
                    "total_gb": _gb(vm.total),
                    "used_gb": _gb(vm.used),
                    "available_gb": _gb(vm.available),
                    "percent": round(vm.percent, 1),
                    "swap_total_gb": _gb(swap.total),
                    "swap_used_gb": _gb(swap.used),
                }
            except Exception:  # noqa: BLE001
                logger.debug("psutil memory sampling failed", exc_info=True)

        return _memory_procfs()

    # ------------------------------------------------------------------ #
    # disk
    # ------------------------------------------------------------------ #
    def _disk(self) -> dict[str, Any]:
        try:
            usage = shutil.disk_usage(Path.home())
            return {
                "total_gb": _gb(usage.total),
                "used_gb": _gb(usage.used),
                "free_gb": _gb(usage.free),
                "percent": round(usage.used / usage.total * 100, 1) if usage.total else None,
            }
        except OSError:
            return {"total_gb": None, "used_gb": None, "free_gb": None, "percent": None}

    # ------------------------------------------------------------------ #
    # network
    # ------------------------------------------------------------------ #
    def _network(self, now: float) -> dict[str, Any]:
        """Byte counters converted to a rate using the previous sample."""
        sent = received = None
        if HAVE_PSUTIL:
            try:
                counters = psutil.net_io_counters()
                sent, received = counters.bytes_sent, counters.bytes_recv
            except Exception:  # noqa: BLE001
                pass
        else:
            sent, received = _network_procfs()

        result: dict[str, Any] = {
            "bytes_sent": sent,
            "bytes_received": received,
            "up_kbps": None,
            "down_kbps": None,
        }

        if sent is not None and received is not None:
            if self._last_net:
                prev_t, prev_sent, prev_recv = self._last_net
                elapsed = now - prev_t
                if elapsed > 0.2:
                    result["up_kbps"] = round((sent - prev_sent) / elapsed / 1024, 1)
                    result["down_kbps"] = round((received - prev_recv) / elapsed / 1024, 1)
            self._last_net = (now, sent, received)

        return result

    # ------------------------------------------------------------------ #
    # GPU
    # ------------------------------------------------------------------ #
    def _gpu(self) -> list[dict[str, Any]]:
        """Query NVIDIA GPUs. Returns an empty list when none are present."""
        if not shutil.which("nvidia-smi"):
            return []
        try:
            output = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=3,
                check=True,
            ).stdout
        except (subprocess.SubprocessError, OSError):
            return []

        gpus: list[dict[str, Any]] = []
        for line in output.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5:
                continue
            gpus.append(
                {
                    "name": parts[0],
                    "utilization": _as_float(parts[1]),
                    "vram_used_mb": _as_float(parts[2]),
                    "vram_total_mb": _as_float(parts[3]),
                    "temperature_c": _as_float(parts[4]),
                }
            )
        return gpus

    # ------------------------------------------------------------------ #
    # temperature
    # ------------------------------------------------------------------ #
    def _temperature(self) -> float | None:
        if HAVE_PSUTIL and hasattr(psutil, "sensors_temperatures"):
            try:
                sensors = psutil.sensors_temperatures()
                for key in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
                    readings = sensors.get(key)
                    if readings:
                        return round(readings[0].current, 1)
                for readings in sensors.values():
                    if readings:
                        return round(readings[0].current, 1)
            except Exception:  # noqa: BLE001
                pass

        # Linux thermal zone fallback (millidegrees).
        zone = Path("/sys/class/thermal/thermal_zone0/temp")
        try:
            return round(int(zone.read_text().strip()) / 1000, 1)
        except (OSError, ValueError):
            return None


# --------------------------------------------------------------------------- #
# procfs fallbacks
# --------------------------------------------------------------------------- #
def _cpu_count_procfs() -> int | None:
    try:
        return sum(
            1 for line in Path("/proc/cpuinfo").read_text().splitlines()
            if line.startswith("processor")
        ) or None
    except OSError:
        return None


def _cpu_percent_procfs() -> float | None:
    """Two /proc/stat samples 100 ms apart."""
    def read() -> tuple[int, int] | None:
        try:
            fields = Path("/proc/stat").read_text().split("\n")[0].split()[1:]
        except (OSError, IndexError):
            return None
        values = [int(v) for v in fields[:8]]
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        return sum(values), idle

    first = read()
    if first is None:
        return None
    time.sleep(0.1)
    second = read()
    if second is None:
        return None

    total_delta = second[0] - first[0]
    idle_delta = second[1] - first[1]
    if total_delta <= 0:
        return None
    return round((1 - idle_delta / total_delta) * 100, 1)


def _memory_procfs() -> dict[str, Any]:
    try:
        lines = Path("/proc/meminfo").read_text().splitlines()
    except OSError:
        return {"total_gb": None, "used_gb": None, "available_gb": None, "percent": None}

    values: dict[str, int] = {}
    for line in lines:
        parts = line.split(":")
        if len(parts) == 2:
            digits = parts[1].strip().split()[0]
            if digits.isdigit():
                values[parts[0]] = int(digits) * 1024  # kB -> bytes

    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", values.get("MemFree", 0))
    used = total - available
    return {
        "total_gb": _gb(total),
        "used_gb": _gb(used),
        "available_gb": _gb(available),
        "percent": round(used / total * 100, 1) if total else None,
        "swap_total_gb": _gb(values.get("SwapTotal", 0)),
        "swap_used_gb": _gb(values.get("SwapTotal", 0) - values.get("SwapFree", 0)),
    }


def _network_procfs() -> tuple[int | None, int | None]:
    try:
        lines = Path("/proc/net/dev").read_text().splitlines()[2:]
    except OSError:
        return None, None

    sent = received = 0
    for line in lines:
        name, _, rest = line.partition(":")
        if name.strip() == "lo":
            continue
        fields = rest.split()
        if len(fields) >= 9:
            received += int(fields[0])
            sent += int(fields[8])
    return sent, received


def _gb(value: int | float | None) -> float | None:
    return round(value / 1_073_741_824, 2) if value else None


def _as_float(text: str) -> float | None:
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


_service: TelemetryService | None = None


def get_telemetry() -> TelemetryService:
    """Process-wide telemetry service."""
    global _service
    if _service is None:
        _service = TelemetryService()
    return _service
