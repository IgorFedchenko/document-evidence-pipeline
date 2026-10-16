"""Evaluate local OCR + live Ollama + real Weaviate on synthetic gold files only."""

import argparse
import json
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8016")
    parser.add_argument("--output", default="docs/live-evaluation.json")
    args = parser.parse_args()
    expected = json.loads((ROOT / "fixtures" / "expected.json").read_text())
    results = []
    with httpx.Client(base_url=args.url, timeout=90) as client:
        health = client.get("/api/health").json()
        assert health["extractor"] == "ollama" and health["embeddings"] == "fastembed", health
        for filename, gold in expected.items():
            start = time.monotonic()
            path = ROOT / "fixtures" / "documents" / filename
            response = client.post(
                "/api/documents", files={"file": (filename, path.read_bytes(), "application/pdf")}
            )
            response.raise_for_status()
            doc_id = response.json()["document"]["id"]
            deadline = time.monotonic() + 840
            while time.monotonic() < deadline:
                response = client.get(f"/api/documents/{doc_id}")
                response.raise_for_status()
                document = response.json()
                if document["status"] in {"ready", "needs_review", "failed"}:
                    break
                time.sleep(2)
            else:
                raise RuntimeError(f"Timed out waiting for {filename}")
            if document["status"] == "failed":
                raise RuntimeError(f"{filename}: {document['error']}")
            actual = {f["name"]: f["value"] for f in document["fields"]}
            correct = sum(actual.get(name) == value for name, value in gold["fields"].items())
            grounded = sum(bool(f["quote"] and f["boxes"]) for f in document["fields"] if f["value"])
            result = {
                "fixture": filename,
                "document_id": doc_id,
                "state": document["status"],
                "seconds": round(time.monotonic() - start, 2),
                "correct_fields": correct,
                "expected_fields": len(gold["fields"]),
                "grounded_fields": grounded,
                "review_fields": sum(f["needs_review"] for f in document["fields"]),
                "actual": actual,
            }
            results.append(result)
            print(json.dumps(result), flush=True)
        response = client.post("/api/ask", json={"question": "What is the total due on the invoice?"})
        response.raise_for_status()
        answer = response.json()
        assert answer["citations"], "No source citations returned"
        for citation in answer["citations"]:
            source = client.get(f"/api/documents/{citation['document_id']}").json()
            page = next(p for p in source["pages"] if p["number"] == citation["page"])
            assert " ".join(citation["quote"].split()) in " ".join(page["text"].split())
    output = {
        "mode": "live local Ollama + Tesseract + BGE + Weaviate",
        "health": health,
        "documents": results,
        "citation_count": len(answer["citations"]),
        "field_accuracy": sum(r["correct_fields"] for r in results)
        / sum(r["expected_fields"] for r in results),
    }
    (ROOT / args.output).write_text(json.dumps(output, indent=2) + "\n")
    # Grounding is a terminal check; live model accuracy is measured, not silently assumed perfect.
    assert all(r["grounded_fields"] > 0 for r in results)


if __name__ == "__main__":
    main()
