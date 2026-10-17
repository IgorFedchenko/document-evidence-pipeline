#!/usr/bin/env bash
# Shared fixture lifecycle, sourced by one-suite verification stages.
# The coordinator supplies a separate artifact directory for each stage.
if [[ -x "$HOME/.local/bin/studio-heavy-run" && "${STUDIO_HEAVY_LOCK_HELD:-}" != 1 ]]; then
  printf 'Run ./scripts/verify.sh so each stage gets its own Studio ticket.\n' >&2
  exit 1
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
project="document-evidence-check-$stage-$$"
export COMPOSE_PROJECT_NAME="$project"
server_pid=''
startup_pending=0
stop_fixture() {
  local attempt
  # A signal can arrive between the background launch and assigning its PID.
  if [[ -z "$server_pid" && "$startup_pending" == 1 ]]; then server_pid="${!:-}"; fi
  [[ -n "$server_pid" ]] || return 0
  # The launcher creates a new session before starting Bash: PGID equals $!.
  # Also signal the direct child in case cancellation beats os.setsid().
  kill -TERM -- "-$server_pid" 2>/dev/null || true
  kill -TERM "$server_pid" 2>/dev/null || true
  for ((attempt=0; attempt<20; attempt++)); do
    if ! kill -0 -- "-$server_pid" 2>/dev/null && ! kill -0 "$server_pid" 2>/dev/null; then break; fi
    sleep 0.1
  done
  # Always retry the group signal: it may have formed during the first TERM.
  kill -KILL -- "-$server_pid" 2>/dev/null || true
  kill -KILL "$server_pid" 2>/dev/null || true
  wait "$server_pid" 2>/dev/null || true
}
cleanup() {
  status=$?
  trap - EXIT INT TERM
  stop_fixture
  # Only this invocation's uniquely named project and temporary vector volume.
  if ! bash scripts/compose.sh -p "$project" down --volumes; then
    [[ "$status" != 0 ]] || status=1
  fi
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

verify_start_fixture() {
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
  startup_pending=1
  EVIDENCE_QUEUED=1 python3 -c 'import os; os.setsid(); os.execvp("bash", ["bash", "scripts/start.sh"])' \
    >"$artifacts/server.log" 2>&1 &
  server_pid=$!
  ready=0
  for ((i=0; i<180; i++)); do
    if curl -fs "$DEMO_URL/api/health" >"$artifacts/health.json"; then ready=1; break; fi
    kill -0 "$server_pid" 2>/dev/null || break
    sleep 1
  done
  if [[ "$ready" != 1 ]]; then printf 'Recorded app did not become ready; see %s\n' "$artifacts/server.log" >&2; exit 1; fi
}
