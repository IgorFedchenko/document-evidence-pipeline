from app.main import create_app
from conftest import FIXTURES
from fastapi.testclient import TestClient


def test_recorded_mode_reports_doubles_and_restricts_fixture_scope(settings, index, invoice_bytes):
    settings.extractor = "recorded"
    with TestClient(create_app(settings, index)) as client:
        health = client.get("/api/health").json()
        assert health["extractor"] == "recorded"
        assert health["embeddings"] == "hash"
        assert health["ocr"] == "tesseract"
        assert (
            client.post("/api/documents", files={"file": ("invoice.pdf", invoice_bytes)}).status_code == 201
        )
        # A valid PDF outside the recorded set must never receive a plausible fixture response.
        modified = invoice_bytes + b"\n% another document\n"
        response = client.post("/api/documents", files={"file": ("other.pdf", modified)})
        assert response.status_code == 422
        assert "bundled synthetic" in response.json()["detail"]
        assert len(client.get("/api/documents").json()) == 1
    assert not list((settings.data_dir / "incoming").iterdir())


def test_recorded_contract_response_uses_real_ocr(settings):
    from app.db import connect
    from app.recorded import RecordedExtractor
    from app.worker import Worker
    from conftest import MemoryIndex

    settings.extractor = "recorded"
    index = MemoryIndex()
    with TestClient(create_app(settings, index)) as client:
        response = client.post(
            "/api/documents",
            files={
                "file": ("contract.pdf", (FIXTURES / "documents" / "synthetic-contract.pdf").read_bytes())
            },
        )
        doc_id = response.json()["document"]["id"]
        assert Worker(settings, extractor=RecordedExtractor(), index=index).tick()
        doc = client.get(f"/api/documents/{doc_id}").json()
        assert doc["status"] in {"ready", "needs_review"}
        assert doc["document_type"] == "contract"
        total = next(field for field in doc["fields"] if field["name"] == "total")
        assert total["value"] == "7500.00" and total["boxes"]
        with connect(settings) as db:
            assert db.execute("SELECT count(*) FROM pages").fetchone()[0] == 2
