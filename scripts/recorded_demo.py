"""Real OCR, worker, API and index; manually authored extraction and hash-vector doubles."""

import os
import threading
from pathlib import Path

import uvicorn
from app.config import Settings
from app.db import init_db
from app.main import create_app
from app.recorded import RecordedExtractor
from app.worker import Worker


def main():
    settings = Settings(
        data_dir=Path(os.environ.get("DEMO_DATA_DIR", "data/recorded")),
        extractor="recorded",
        embedding_mode="hash",
        ocr_provider="tesseract",
        allow_paid_ocr=False,
        weaviate_url=os.environ.get(
            "TEST_WEAVIATE_URL", f"http://127.0.0.1:{os.environ.get('VECTOR_PORT', '8097')}"
        ),
    )
    init_db(settings)
    worker = Worker(settings, extractor=RecordedExtractor())
    stop = threading.Event()

    def run():
        while not stop.is_set():
            if not worker.tick():
                stop.wait(0.2)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    try:
        uvicorn.run(
            create_app(settings),
            host="127.0.0.1",
            port=int(os.environ.get("APP_PORT", "8017")),
            access_log=False,
        )
    finally:
        stop.set()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
