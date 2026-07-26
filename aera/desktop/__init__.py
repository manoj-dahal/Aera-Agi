# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""AERA desktop application.

Runs AERA as a native OS application: the kernel executes in-process on a
background event loop and the UI is rendered in a native window with native
menus and native file dialogs. No web server, no browser, no open port.
"""

from .app import DesktopApp, run_desktop
from .bridge import DesktopBridge
from .settings import DesktopSettings, app_data_dir

__all__ = [
    "DesktopApp",
    "DesktopBridge",
    "DesktopSettings",
    "app_data_dir",
    "run_desktop",
]
