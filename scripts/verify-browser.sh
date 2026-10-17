#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
stage=browser
source scripts/verify-common.sh

verify_start_fixture
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
printf '\nBrowser checks complete. Evidence: %s\n' "$artifacts"
