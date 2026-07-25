#!/usr/bin/env bash
# AERA AGI — one-shot development environment setup
set -euo pipefail
cd "$(dirname "$0")/.."

echo "══════════════════════════════════════"
echo "  AERA AGI — Development Setup"
echo "══════════════════════════════════════"

[ -f .env ] || { cp .env.example .env && echo "✔ Created .env from .env.example"; }

echo "→ Installing Node dependencies…"
npm install

echo "→ Installing Python dependencies…"
pip install -r requirements.txt

echo ""
echo "✔ Setup complete. Next steps:"
echo "    make dev        # run frontend + backend"
echo "    make docs       # browse the design docs"
echo "    make docker-up  # full stack via Docker"
