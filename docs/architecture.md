# Architecture

Folio is a single-workspace reference with a local document store, a durable SQLite job queue and a
rebuildable Weaviate search index. The API serves the built React workspace and accepts files; the
worker processes them independently. The recorded bootstrap runs that worker in a background thread
beside Uvicorn. The optional local-model Compose deployment runs API and worker as separate services.

## Processing and persistence

Upload streams to a temporary file while computing SHA-256. Signature/parser checks precede storage;
a database unique constraint resolves concurrent duplicate uploads. Accepted bytes go into a UUID
folder. The worker atomically claims a job and renews its lease while rendering and OCRing pages.
OCR text, word confidence and normalized word boxes are saved page by page; previews are raster images.
Two-page extraction batches are cached, then merged into typed fields with independent source checks.

Each candidate is validated for field type, claimed page, supporting value and contiguous source word
span. Missing fields and conflicts enter review. Confidence is bounded by OCR quality. The original
candidate remains visible even when unsupported; absent evidence and zero confidence indicate that
it is not validated. Human edits use version checks and append old/new values to review history.
They do not regenerate machine quotes, confidence or boxes.

Indexing creates overlapping page-bounded passages with deterministic UUIDs and explicit vectors.
Only completely indexed documents are eligible for answers. The API asks Weaviate for hybrid dense/BM25
hits, filters eligible document IDs, then ranks source lines by lexical question overlap. Citations
link the exact excerpt to a document page. This is provenance-aware retrieval, not a semantic guarantee
or generated answer. `selection.py` contains a separate constrained local-model evidence selector;
`main.py` does not invoke it.

## Runtime modes

| Mode | Extraction | Embeddings | Infrastructure |
|---|---|---|---|
| Default `scripts/start.sh` | Manually authored `fixtures/responses/` | Deterministic 256-dimensional hash-vector double | Native API/worker/Tesseract/SQLite + dedicated Docker Weaviate |
| `scripts/verify.sh` | Same recorded extractor | Same hash double | Fresh isolated data, temporary Weaviate project, real browser |
| Optional local-model adapters | Ollama constrained JSON | BGE FastEmbed/ONNX | `compose.local-models.yaml`; separate API and worker, local model service |

Recorded extraction is intentionally fixture-specific, with upload digests checked against the bundled
files. It is not a fallback for arbitrary uploads. `/api/health` reports `extractor: recorded`,
`embeddings: hash`, `ocr: tesseract`. Health is liveness/mode information, not dependency readiness.
The bootstrap forces those safe providers even if an existing `.env` contains local-model settings.

`APP_PORT`/`VECTOR_PORT` override demo loopback ports 8017/8097. `DEMO_DATA_DIR` changes native app
storage. `ACCESS_TOKEN` enables the optional workspace cookie. API upload configuration otherwise
comes from `Settings`; do not point a recorded workspace at a live model's data/index.

The local-model adapter stack is optional and unconnected in recorded startup. Its explicit
`scripts/start-local-models.sh` builds a CPU-only Ollama image and downloads the configured model;
BGE weights are also fetched on first embedding. Do not invoke it without owner approval in a managed
session. Historical measurements used qwen2.5:1.5b and BGE; recorded acceptance does not test their
quality or install weights. The AWS Textract adapter is separately cost-gated and disabled by default.
No cloud LLM adapter is included.

## Failure and deployment boundaries

Transient errors use three attempts with exponential backoff. OCR and extraction checkpoints survive
retry; index upserts can repeat. Expired final leases become failures rather than disappearing jobs.
Retry resets a failed job's attempt budget. Logs contain job IDs/error types, never document text.

SQLite WAL is suitable for this bounded local workload. Horizontal scheduling, lease fencing,
authorization, secure remote access, retention/deletion, backups and malicious-file isolation need
additional production design. The native demo inherits the host user's permissions; it does not claim
the optional Docker app's non-root/container isolation.
