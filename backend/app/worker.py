import json
import logging
import signal
import threading
import time

from app.config import Settings
from app.db import claim, connect, init_db
from app.extraction import Extraction, OllamaExtractor, merge_extractions, serialize_extraction
from app.ocr import make_ocr, render_page
from app.search import WeaviateIndex

logger = logging.getLogger(__name__)


class Worker:
    def __init__(self, settings: Settings, ocr=None, extractor=None, index=None):
        self.settings = settings
        self.ocr = ocr or make_ocr(settings)
        if settings.extractor != "ollama" and extractor is None:
            raise ValueError("Only local Ollama extraction is supported")
        self.extractor = extractor or OllamaExtractor(settings)
        self.index = index or WeaviateIndex(settings)

    def tick(self):
        doc = claim(self.settings)
        if not doc:
            return False
        heartbeat_stop = threading.Event()

        def heartbeat():
            while not heartbeat_stop.wait(20):
                with connect(self.settings) as db:
                    db.execute("UPDATE documents SET lease_until=? WHERE id=? AND status='processing'",
                               (time.time() + self.settings.lease_seconds, doc["id"]))

        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()
        try:
            self.process(doc)
        except Exception as exc:
            # Do not log exception messages: an SDK error can contain document data or credentials.
            code = type(exc).__name__
            logger.warning("job=%s attempt=%s error_type=%s", doc["id"], doc["attempts"], code)
            terminal = doc["attempts"] >= self.settings.max_attempts
            with connect(self.settings) as db:
                db.execute(
                    "UPDATE documents SET status=?,stage=?,error=?,available_at=?,lease_until=0 WHERE id=?",
                    ("failed" if terminal else "queued", "failed" if terminal else "retry_wait", code,
                     time.time() + 3 * 2 ** doc["attempts"], doc["id"]),
                )
        finally:
            heartbeat_stop.set()
            thread.join(timeout=2)
        return True

    def process(self, doc):
        folder = self.settings.data_dir / "documents" / doc["id"]
        for number in range(1, doc["page_count"] + 1):
            with connect(self.settings) as db:
                exists = db.execute("SELECT 1 FROM pages WHERE document_id=? AND number=?",
                                    (doc["id"], number)).fetchone()
            if exists:
                continue
            image = render_page(folder / "original", number)
            page = self.ocr.read(image, number)
            temporary = folder / f"page-{number}.tmp.png"
            image.save(temporary, format="PNG")
            temporary.replace(folder / f"page-{number}.png")
            image.close()
            with connect(self.settings) as db:
                db.execute("INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?)",
                           (doc["id"], number, page.text, json.dumps(page.words), page.width, page.height))
                db.execute("UPDATE documents SET processed_pages=?,stage='ocr' WHERE id=?", (number, doc["id"]))
        with connect(self.settings) as db:
            pages = [dict(row) for row in db.execute("SELECT * FROM pages WHERE document_id=? ORDER BY number",
                                                   (doc["id"],))]
            db.execute("UPDATE documents SET stage='extracting' WHERE id=?", (doc["id"],))
        for page in pages:
            page["words"] = json.loads(page["words"])
        extractions = []
        for offset in range(0, len(pages), 2):
            batch = offset // 2
            with connect(self.settings) as db:
                saved = db.execute("SELECT payload FROM extractions WHERE document_id=? AND batch=?",
                                   (doc["id"], batch)).fetchone()
            if saved:
                extraction = Extraction.model_validate_json(saved["payload"])
            else:
                extraction = self.extractor.extract(pages[offset:offset + 2])
                with connect(self.settings) as db:
                    db.execute("INSERT INTO extractions VALUES (?,?,?)",
                               (doc["id"], batch, serialize_extraction(extraction)))
            extractions.append(extraction)
        document_type, fields = merge_extractions(extractions, pages, self.settings)
        with connect(self.settings) as db:
            for field in fields:
                db.execute(
                    "INSERT OR IGNORE INTO fields(document_id,name,value,confidence,page,quote,boxes,needs_review) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (doc["id"], field["name"], field["value"], field["confidence"], field["page"], field["quote"],
                     json.dumps(field["boxes"]), field["needs_review"]),
                )
            db.execute("UPDATE documents SET stage='indexing',document_type=? WHERE id=?",
                       (document_type, doc["id"]))
        self.index.index(doc, pages)
        with connect(self.settings) as db:
            needs_review = db.execute("SELECT count(*) FROM fields WHERE document_id=? AND needs_review=1",
                                      (doc["id"],)).fetchone()[0]
            db.execute("UPDATE documents SET status=?,stage='complete',lease_until=0 WHERE id=?",
                       ("needs_review" if needs_review else "ready", doc["id"]))


def main():
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    init_db(settings)
    worker = Worker(settings)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    while not stop.is_set():
        if not worker.tick():
            stop.wait(1)


if __name__ == "__main__":
    main()
