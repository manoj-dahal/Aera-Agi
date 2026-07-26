# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""AERA desktop application.

A native OS application: the AERA kernel runs in-process on a background event
loop, and the UI is rendered in a native window (WebKit on Linux/macOS, WebView2
on Windows) with native menus and native file dialogs.

There is no web server, no port to bind and no browser involved - the UI is
loaded from local files and talks to the kernel through a direct Python bridge.
"""

from __future__ import annotations

import asyncio
import sys
import threading
from pathlib import Path

from ..core.config import AeraConfig, load_config
from ..core.kernel import Kernel
from ..core.logging import get_logger, setup_logging
from .bridge import DesktopBridge
from .settings import DesktopSettings, app_data_dir

logger = get_logger("desktop.app")

#: Built React interface. The only UI: there is no hand-written fallback.
UI_REACT_DIR = Path(__file__).resolve().parent / "ui-react"

#: Shown when the interface has not been built yet.
BUILD_HINT = "cd interface && npm install && npm run build"


def resolve_ui() -> Path:
    """Return the UI entry point.

    The interface is a build artifact, so a source checkout has none until it
    is built. Raising here with the exact command beats loading a blank
    window and leaving the user to guess.
    """
    index = UI_REACT_DIR / "index.html"
    if not index.is_file():
        raise FileNotFoundError(
            f"the AERA interface has not been built yet.\n"
            f"  expected: {index}\n"
            f"  build it: {BUILD_HINT}"
        )
    return index


class DesktopApp:
    """Owns the kernel thread, the native window and their shared lifetime."""

    def __init__(self, config: AeraConfig | None = None) -> None:
        self.config = config or self._default_config()
        self.settings = DesktopSettings()
        self.kernel: Kernel | None = None
        self.bridge = DesktopBridge(self)
        self.window = None

        self.loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._startup_error: BaseException | None = None

    # ------------------------------------------------------------------ #
    # configuration
    # ------------------------------------------------------------------ #
    @staticmethod
    def _default_config() -> AeraConfig:
        """Desktop installs keep state in the user's app-data directory."""
        cfg = load_config()
        data = app_data_dir()
        cfg.system.storage = str(data)
        cfg.system.logs = str(data / "logs")
        cfg.system.cache = str(data / "cache")
        cfg.system.temp = str(data / "temp")
        cfg.security.secret_key_file = str(data / ".secret.key")
        cfg.logging.file = str(data / "logs" / "aera.log")
        return cfg

    # ------------------------------------------------------------------ #
    # kernel thread
    # ------------------------------------------------------------------ #
    def _kernel_thread(self) -> None:
        """Run the kernel's event loop for the life of the application."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.loop = loop

        async def boot() -> None:
            self.kernel = Kernel(self.config)
            await self.kernel.start()

        try:
            loop.run_until_complete(boot())
        except BaseException as exc:  # noqa: BLE001 - reported to the main thread
            self._startup_error = exc
            logger.exception("kernel failed to start")
            self._ready.set()
            return

        self._ready.set()
        try:
            loop.run_forever()
        finally:
            try:
                if self.kernel is not None:
                    loop.run_until_complete(self.kernel.stop())
            except Exception:  # noqa: BLE001
                logger.exception("error during kernel shutdown")
            loop.close()

    def start_kernel(self, timeout: float = 60.0) -> None:
        self._thread = threading.Thread(
            target=self._kernel_thread, daemon=True, name="aera-kernel"
        )
        self._thread.start()
        if not self._ready.wait(timeout):
            raise RuntimeError("AERA kernel did not start in time")
        if self._startup_error is not None:
            raise self._startup_error

    def stop_kernel(self) -> None:
        if self.loop is not None and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=15)

    # ------------------------------------------------------------------ #
    # native menus
    # ------------------------------------------------------------------ #
    def _build_menu(self):
        from webview.menu import Menu, MenuAction, MenuSeparator

        def js(code: str):
            def action() -> None:
                if self.window is not None:
                    self.window.evaluate_js(code)

            return action

        return [
            Menu(
                "File",
                [
                    MenuAction("Open Folder…", self.bridge.open_folder_dialog),
                    MenuAction("Re-index Workspace", js("window.aeraMenu('reindex')")),
                    MenuSeparator(),
                    MenuAction("Export Conversation…", js("window.aeraMenu('export')")),
                    MenuSeparator(),
                    MenuAction("Quit AERA", self.request_quit),
                ],
            ),
            Menu(
                "View",
                [
                    MenuAction("Dashboard", js("window.aeraMenu('view:dashboard')")),
                    MenuAction("Memory Graph", js("window.aeraMenu('view:memory')")),
                    MenuAction("Agents", js("window.aeraMenu('view:agents')")),
                    MenuAction("Workspace", js("window.aeraMenu('view:workspace')")),
                    MenuAction("Settings", js("window.aeraMenu('view:settings')")),
                    MenuSeparator(),
                    MenuAction("Toggle Full Screen", self._toggle_fullscreen),
                ],
            ),
            Menu(
                "Conversation",
                [
                    MenuAction("New Conversation", js("window.aeraMenu('new-chat')")),
                    MenuAction("Clear Transcript", js("window.aeraMenu('clear')")),
                ],
            ),
            Menu(
                "Help",
                [
                    MenuAction("About AERA", js("window.aeraMenu('about')")),
                    MenuAction("Open Data Folder", self._open_data_folder),
                ],
            ),
        ]

    def _toggle_fullscreen(self) -> None:
        if self.window is not None:
            self.window.toggle_fullscreen()

    def _open_data_folder(self) -> None:
        self.bridge.reveal_in_file_manager(str(app_data_dir()))

    # ------------------------------------------------------------------ #
    # window lifecycle
    # ------------------------------------------------------------------ #
    def _on_closing(self) -> None:
        """Persist window geometry before the window disappears."""
        try:
            if self.window is not None:
                self.settings.update(
                    {
                        "window_width": int(self.window.width),
                        "window_height": int(self.window.height),
                        "window_x": int(self.window.x) if self.window.x is not None else None,
                        "window_y": int(self.window.y) if self.window.y is not None else None,
                    }
                )
        except Exception:  # noqa: BLE001 - geometry is best effort
            pass

    def _on_loaded(self) -> None:
        """Restore the previous workspace once the UI is live."""
        last = self.settings.get("last_workspace")
        if last and Path(last).is_dir():
            try:
                self.bridge.open_workspace(last)
                if self.window is not None:
                    self.window.evaluate_js("window.aeraRefreshAll && window.aeraRefreshAll()")
            except Exception:  # noqa: BLE001
                logger.debug("could not restore the previous workspace")

    def request_quit(self) -> None:
        if self.window is not None:
            self.window.destroy()

    # ------------------------------------------------------------------ #
    # run
    # ------------------------------------------------------------------ #
    def run(self, *, debug: bool = False, gui: str | None = None) -> int:
        """Start the kernel, open the native window and block until closed."""
        import webview

        setup_logging(
            self.config.logging.level,
            json_format=self.config.logging.json_format,
            file=self.config.logging.file,
        )

        try:
            index = resolve_ui()
        except FileNotFoundError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        logger.info("starting the AERA desktop application")
        self.start_kernel()

        self.window = webview.create_window(
            title="AERA — AI Operating System",
            url=str(index),
            js_api=self.bridge,
            width=int(self.settings.get("window_width")),
            height=int(self.settings.get("window_height")),
            x=self.settings.get("window_x"),
            y=self.settings.get("window_y"),
            min_size=(980, 640),
            background_color="#07090F",
            text_select=True,
        )
        self.bridge.attach(self.window)
        self.window.events.closing += self._on_closing
        self.window.events.loaded += self._on_loaded

        try:
            webview.start(
                debug=debug,
                gui=gui,
                menu=self._build_menu(),
                private_mode=False,
                storage_path=str(app_data_dir() / "webview"),
            )
        finally:
            logger.info("window closed, stopping the kernel")
            self.stop_kernel()
        return 0


def run_desktop(config: AeraConfig | None = None, *, debug: bool = False,
                gui: str | None = None) -> int:
    """Entry point used by ``aera desktop`` and the packaged executable."""
    return DesktopApp(config).run(debug=debug, gui=gui)
