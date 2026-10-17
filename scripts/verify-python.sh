#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
stage=python
source scripts/verify-common.sh

uv sync --frozen --extra dev
uv run --frozen ruff check backend scripts tests
uv run --frozen ruff format --check backend scripts tests
verify_start_fixture
uv run --frozen pytest -q --junitxml="$artifacts/python.xml"
printf '\nPython checks complete. JUnit: %s/python.xml\n' "$artifacts"
