#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Studio's shared queue owns all Docker/build work on this host.
if [[ -x "$HOME/.local/bin/studio-heavy-run" && "${EVIDENCE_QUEUED:-}" != 1 ]]; then
  exec "$HOME/.local/bin/studio-heavy-run" -- env EVIDENCE_QUEUED=1 bash scripts/start.sh
fi
if ! docker buildx inspect document-evidence-builder >/dev/null 2>&1; then
  docker buildx create --name document-evidence-builder --driver docker-container \
    --driver-opt memory=4g --driver-opt cpu-quota=200000 --driver-opt cpu-period=100000
fi
# A dedicated BuildKit service caps the work executed by the Docker daemon too.
docker buildx build --builder document-evidence-builder --load -t document-evidence:local .
docker buildx build --builder document-evidence-builder --load -f Dockerfile.ollama -t document-evidence-ollama:local .
bash scripts/compose.sh up --no-build -d --wait --wait-timeout 900
printf '\nWorkspace: http://localhost:%s\n' "${APP_PORT:-8016}"
printf 'Upload synthetic files from fixtures/documents/. First AI request may take a few minutes.\n'
