# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Entry point for the packaged AERA desktop executable.

Frozen builds have no working directory guarantees and no console, so this
resolves bundled resources explicitly and reports fatal errors in a dialog
rather than to a terminal nobody is watching.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def bundle_root() -> Path:
    """Directory holding bundled data, whether frozen or run from source."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def main() -> int:
    root = bundle_root()

    # Ship the default configuration with the app; user overrides live in the
    # per-user data directory, which the desktop app points the kernel at.
    bundled_config = root / "config"
    if bundled_config.is_dir():
        os.environ.setdefault("AERA_CONFIG_DIR", str(bundled_config))

    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    try:
        from aera.desktop import run_desktop

        return run_desktop()
    except Exception as exc:  # noqa: BLE001 - last resort for a windowed app
        message = f"AERA could not start.\n\n{type(exc).__name__}: {exc}"
        try:
            import webview

            webview.create_window("AERA — Startup Error", html=_error_html(message))
            webview.start()
        except Exception:  # noqa: BLE001
            print(message, file=sys.stderr)
        return 1


def _error_html(message: str) -> str:
    import html

    return f"""<!DOCTYPE html><html><body style="
        background:#07090f;color:#e9eef8;font-family:system-ui,sans-serif;
        padding:32px;line-height:1.6">
      <h2 style="color:#f87171;margin:0 0 12px">AERA failed to start</h2>
      <pre style="background:#111725;border:1px solid #202a3e;border-radius:8px;
        padding:14px;white-space:pre-wrap;font-size:12px">{html.escape(message)}</pre>
      <p style="color:#8494b2;font-size:13px">
        If this persists, run <code>aera serve</code> for the headless server,
        or report the issue with the text above.</p>
    </body></html>"""


if __name__ == "__main__":
    raise SystemExit(main())
