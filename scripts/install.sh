#!/usr/bin/env bash
# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

# Install AERA and its dependencies into a local virtualenv.
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"
VENV="${VENV:-.venv}"

echo "==> Checking Python"
"$PYTHON" -c 'import sys; assert sys.version_info >= (3,10), f"Python 3.10+ required, found {sys.version.split()[0]}"'

echo "==> Creating virtualenv at $VENV"
[ -d "$VENV" ] || "$PYTHON" -m venv "$VENV"

echo "==> Installing dependencies"
"$VENV/bin/pip" install --quiet --upgrade pip
# [desktop] as well as [dev]: bare `aera` launches the desktop application,
# which imports pywebview. Installing only [dev] left the command this script
# recommends failing with ModuleNotFoundError on a clean machine.
"$VENV/bin/pip" install --quiet -e ".[dev,desktop]"

echo "==> Preparing runtime directories"
mkdir -p storage/logs storage/cache storage/temp

[ -f .env ] || { [ -f .env.example ] && cp .env.example .env && echo "==> Created .env from template"; }

cat <<MSG

  AERA installed.

    source $VENV/bin/activate
    aera                  # desktop application
    aera serve            # dashboard at http://localhost:8080
    aera repl             # interactive terminal session
    pytest -q             # run the test suite

  To build a standalone executable (needs Node 20+ for the interface):

    ./scripts/build-desktop.sh

  No API keys are required: AERA runs offline on the built-in reasoner.
  For a full local LLM, install Ollama and run 'ollama serve'.

MSG
