# Document Evidence Pipeline — project instructions

Independent MIT reference implementation. Use synthetic/public fixtures only; never add employer/client
code, documents, names, credentials or confidential material. Preserve contributor and agent attribution.

## Structure

- `backend/app/`: FastAPI, SQLite jobs, OCR, extraction/validation, worker and evidence retrieval.
- `frontend/src/`: React workspace; `components/FieldCard.tsx` owns field review presentation.
- `fixtures/`: generated synthetic documents, human-authored expected values and recorded test responses.
- `scripts/`: recorded demo startup, verification, fixture generation and optional local adapters.
- `tests/` and `frontend/e2e/`: Python boundaries/integration and real-app browser acceptance.
- `docs/`: public architecture, decisions, testing and selected clean screenshots.

## Commands

- `./scripts/start.sh`: default recorded fixture demo; real Tesseract/SQLite/worker/Weaviate, authored
  extraction and hash-vector doubles; no model downloads or inference.
- `./scripts/verify.sh`: full isolated Python/integration/build/browser acceptance. It automatically
  uses two sequential `studio-heavy-run` tickets where installed: Python, then browser. Each stage
  owns setup and cleanup; run the coordinator directly without an outer queue wrapper.
- `uv run --frozen ruff check backend scripts tests` and `uv run --frozen ruff format --check backend scripts tests`.
- `uv run --frozen pytest -q`: unit/OCR suite; index integration requires `TEST_WEAVIATE_URL`.
- `npm run build --prefix frontend`; `npm run e2e --prefix frontend` requires a running app.

On shared hosts, put all heavy tests, builds, Docker jobs and browser checks through the host's
`studio-heavy-run` queue. Do not interrupt unrelated work or prune shared Docker resources.

## Boundaries

The default recorded runtime accepts only bundled fixture bytes. Do not silently substitute recordings
for arbitrary documents or describe a recorded check as live-model accuracy. API answers use lexical
`evidence_answer`; the standalone model selector is not connected to the API/UI.

Preserve extraction/inference/selection behavior measured at `93e3470`: 11/13 expected development
fields; invoice dates missing; invalid contract duration-as-date flagged for review. Do not change
prompts, Pydantic schema or grounding rules merely to improve the demo. Pydantic model docstrings
also affect JSON schema. Human edits preserve original machine evidence and must be labelled that way.

No paid services, cloud OCR, product LLM keys, live model calls or model downloads without explicit owner
approval. Optional local model adapters are opt-in. Textract requires explicit cost approval and remains
disabled; do not supply cloud credentials. Keep logs free of document text and secrets.

Keep process journals, reviews, raw recordings and host execution artifacts outside the product tree.
Commit only selected synthetic screenshot/GIF assets. Do not rewrite history, squash or force-push.
Keep this repository private until the owner's common publication review. All new commits use
`[skip ci]`; never run or dispatch private GitHub Actions. The workflow also guards private execution.
