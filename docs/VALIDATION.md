# Acceptance evidence

This file is updated with observed results before delivery. The terminal acceptance artifact is
a successful browser flow, a live local-model extraction evaluation, and a green GitHub Actions run
at the committed repository SHA. Recorded-response CI and live-model validation are reported separately.

| Requirement | Evidence |
|---|---|
| Batch upload and visible processing | Browser upload/queue flow; asynchronous durable worker. |
| Hundreds of pages | 400-page input limit, bounded two-page model windows; bulk checkpoint test. No throughput SLA claimed. |
| No duplicates | Sequential and concurrent hash-dedup tests; duplicate upload in browser. |
| Real local OCR | Raster-only gold PDF tests through Tesseract; scan and multi-page PDF inputs. |
| LLM JSON and validation | Local Ollama adapter, strict Pydantic schema, source/type/score tests, live gold evaluation. |
| Human review | Missing/low/contradictory evidence tests, UI correction, optimistic concurrency and audit tests. |
| Weaviate citations | Real server upsert/hybrid test, browser answer and page navigation; no unsupported synthesis. |
| Reliability | Index failure with cached OCR/model recovery; crash lease and attempt limit tests. |
| Safety and cost | Fake-client Textract tests and default-deny paid gate; no paid APIs. |
| One-command launch | `scripts/start.sh` → Docker Compose; observed local smoke. |
| CI | Workflow URL and SHA recorded below after the run. |

## Observed results

WIP — Igor stopped implementation on 2026-10-16 to transfer it to the reviewed Claude Opus
delivery process. No claim of completed acceptance or permission to publish is made.

- Local Python: **23 passed, 1 skipped** (the real Weaviate integration requires its test URL).
  Ruff passed. The gold extraction tests used real Tesseract and explicitly recorded LLM responses.
- React/TypeScript build passed under the Studio wrapper. The application Docker image and the
  SHA-256-verified CPU-only Ollama image built successfully under a capped BuildKit service.
- `scripts/start.sh` completed successfully. API, Weaviate and Ollama were healthy; worker running.
  `GET /api/health` reported Tesseract / Ollama / FastEmbed; the document library was empty.
- Earlier GitHub Actions attempts completed the Python + real Weaviate step and the browser
  acceptance step, producing a screenshot and viewport video in private workflow artifacts.
  Some runs were subsequently cancelled by concurrency on newer pushes. This is not a claim that
  the final commit has a green completed workflow; the handoff records the observed run statuses.
- Live Ollama gold accuracy was **not measured**. The evaluation was cancelled while still
  queued on Studio. Local browser E2E and the manual recording were **not started**.
- The README screenshot target and the promised final demo recording are not committed artifacts
  yet. The manual run folder contains only a WIP report and pre-run scoped resource baselines.
