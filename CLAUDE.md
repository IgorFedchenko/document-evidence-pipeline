# Document Evidence Pipeline

Independent MIT reference implementation. Use synthetic fixtures only. Never copy employer/client code,
documents or names. Keep GitHub private until Igor explicitly approves public visibility.

Run `uv run pytest`, `uv run ruff check .`, and frontend build; use `scripts/verify.sh` for the terminal
acceptance flow. On Studio, every build, Docker job and browser E2E must run through
`~/.local/bin/studio-heavy-run -- <command>`. Do not interrupt other queue occupants.

No paid services, cloud OCR calls or LLM API keys without Igor's prior approval. Ollama and local
embeddings are free local inference. Textract is an opt-in adapter, unit tested with fake clients.
Do not read Upwork messages or use any writing Upwork tool as part of this project.

Canonical durable instructions belong here, not in an independent AGENTS.md.
