"""Start a real local API/worker using recorded LLM responses; no model or cloud calls in CI."""
import json
import os
import threading
from pathlib import Path

import uvicorn
from app.config import Settings
from app.db import init_db
from app.extraction import Extraction
from app.main import create_app
from app.worker import Worker

ROOT = Path(__file__).resolve().parents[1]


class Recorded:
    def extract(self, pages):
        filename = "contract.json" if "AGREEMENT" in pages[0]["text"] else "invoice.json"
        return Extraction.model_validate(json.loads((ROOT / "fixtures" / "responses" / filename).read_text()))


def main():
    settings = Settings(data_dir=Path(os.environ.get("CI_DATA_DIR", "/tmp/evidence-ci")), embedding_mode="hash",
                        weaviate_url=os.environ.get("TEST_WEAVIATE_URL", "http://localhost:8096"))
    init_db(settings)
    worker = Worker(settings, extractor=Recorded())
    def run():
        while True:
            if not worker.tick():
                threading.Event().wait(0.2)
    threading.Thread(target=run, daemon=True).start()
    uvicorn.run(create_app(settings), host="127.0.0.1", port=8016, access_log=False)


if __name__ == "__main__":
    main()
