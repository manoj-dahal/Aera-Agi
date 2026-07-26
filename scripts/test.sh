#!/usr/bin/env bash
# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

# Run the full test suite (plus linting when ruff is available).
set -euo pipefail
cd "$(dirname "$0")/.."
VENV="${VENV:-.venv}"
PY="$([ -x "$VENV/bin/python" ] && echo "$VENV/bin/python" || echo python3)"

echo "==> Tests"
"$PY" -m pytest "$@"

if "$PY" -c 'import ruff' 2>/dev/null || [ -x "$VENV/bin/ruff" ]; then
  echo "==> Lint"
  "$VENV/bin/ruff" check aera/ tests/ || true
fi
