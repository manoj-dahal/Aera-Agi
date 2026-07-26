#!/usr/bin/env bash
# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

# Start the AERA API server and dashboard.
set -euo pipefail
cd "$(dirname "$0")/.."
VENV="${VENV:-.venv}"
PY="$([ -x "$VENV/bin/python" ] && echo "$VENV/bin/python" || echo python3)"
exec "$PY" -m aera serve "$@"
