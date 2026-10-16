from concurrent.futures import ThreadPoolExecutor

from app.db import connect
from app.main import create_app
from fastapi.testclient import TestClient


def test_upload_hash_dedup_and_traversal_safe(client, invoice_bytes, settings):
    first = client.post(
        "/api/documents", files={"file": ("../../bill.pdf", invoice_bytes, "application/pdf")}
    )
    assert first.status_code == 201
    data = first.json()
    assert data["document"]["filename"] == "bill.pdf"
    second = client.post("/api/documents", files={"file": ("renamed.pdf", invoice_bytes)})
    assert second.json()["duplicate"] is True
    assert second.json()["document"]["id"] == data["document"]["id"]
    assert len(client.get("/api/documents").json()) == 1
    assert not list((settings.data_dir / "incoming").iterdir())


def test_concurrent_uploads_converge(client, invoice_bytes):
    def upload(_):
        return client.post("/api/documents", files={"file": ("same.pdf", invoice_bytes)}).json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(upload, range(2)))
    assert len({r["document"]["id"] for r in results}) == 1
    assert sum(r["duplicate"] for r in results) == 1


def test_invalid_and_oversized_files(client, settings):
    assert client.post("/api/documents", files={"file": ("empty.pdf", b"")}).status_code == 422
    assert client.post("/api/documents", files={"file": ("fake.pdf", b"not a pdf")}).status_code == 422
    settings.max_upload_bytes = 10
    assert client.post("/api/documents", files={"file": ("huge.pdf", b"x" * 11)}).status_code == 413


def test_csrf_and_host_rejected(client):
    assert (
        client.post(
            "/api/ask", json={"question": "total?"}, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert client.get("/api/documents", headers={"Host": "evil.example"}).status_code == 400


def test_optional_token_protects_documents_and_images(settings, index):
    settings.access_token = "test-only-token"
    with TestClient(create_app(settings, index)) as client:
        assert client.get("/api/documents").status_code == 401
        assert client.post("/api/session", json={"token": "wrong"}).status_code == 401
        assert client.post("/api/session", json={"token": "test-only-token"}).status_code == 200
        assert client.get("/api/documents").status_code == 200
        assert "HttpOnly" in str(client.cookies) or client.cookies.get("evidence_session")


def test_unknown_id_and_question_limits(client):
    assert client.get("/api/documents/nope").status_code == 422
    assert client.get("/api/documents/00000000-0000-0000-0000-000000000000").status_code == 404
    assert client.post("/api/ask", json={"question": "x" * 1001}).status_code == 422
    assert client.post("/api/ask", json={"question": "What is the total?"}).json()["citations"] == []


def test_review_has_validation_audit_and_optimistic_concurrency(client, invoice_bytes, settings):
    doc = client.post("/api/documents", files={"file": ("bill.pdf", invoice_bytes)}).json()["document"]
    with connect(settings) as db:
        db.execute("UPDATE documents SET status='needs_review' WHERE id=?", (doc["id"],))
        db.execute(
            "INSERT INTO fields(document_id,name,value,confidence,quote,needs_review) VALUES(?,?,?,?,?,?)",
            (doc["id"], "total", "5.00", 0.4, "Total due: 5.00", 1),
        )
    url = f"/api/documents/{doc['id']}/fields/total"
    assert client.patch(url, json={"value": "NaN", "version": 1}).status_code == 422
    assert client.patch(url, json={"value": "2400.00", "version": 1}).status_code == 200
    assert client.patch(url, json={"value": "1.00", "version": 1}).status_code == 409
    detail = client.get(f"/api/documents/{doc['id']}").json()
    assert detail["status"] == "ready"
    assert detail["fields"][0]["confidence"] == 0.4
    assert detail["fields"][0]["reviewed"] == 1
    with connect(settings) as db:
        assert db.execute("SELECT old_value,new_value FROM review_events").fetchone()[:] == (
            "5.00",
            "2400.00",
        )
