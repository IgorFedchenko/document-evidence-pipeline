"""Manually authored fixture responses for the explicitly labelled offline demo."""

import hashlib
from pathlib import Path

from app.extraction import Extraction

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def supported_digest(digest: str) -> bool:
    """Only byte-identical bundled documents belong to the recorded demo's scope."""
    return any(
        hashlib.sha256(path.read_bytes()).hexdigest() == digest
        for path in (FIXTURES / "documents").iterdir()
        if path.is_file()
    )


class RecordedExtractor:
    def extract(self, pages: list[dict]) -> Extraction:
        filename = "contract.json" if "AGREEMENT" in pages[0]["text"] else "invoice.json"
        return Extraction.model_validate_json((FIXTURES / "responses" / filename).read_text())
