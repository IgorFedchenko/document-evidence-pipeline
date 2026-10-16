#!/usr/bin/env bash
# Called by start.sh inside the host's heavy-job queue when available.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v tesseract >/dev/null || { printf 'Install Tesseract with English data first.\n' >&2; exit 1; }
uv sync --frozen --extra dev
if [[ ! -d frontend/node_modules ]]; then
  npm ci --prefix frontend --no-fund --no-audit
fi
npm run build --prefix frontend
bash scripts/compose.sh up -d --wait --wait-timeout 120 weaviate
