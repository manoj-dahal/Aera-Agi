#!/usr/bin/env bash
# Start the AERA API server and dashboard.
set -euo pipefail
cd "$(dirname "$0")/.."
VENV="${VENV:-.venv}"
PY="$([ -x "$VENV/bin/python" ] && echo "$VENV/bin/python" || echo python3)"
exec "$PY" -m aera serve "$@"
