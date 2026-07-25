#!/usr/bin/env bash
# Build the Docker image.
set -euo pipefail
cd "$(dirname "$0")/.."
TAG="${1:-aera:1.0.0}"
echo "==> Building $TAG"
docker build -t "$TAG" .
echo "==> Built $TAG"
docker images "$TAG"
