import json
from pathlib import Path

import pytest
from app.config import Settings
from app.db import init_db
from app.extraction import Extraction
from app.main import create_app
from fastapi.testclient import TestClient

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


class MemoryIndex:
    def __init__(self):
        self.rows = []

    def index(self, doc, pages):
        self.rows = [
            {
                "documentId": doc["id"],
                "filename": doc["filename"],
                "page": p["number"],
                "text": p["text"],
                "_additional": {"score": 1},
            }
            for p in pages
        ]

    def search(self, question):
        return self.rows


class RecordedExtractor:
    def __init__(self, filename="invoice.json"):
        self.filename = filename
        self.calls = 0

    def extract(self, pages):
        self.calls += 1
        return Extraction.model_validate(json.loads((FIXTURES / "responses" / self.filename).read_text()))


@pytest.fixture
def settings(tmp_path):
    result = Settings(data_dir=tmp_path, embedding_mode="hash", max_attempts=2)
    init_db(result)
    return result


@pytest.fixture
def index():
    return MemoryIndex()


@pytest.fixture
def client(settings, index):
    with TestClient(create_app(settings, index)) as result:
        yield result


@pytest.fixture
def invoice_bytes():
    return (FIXTURES / "documents" / "synthetic-invoice.pdf").read_bytes()
