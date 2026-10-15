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

Pending final stack and browser acceptance.
