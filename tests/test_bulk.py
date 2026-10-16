from app.db import connect
from app.extraction import Extraction
from app.ocr import OcrPage
from app.worker import Worker
from PIL import Image


def test_205_page_batch_checkpoints_and_bounded_model_windows(client, settings, index, tmp_path):
    """Queue/control-path scale check, not an OCR accuracy or inference throughput benchmark."""
    path = tmp_path / "205-pages.tiff"
    frames = [Image.new("RGB", (16, 16), (i % 255, 255, 255)) for i in range(205)]
    frames[0].save(path, save_all=True, append_images=frames[1:])
    response = client.post("/api/documents", files={"file": (path.name, path.read_bytes())})
    assert response.status_code == 201
    doc = response.json()["document"]
    assert doc["page_count"] == 205

    class Ocr:
        def read(self, image, number):
            return OcrPage(number, f"Synthetic page {number}", [], image.width, image.height)

    class Model:
        def __init__(self):
            self.batches = []

        def extract(self, pages):
            self.batches.append([p["number"] for p in pages])
            assert len(pages) <= 2
            return Extraction(document_type="unknown", fields=[])

    model = Model()
    Worker(settings, Ocr(), model, index).tick()
    final = client.get(f"/api/documents/{doc['id']}").json()
    assert final["processed_pages"] == 205
    assert final["status"] == "needs_review"
    assert len(model.batches) == 103
    assert model.batches[-1] == [205]
    with connect(settings) as db:
        assert db.execute("SELECT count(*) FROM pages").fetchone()[0] == 205
        assert db.execute("SELECT count(*) FROM extractions").fetchone()[0] == 103
