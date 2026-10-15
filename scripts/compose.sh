#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if docker compose version >/dev/null 2>&1; then
  exec docker compose "$@"
elif command -v docker-compose >/dev/null 2>&1; then
  exec docker-compose "$@"
else
  printf 'Docker Compose v2 is required. Install it, then rerun scripts/start.sh.\n' >&2
  exit 1
fi
