#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# One queue owner for the entire suite, including the temporary app and index.
if [[ -x "$HOME/.local/bin/studio-heavy-run" && "${EVIDENCE_QUEUED:-}" != 1 ]]; then
  exec "$HOME/.local/bin/studio-heavy-run" --project document-evidence-pipeline -- env EVIDENCE_QUEUED=1 bash scripts/verify.sh
fi

artifacts="${TEST_ARTIFACT_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/evidence-check.XXXXXX")}"
mkdir -p "$artifacts"
artifacts="$(cd "$artifacts" && pwd)"
export APP_PORT="${APP_PORT:-8018}" VECTOR_PORT="${VECTOR_PORT:-8098}"
export TEST_WEAVIATE_URL="http://127.0.0.1:$VECTOR_PORT" DEMO_URL="http://127.0.0.1:$APP_PORT"
export DEMO_DATA_DIR="$artifacts/data" PYTHONPATH=backend OMP_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false
export OCR_PROVIDER=tesseract ALLOW_PAID_OCR=false EMBEDDING_MODE=hash
export ACCESS_TOKEN=''
export PLAYWRIGHT_OUTPUT_DIR="$artifacts/browser" PLAYWRIGHT_HTML_OUTPUT_DIR="$artifacts/report"
export SCREENSHOT_PATH="$artifacts/workspace.png"
export COVER_PATH="$artifacts/cover.png"
project="document-evidence-check-$$"
export COMPOSE_PROJECT_NAME="$project"
server_pid=''
cleanup() {
  if [[ -n "$server_pid" ]]; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
  # Only this invocation's uniquely named project and temporary vector volume.
  bash scripts/compose.sh -p "$project" down --volumes
}
trap cleanup EXIT
trap 'exit 130' INT TERM

uv run --frozen ruff check backend scripts tests
uv run --frozen ruff format --check backend scripts tests
uv run --frozen python - "$APP_PORT" "$VECTOR_PORT" "$artifacts/source-manifest.json" <<'PY'
import hashlib
import json
import socket
import subprocess
import sys
from pathlib import Path

for port in map(int, sys.argv[1:3]):
    with socket.socket() as listener:
        try:
            listener.bind(("127.0.0.1", port))
        except OSError as exc:
            raise SystemExit(f"Verification requires unused loopback port {port}") from exc

paths = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"])
files = {}
for name in paths.decode().split("\0"):
    path = Path(name)
    if not name or not path.is_file() or name.startswith("docs/screenshots/") or path.suffix == ".log":
        continue
    files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
manifest = {
    "head_before_verification": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "excluded": ["gitignored/generated files", "docs/screenshots/", "*.log"],
    "files": dict(sorted(files.items())),
}
Path(sys.argv[3]).write_text(json.dumps(manifest, indent=2) + "\n")
PY
# Exercise the documented one-command startup, including dependency sync and UI build.
# EVIDENCE_QUEUED prevents taking the same host locks twice.
EVIDENCE_QUEUED=1 bash scripts/start.sh >"$artifacts/server.log" 2>&1 &
server_pid=$!
ready=0
for ((i=0; i<180; i++)); do
  if curl -fs "$DEMO_URL/api/health" >"$artifacts/health.json"; then ready=1; break; fi
  kill -0 "$server_pid" 2>/dev/null || break
  sleep 1
done
if [[ "$ready" != 1 ]]; then printf 'Recorded app did not become ready; see %s\n' "$artifacts/server.log" >&2; exit 1; fi
uv run --frozen pytest -q --junitxml="$artifacts/python.xml"
npm run e2e --prefix frontend
if command -v ffmpeg >/dev/null; then
  for video in "$artifacts"/browser/*/video.webm; do
    [[ -f "$video" ]] || continue
    ffmpeg -y -loglevel error -threads 2 -filter_threads 2 -filter_complex_threads 2 -i "$video" \
      -vf 'fps=7,scale=1000:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer' \
      -loop 0 "$artifacts/walkthrough.gif"
    break
  done
fi
printf '\nPASS: real OCR/API/worker/SQLite/Weaviate; recorded extraction/hash vectors.\nEvidence: %s\n' "$artifacts"
