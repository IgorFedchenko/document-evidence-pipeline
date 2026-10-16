#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Keep preparation in the shared queue; the interactive server starts after it exits.
prepare=(bash scripts/prepare-demo.sh)
if [[ -x "$HOME/.local/bin/studio-heavy-run" && "${EVIDENCE_QUEUED:-}" != 1 ]]; then
  "$HOME/.local/bin/studio-heavy-run" --project document-evidence-pipeline -- "${prepare[@]}"
else
  "${prepare[@]}"
fi
export PYTHONPATH=backend OMP_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false
printf '\nRecorded fixture demo: http://127.0.0.1:%s\n' "${APP_PORT:-8017}"
printf 'Real OCR and search; recorded extraction and hash-vector doubles. Ctrl-C stops the app.\n'
exec uv run --frozen python scripts/recorded_demo.py
