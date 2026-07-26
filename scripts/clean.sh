#!/usr/bin/env bash
# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

# Remove caches and build artefacts. Runtime state under storage/ is preserved
# unless --all is passed.
set -euo pipefail
cd "$(dirname "$0")/.."

find . -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find . -type d -name '*.egg-info' -prune -exec rm -rf {} + 2>/dev/null || true
rm -rf .pytest_cache .ruff_cache .mypy_cache build dist .coverage htmlcov
echo "==> Caches cleared"

if [ "${1:-}" = "--all" ]; then
  rm -rf storage .tmp
  echo "==> Runtime state removed"
fi
