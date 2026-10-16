import json
import sqlite3
import time
from contextlib import contextmanager

from app.config import Settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
 id TEXT PRIMARY KEY, sha256 TEXT NOT NULL UNIQUE, filename TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'queued', stage TEXT NOT NULL DEFAULT 'queued',
 page_count INTEGER NOT NULL, processed_pages INTEGER NOT NULL DEFAULT 0,
 attempts INTEGER NOT NULL DEFAULT 0, available_at REAL NOT NULL DEFAULT 0,
 lease_until REAL NOT NULL DEFAULT 0, error TEXT, created_at REAL NOT NULL,
 document_type TEXT NOT NULL DEFAULT 'unknown'
);
CREATE TABLE IF NOT EXISTS pages (
 document_id TEXT NOT NULL REFERENCES documents(id), number INTEGER NOT NULL,
 text TEXT NOT NULL, words TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL,
 PRIMARY KEY(document_id, number)
);
CREATE TABLE IF NOT EXISTS extractions (
 document_id TEXT NOT NULL REFERENCES documents(id), batch INTEGER NOT NULL,
 payload TEXT NOT NULL, PRIMARY KEY(document_id,batch)
);
CREATE TABLE IF NOT EXISTS fields (
 document_id TEXT NOT NULL REFERENCES documents(id), name TEXT NOT NULL,
 value TEXT, confidence REAL NOT NULL, page INTEGER, quote TEXT NOT NULL,
 boxes TEXT NOT NULL DEFAULT '[]', needs_review INTEGER NOT NULL,
 reviewed INTEGER NOT NULL DEFAULT 0, version INTEGER NOT NULL DEFAULT 1,
 PRIMARY KEY(document_id,name)
);
CREATE TABLE IF NOT EXISTS review_events (
 id INTEGER PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
 field_name TEXT NOT NULL, old_value TEXT, new_value TEXT, created_at REAL NOT NULL
);
"""


@contextmanager
def connect(settings: Settings):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(settings.database, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def init_db(settings: Settings):
    with connect(settings) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript(SCHEMA)


def claim(settings: Settings):
    now = time.time()
    with connect(settings) as db:
        db.execute("BEGIN IMMEDIATE")
        # A crash on the last attempt must become visible, not remain stuck forever.
        db.execute(
            "UPDATE documents SET status='failed',stage='failed',error='Worker lease expired' "
            "WHERE status='processing' AND lease_until<? AND attempts>=?",
            (now, settings.max_attempts),
        )
        row = db.execute(
            "SELECT * FROM documents WHERE "
            "((status='queued' AND available_at<=?) OR (status='processing' AND lease_until<?)) "
            "AND attempts<? ORDER BY created_at LIMIT 1",
            (now, now, settings.max_attempts),
        ).fetchone()
        if not row:
            return None
        db.execute(
            "UPDATE documents SET status='processing',stage='ocr',attempts=attempts+1,"
            "lease_until=?,error=NULL WHERE id=?",
            (now + settings.lease_seconds, row["id"]),
        )
        return dict(db.execute("SELECT * FROM documents WHERE id=?", (row["id"],)).fetchone())


def document_view(db, doc):
    result = dict(doc)
    completed = db.execute("SELECT count(*) FROM extractions WHERE document_id=?", (doc["id"],)).fetchone()[0]
    result["extracted_pages"] = min(completed * 2, doc["page_count"])
    result["fields"] = []
    for row in db.execute("SELECT * FROM fields WHERE document_id=? ORDER BY name", (doc["id"],)):
        field = dict(row)
        field["boxes"] = json.loads(field["boxes"])
        result["fields"].append(field)
    return result
