#!/usr/bin/env bash
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
"$VENV/bin/pip" install --quiet -e ".[dev]"

echo "==> Preparing runtime directories"
mkdir -p storage/logs storage/cache storage/temp

[ -f .env ] || { [ -f .env.example ] && cp .env.example .env && echo "==> Created .env from template"; }

cat <<MSG

  AERA installed.

    source $VENV/bin/activate
    aera serve            # dashboard at http://localhost:8080
    aera repl             # interactive terminal session
    pytest -q             # run the test suite

  No API keys are required: AERA runs offline on the built-in reasoner.
  For a full local LLM, install Ollama and run 'ollama serve'.

MSG
