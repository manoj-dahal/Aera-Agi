#!/usr/bin/env bash
# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

# Build the standalone AERA desktop executable for the current platform.
#
#   Linux   -> dist/AERA/AERA
#   macOS   -> dist/AERA.app
#   Windows -> dist/AERA/AERA.exe
#
# The React interface is built first. installer/aera.spec refuses to run
# without it, so on a clean clone this script used to stop with the spec's
# error message telling the reader to go and run npm themselves -- which is
# something the script can simply do.
set -euo pipefail
cd "$(dirname "$0")/.."

VENV="${VENV:-.venv}"
PY="$([ -x "$VENV/bin/python" ] && echo "$VENV/bin/python" || echo python3)"
UI="aera/desktop/ui-react/index.html"

# Fail with a sentence a reader can act on, rather than a Node stack trace
# five steps later.
need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "error: $1 is required to build the interface but is not installed." >&2
    echo "       Install Node 20 or newer from https://nodejs.org and re-run." >&2
    exit 1
  }
}

echo "==> Checking build dependencies"
need node
need npm
"$PY" -m pip install --quiet --upgrade pyinstaller pywebview

echo "==> Building interface"
(
  cd interface
  # npm ci is reproducible and needs the lockfile; fall back when it is
  # absent so a modified checkout still builds.
  if [ -f package-lock.json ]; then npm ci --silent; else npm install --silent; fi
  npm run build
)

# The spec checks this too, but failing here names the step that was meant
# to produce it instead of blaming the packager.
[ -f "$UI" ] || { echo "error: the interface build produced no $UI" >&2; exit 1; }

echo "==> Cleaning previous build"
rm -rf build dist

echo "==> Building executable"
"$PY" -m PyInstaller installer/aera.spec --noconfirm --clean

# Confirm something was actually produced. PyInstaller can exit 0 having
# written nothing useful if the spec is edited badly.
case "$(uname -s)" in
  Darwin)               ARTIFACT="dist/AERA.app" ;;
  MINGW*|MSYS*|CYGWIN*) ARTIFACT="dist/AERA/AERA.exe" ;;
  *)                    ARTIFACT="dist/AERA/AERA" ;;
esac
[ -e "$ARTIFACT" ] || { echo "error: the build reported success but $ARTIFACT is missing" >&2; exit 1; }

echo
echo "  Built: $ARTIFACT"
echo "  Double-click it, or run it directly. No Python needed on the target machine."
echo
