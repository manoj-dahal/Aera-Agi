"""Native JavaScript bridge.

Exposes desktop-only capabilities to the UI layer. Everything here runs in the
application process, so the UI calls native folder pickers, the clipboard and
the local kernel directly - no HTTP round trip, no browser sandbox.

Methods on :class:`DesktopBridge` are reachable from JavaScript as
``window.pywebview.api.<method>()``.
"""

from __future__ import annotations

import asyncio
import json
import platform
import subprocess
import threading
from pathlib import Path
from typing import Any

from ..core.logging import get_logger

logger = get_logger("desktop.bridge")


class DesktopBridge:
    """Native API surface handed to the embedded UI."""

    def __init__(self, app) -> None:
        self.app = app  # DesktopApp - avoids a circular import
        self._window = None

    def attach(self, window) -> None:
        self._window = window

    # ------------------------------------------------------------------ #
    # async plumbing
    # ------------------------------------------------------------------ #
    def _run(self, coro) -> Any:
        """Run a coroutine on the kernel's event loop from the UI thread."""
        loop = self.app.loop
        if loop is None or not loop.is_running():
            raise RuntimeError("AERA kernel is not running")
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=180)

    @staticmethod
    def _ok(data: Any = None, message: str = "Completed") -> dict:
        return {"success": True, "message": message, "data": data}

    @staticmethod
    def _err(error: str) -> dict:
        return {"success": False, "error": error}

    # ------------------------------------------------------------------ #
    # conversation
    # ------------------------------------------------------------------ #
    def chat(self, message: str, conversation_id: str | None = None) -> dict:
        """Send a message through the Core Agent pipeline."""
        try:
            kernel = self.app.kernel
            cid = conversation_id or "desktop"
            result = self._run(kernel.chat(message, conversation_id=cid))
            return self._ok({**result.to_public(), "conversation_id": cid})
        except Exception as exc:  # noqa: BLE001 - surface errors to the UI
            logger.exception("chat failed")
            return self._err(str(exc))

    def chat_stream(self, message: str, conversation_id: str | None = None) -> dict:
        """Stream a reply, pushing tokens into the UI as they arrive.

        Runs on a worker thread and calls back into JavaScript via
        ``window.aeraOnToken`` / ``window.aeraOnDone``.
        """
        cid = conversation_id or "desktop"

        def worker() -> None:
            try:
                kernel = self.app.kernel

                async def pump() -> str:
                    context = ""
                    if kernel.memory is not None:
                        context = await kernel.memory.build_context(
                            message, conversation_id=cid
                        )
                    system = (
                        "You are AERA, a desktop AI operating system with persistent "
                        "memory. Be direct and technically precise."
                    )
                    if context:
                        system += f"\n\n{context}"

                    pieces: list[str] = []
                    async for token in kernel.router.stream(message, system=system):
                        pieces.append(token)
                        self._emit("aeraOnToken", {"content": token})
                    full = "".join(pieces)
                    if kernel.memory is not None and full:
                        await kernel.memory.remember_exchange(
                            message, full, conversation_id=cid
                        )
                    return full

                full = self._run(pump())
                self._emit("aeraOnDone", {"content": full, "conversation_id": cid})
            except Exception as exc:  # noqa: BLE001
                logger.exception("stream failed")
                self._emit("aeraOnError", {"error": str(exc)})

        threading.Thread(target=worker, daemon=True, name="aera-stream").start()
        return self._ok({"streaming": True, "conversation_id": cid})

    def _emit(self, fn: str, payload: dict) -> None:
        """Invoke a global JS callback in the window."""
        if self._window is None:
            return
        try:
            self._window.evaluate_js(f"window.{fn} && window.{fn}({json.dumps(payload)})")
        except Exception:  # noqa: BLE001 - window may be closing
            pass

    def tap_to_memory(self, conversation_id: str | None = None) -> dict:
        """Prime context before voice listening begins."""
        try:
            return self._ok(self._run(self.app.kernel.prime_context(conversation_id=conversation_id)))
        except Exception as exc:  # noqa: BLE001
            return self._err(str(exc))

    # ------------------------------------------------------------------ #
    # native dialogs
    # ------------------------------------------------------------------ #
    def open_folder_dialog(self) -> dict:
        """Native OS folder picker - the spec's 'Open Local Folder'."""
        import webview

        if self._window is None:
            return self._err("no window")
        try:
            selection = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        except Exception as exc:  # noqa: BLE001
            return self._err(f"dialog failed: {exc}")
        if not selection:
            return self._ok(None, "Cancelled")
        return self.open_workspace(str(selection[0]))

    def open_file_dialog(self, multiple: bool = False) -> dict:
        import webview

        if self._window is None:
            return self._err("no window")
        selection = self._window.create_file_dialog(
            webview.OPEN_DIALOG, allow_multiple=multiple
        )
        return self._ok(list(selection) if selection else None)

    def save_file_dialog(self, filename: str = "aera-export.md", content: str = "") -> dict:
        """Save text to a user-chosen location."""
        import webview

        if self._window is None:
            return self._err("no window")
        target = self._window.create_file_dialog(
            webview.SAVE_DIALOG, save_filename=filename
        )
        if not target:
            return self._ok(None, "Cancelled")
        path = Path(target if isinstance(target, str) else target[0])
        try:
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            return self._err(f"could not write {path}: {exc}")
        return self._ok({"path": str(path)}, f"Saved to {path.name}")

    # ------------------------------------------------------------------ #
    # workspace
    # ------------------------------------------------------------------ #
    def open_workspace(self, path: str) -> dict:
        try:
            kernel = self.app.kernel
            project = kernel.workspace.open(path, index=True)
            self._run(kernel.workspace.sync_to_memory())
            summary = kernel.workspace.summary()
            self.app.settings.set("last_workspace", str(project.root))
            return self._ok(summary, f"Opened {project.name}")
        except Exception as exc:  # noqa: BLE001
            return self._err(str(exc))

    def workspace_summary(self) -> dict:
        try:
            return self._ok(self.app.kernel.workspace.summary())
        except Exception as exc:  # noqa: BLE001
            return self._err(str(exc))

    def workspace_search(self, query: str, limit: int = 20) -> dict:
        try:
            return self._ok({"results": self.app.kernel.workspace.search(query, limit=limit)})
        except Exception as exc:  # noqa: BLE001
            return self._err(str(exc))

    def read_workspace_file(self, relative: str) -> dict:
        try:
            return self._ok(self.app.kernel.workspace.read_file(relative))
        except Exception as exc:  # noqa: BLE001
            return self._err(str(exc))

    def reveal_in_file_manager(self, path: str) -> dict:
        """Open a path in Explorer / Finder / the Linux file manager."""
        target = Path(path).expanduser()
        if not target.exists():
            return self._err(f"path not found: {target}")
        system = platform.system()
        try:
            if system == "Windows":
                subprocess.Popen(["explorer", str(target)])
            elif system == "Darwin":
                subprocess.Popen(["open", "-R", str(target)])
            else:
                subprocess.Popen(["xdg-open", str(target.parent if target.is_file() else target)])
        except OSError as exc:
            return self._err(str(exc))
        return self._ok({"path": str(target)})

    # ------------------------------------------------------------------ #
    # memory
    # ------------------------------------------------------------------ #
    def memory_search(self, query: str, limit: int = 20) -> dict:
        try:
            results = self._run(self.app.kernel.memory.recall(query, limit=limit))
            return self._ok({"results": [r.to_public() for r in results]})
        except Exception as exc:  # noqa: BLE001
            return self._err(str(exc))

    def memory_list(self, limit: int = 30) -> dict:
        try:
            nodes = self.app.kernel.memory.graph.find(limit=limit)
            return self._ok({"memories": [n.to_public() for n in nodes]})
        except Exception as exc:  # noqa: BLE001
            return self._err(str(exc))

    def memory_stats(self) -> dict:
        try:
            return self._ok(self.app.kernel.memory.stats())
        except Exception as exc:  # noqa: BLE001
            return self._err(str(exc))

    # ------------------------------------------------------------------ #
    # agents / system
    # ------------------------------------------------------------------ #
    def list_agents(self) -> dict:
        try:
            registry = self.app.kernel.registry
            return self._ok(
                {
                    "agents": registry.status(),
                    "summary": registry.summary(),
                    "capabilities": registry.capability_map(),
                }
            )
        except Exception as exc:  # noqa: BLE001
            return self._err(str(exc))

    def telemetry(self) -> dict:
        """Live host metrics for the PC Information panel."""
        try:
            return self._ok(self.app.kernel.telemetry.snapshot())
        except Exception as exc:  # noqa: BLE001
            return self._err(str(exc))

    def system_status(self) -> dict:
        try:
            return self._ok(self.app.kernel.status())
        except Exception as exc:  # noqa: BLE001
            return self._err(str(exc))

    def provider_health(self) -> dict:
        try:
            return self._ok(self._run(self.app.kernel.router.health()))
        except Exception as exc:  # noqa: BLE001
            return self._err(str(exc))

    def recent_events(self, limit: int = 40) -> dict:
        """Poll recent bus events (the desktop UI has no socket)."""
        try:
            events = self.app.kernel.bus.history("*", limit)
            return self._ok({"events": [e.to_dict() for e in events]})
        except Exception as exc:  # noqa: BLE001
            return self._err(str(exc))

    # ------------------------------------------------------------------ #
    # settings & window
    # ------------------------------------------------------------------ #
    def get_settings(self) -> dict:
        cfg = self.app.kernel.config
        return self._ok(
            {
                "settings": cfg.settings.model_dump(),
                "voice": cfg.voice.model_dump(),
                "memory": cfg.memory.model_dump(),
                "models": {
                    "default": cfg.models.default,
                    "routing_mode": cfg.models.routing_mode,
                    "local": cfg.models.local.model_dump(),
                },
                "preferences": self.app.settings.all(),
            }
        )

    def set_preference(self, key: str, value: Any) -> dict:
        self.app.settings.set(key, value)
        return self._ok({key: value})

    def set_secret(self, name: str, value: str) -> dict:
        """Store an API key in the encrypted vault."""
        try:
            self.app.kernel.vault.set(name, value)
            return self._ok({"name": name}, "Saved to the encrypted vault")
        except Exception as exc:  # noqa: BLE001
            return self._err(str(exc))

    def list_secrets(self) -> dict:
        try:
            return self._ok({"secrets": self.app.kernel.vault.masked()})
        except Exception as exc:  # noqa: BLE001
            return self._err(str(exc))

    def copy_to_clipboard(self, text: str) -> dict:
        """Best-effort native clipboard write."""
        system = platform.system()
        cmds = {
            "Darwin": ["pbcopy"],
            "Windows": ["clip"],
        }
        cmd = cmds.get(system) or ["xclip", "-selection", "clipboard"]
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            proc.communicate(text.encode("utf-8"), timeout=5)
            return self._ok(None, "Copied")
        except (OSError, subprocess.SubprocessError):
            # The UI falls back to the DOM clipboard API.
            return self._err("no native clipboard available")

    def quit(self) -> dict:
        self.app.request_quit()
        return self._ok(None, "Shutting down")
