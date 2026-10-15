#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv run ruff check backend scripts tests
uv run pytest -q
if [[ -x "$HOME/.local/bin/studio-heavy-run" ]]; then
  "$HOME/.local/bin/studio-heavy-run" -- npm run build --prefix frontend
  "$HOME/.local/bin/studio-heavy-run" -- npm run e2e --prefix frontend
else
  npm run build --prefix frontend
  npm run e2e --prefix frontend
fi
