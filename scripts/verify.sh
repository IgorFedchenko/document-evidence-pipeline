#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${STUDIO_HEAVY_LOCK_HELD:-}" == 1 || "${STUDIO_LIGHT_LOCK_HELD:-}" == 1 ]]; then
  printf 'Run ./scripts/verify.sh directly; its stages need separate Studio tickets.\n' >&2
  exit 1
fi

artifacts="${TEST_ARTIFACT_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/evidence-check.XXXXXX")}"
mkdir -p "$artifacts"
artifacts="$(cd "$artifacts" && pwd)"

run_stage() {
  local stage="$1"
  export TEST_ARTIFACT_DIR="$artifacts/$stage"
  if [[ -x "$HOME/.local/bin/studio-heavy-run" ]]; then
    "$HOME/.local/bin/studio-heavy-run" --project document-evidence-pipeline -- bash "scripts/verify-$stage.sh"
  else
    bash "scripts/verify-$stage.sh"
  fi
}

# Each ticket owns setup, one suite and cleanup; no services remain between tickets.
run_stage python
run_stage browser
printf '\nPASS: real OCR/API/worker/SQLite/Weaviate; recorded extraction/hash vectors.\nEvidence: %s\n' "$artifacts"
