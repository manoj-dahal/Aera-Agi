# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

# PyInstaller spec — builds a self-contained AERA desktop executable.
#
#   pyinstaller installer/aera.spec --noconfirm
#
# Produces dist/AERA (Linux/macOS) or dist/AERA.exe (Windows). End users need
# no Python installation: the interpreter, dependencies, UI assets and default
# configuration are all bundled.

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve().parent
IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"

# The UI is loaded from disk at runtime, so the built interface must ship
# with the app. Build it first: cd interface && npm install && npm run build
UI_DIR = ROOT / "aera" / "desktop" / "ui-react"
if not (UI_DIR / "index.html").is_file():
    raise SystemExit(
        f"the interface has not been built: {UI_DIR / 'index.html'} is missing.\n"
        "run: cd interface && npm install && npm run build"
    )

datas = [
    (str(UI_DIR), "aera/desktop/ui-react"),
    (str(ROOT / "config"), "config"),
]

# Providers and routers are resolved by name at runtime, so PyInstaller's
# static analysis cannot see them.
hiddenimports = [
    *collect_submodules("aera"),
    "webview",
    "uvicorn",
    "anyio",
    "httpx",
    "cryptography",
    "yaml",
]

# The desktop build has no need for the server stack's optional extras.
excludes = [
    "tkinter", "matplotlib", "numpy", "scipy", "pandas",
    "PIL", "pytest", "IPython", "notebook",
]

a = Analysis(
    [str(ROOT / "installer" / "entrypoint.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AERA",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # windowed application: no terminal
    disable_windowed_traceback=False,
    argv_emulation=IS_MACOS,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "installer" / "icon.ico") if IS_WINDOWS else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AERA",
)

if IS_MACOS:
    app = BUNDLE(
        coll,
        name="AERA.app",
        icon=str(ROOT / "installer" / "icon.icns"),
        bundle_identifier="ai.aera.desktop",
        info_plist={
            "CFBundleName": "AERA",
            "CFBundleDisplayName": "AERA",
            "CFBundleShortVersionString": "1.0.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
            # The workspace indexer reads user-selected project folders.
            "NSDesktopFolderUsageDescription": "AERA indexes project folders you open.",
            "NSDocumentsFolderUsageDescription": "AERA indexes project folders you open.",
        },
    )
