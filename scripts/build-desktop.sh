#!/usr/bin/env bash
# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

# Build the standalone AERA desktop executable for the current platform.
#
#   Linux   -> dist/AERA/AERA
#   macOS   -> dist/AERA.app
#   Windows -> dist/AERA/AERA.exe
set -euo pipefail
cd "$(dirname "$0")/.."

VENV="${VENV:-.venv}"
PY="$([ -x "$VENV/bin/python" ] && echo "$VENV/bin/python" || echo python3)"

echo "==> Checking build dependencies"
"$PY" -m pip install --quiet --upgrade pyinstaller pywebview

echo "==> Cleaning previous build"
rm -rf build dist

echo "==> Building"
"$PY" -m PyInstaller installer/aera.spec --noconfirm --clean

echo
case "$(uname -s)" in
  Darwin) echo "  Built: dist/AERA.app" ;;
  MINGW*|MSYS*|CYGWIN*) echo "  Built: dist/AERA/AERA.exe" ;;
  *) echo "  Built: dist/AERA/AERA" ;;
esac
echo "  Double-click it, or run it directly. No Python needed on the target machine."
echo
