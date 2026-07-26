#!/usr/bin/env bash
# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

# Build the Docker image.
set -euo pipefail
cd "$(dirname "$0")/.."
TAG="${1:-aera:1.0.0}"
echo "==> Building $TAG"
docker build -t "$TAG" .
echo "==> Built $TAG"
docker images "$TAG"
