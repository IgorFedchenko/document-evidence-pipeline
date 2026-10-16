# Testing

## Reproduce the acceptance flow

Install the prerequisites in the README, then run `./scripts/start.sh` once to prepare dependencies.
Stop the app with Ctrl-C. Install a browser if it is absent:

```sh
cd frontend
npx playwright install chromium
cd ..
./scripts/verify.sh
```

The verification script checks Python formatting/lint, starts a uniquely named real Weaviate container,
runs Python tests, typechecks/builds React, starts the recorded app and runs Playwright. Its default ports
are app 8018 and index 8098; set `APP_PORT` and `VECTOR_PORT` to unused loopback ports if needed.
`TEST_ARTIFACT_DIR` can select an external directory for JUnit, browser reports/video, server logs and a
screenshot. Otherwise it uses an OS temporary directory. Use a fresh output directory for each run.

On hosts with `studio-heavy-run`, the script queues the entire lifecycle once. Do not wrap it again
or launch detached tests that outlive its queue owner. It stops its own app and removes only its unique
Compose project's temporary vector volume. It leaves other workspaces, volumes and models untouched.

## What the checks establish

| Layer | Evidence |
|---|---|
| Real OCR | Image-only synthetic PDFs pass through Tesseract; source words and boxes are validated. |
| Extraction boundaries | Authored responses, strict schema failures, type/value/quote checks, conflicts and absent fields. The invalid-extra-key mock includes completion metadata and a valid-response control. |
| Durability | Concurrent deduplication, bounded retries, lease recovery and reuse of persisted page/batch checkpoints. |
| Review/security | Audit history, optimistic conflicts, input limits, token protection, origin/host rejection and paid-OCR gating. |
| Bulk behavior | Synthetic 205-page processing/checkpoint recovery; this uses doubles and is not a live-model throughput measurement. |
| Real search server | Explicit `DocumentPassageTest` collection, repeated upsert and hybrid retrieval in Weaviate. |
| Recorded runtime | Honest health mode; reject otherwise valid documents outside the fixture byte set; contract OCR/worker integration. |
| Real browser | Upload, page/word highlighting, human review, citation navigation, duplicate upload, unsupported question and mobile overflow. No application-route mocks. |

The browser's screenshot and GIF are actual recorded-mode captures. Models and embeddings are explicit
doubles; passing checks do not estimate live accuracy. Historical model measurement at `93e3470` remains
11/13 expected development fields, with the original stricter feasibility gate failed.

## Focused development checks

```sh
uv run --frozen ruff check backend scripts tests
uv run --frozen ruff format --check backend scripts tests
uv run --frozen pytest -q
npm run build --prefix frontend
DEMO_URL=http://127.0.0.1:8017 npm run e2e --prefix frontend
```

The unit command skips the real-index test unless `TEST_WEAVIATE_URL` is supplied. Full acceptance through
`verify.sh` includes it. On shared Studio hosts, individual heavy/full suites, builds, Docker operations
and browser checks also require the heavy-job queue. The helper handles it automatically.

GitHub Actions is manual-only with a public-repository condition. No private hosted run is required or
claimed, and no private workflow may be dispatched. First-time package/image/browser installation uses
the network; the recorded runtime itself makes no inference/cloud requests.
