# Key decisions

## Evidence before convenience

Constrained JSON is followed by independent type and OCR-source checks. A model's confidence does not
establish correctness. Unsupported candidates stay visible for review with cleared evidence and zero
score. This avoids silently accepting a plausible answer, while preserving information for a reviewer.

Human correction changes the saved value and creates an audit event. Original machine provenance stays
attached and is explicitly labelled; it must not imply that a newly typed value occurs in the scan.
Optimistic versions prevent two reviewers from silently overwriting one another.

## Recorded default, explicit model opt-in

The default run should demonstrate the application without model downloads, API keys or cloud services.
Authored fixture responses and deterministic hash vectors make that flow repeatable. Real OCR, database,
worker, search server and browser are retained. Restricting recorded uploads to bundled bytes keeps the
boundary honest. The tradeoff is narrow supported input and no measure of model extraction quality.

The historical real-model development slice is disclosed separately: 11/13 expected fields, both invoice
dates missing, and an invalid contract duration-as-date candidate flagged by validation. Its stricter
feasibility gate failed; the final recorded browser check does not change that result.

## Local durable queue and rebuildable index

SQLite keeps upload metadata, job state, OCR, extraction batches, fields and review events together.
Atomic claims, leases and checkpoints keep restart behavior understandable without a separate queue
service. Weaviate is derived search state, with deterministic IDs for retry-safe upserts. This is a
small local system; it deliberately stops short of distributed lease fencing and multitenant scheduling.

## Extractive API answers

The API uses lexical overlap to select exact OCR lines after hybrid retrieval. Every excerpt has a
page citation, but lexical overlap can select the wrong passage or miss a paraphrase. The standalone
model selector remains an experimental adapter, not a deployed answer path. Keeping those modes
separate prevents a successful adapter experiment from becoming an unsupported UI claim.

## Reproducible local acceptance

One verification coordinator runs Python and browser stages sequentially, each with fresh app data and
a uniquely named temporary search server. Each stage takes its own host queue ticket, builds the frontend,
runs one suite and finishes cleanup before releasing its slot. No services remain between tickets.
Raw logs and recordings stay outside the repository. The selected screenshot/GIF
contain only synthetic data. Private hosted Actions are disabled; acceptance is reproduced locally.
