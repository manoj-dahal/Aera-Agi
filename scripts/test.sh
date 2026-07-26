#!/usr/bin/env bash
# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

# Run the full test suite (plus linting when ruff is available).
set -euo pipefail
cd "$(dirname "$0")/.."
VENV="${VENV:-.venv}"
PY="$([ -x "$VENV/bin/python" ] && echo "$VENV/bin/python" || echo python3)"

echo "==> Tests"
"$PY" -m pytest "$@"

# ruff ships as a binary, not an importable module: the old check was
# `python -c 'import ruff'`, which always fails, so linting never ran here.
# And `|| true` discarded the result, so it could not have failed the script
# even when it did run.
RUFF="$([ -x "$VENV/bin/ruff" ] && echo "$VENV/bin/ruff" || command -v ruff || true)"
if [ -n "$RUFF" ]; then
  echo "==> Lint"
  "$RUFF" check aera/ tests/ tools/ installer/
else
  echo "==> Lint skipped: ruff is not installed (pip install -e \".[dev]\")"
fi
