import hashlib
import hmac
import json
import shutil
import sqlite3
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import Settings
from app.db import connect, document_view, init_db
from app.extraction import validate_value
from app.ocr import inspect_file
from app.search import WeaviateIndex, evidence_answer


class Question(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


class Review(BaseModel):
    value: str = Field(min_length=1, max_length=500)
    version: int = Field(ge=1)


class Login(BaseModel):
    token: str = Field(max_length=500)


def create_app(settings: Settings | None = None, index=None):
    settings = settings or Settings()
    index = index or WeaviateIndex(settings)

    @asynccontextmanager
    async def lifespan(app):
        init_db(settings)
        yield

    app = FastAPI(title="Document Evidence Pipeline", version="0.1.0", lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])

    @app.middleware("http")
    async def security(request: Request, call_next):
        # Same-origin browser requests only; no wildcard CORS. Deny CSRF on local unauthed installs too.
        origin = request.headers.get("origin")
        if request.method not in {"GET", "HEAD", "OPTIONS"} and origin:
            if origin != f"{request.url.scheme}://{request.headers.get('host')}":
                return Response("Origin rejected", status_code=403)
        if request.url.path.startswith("/api/") and request.url.path not in {"/api/health", "/api/session"}:
            if settings.access_token:
                supplied = request.cookies.get("evidence_session", "") or request.headers.get("x-access-token", "")
                if not hmac.compare_digest(supplied, settings.access_token):
                    return Response("Access token required", status_code=401)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' blob:; style-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; frame-ancestors 'none'; object-src 'none'"
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.1.0", "extractor": settings.extractor,
                "embeddings": settings.embedding_mode, "ocr": settings.ocr_provider}

    @app.post("/api/session")
    def login(body: Login, response: Response):
        if settings.access_token and not hmac.compare_digest(body.token, settings.access_token):
            raise HTTPException(401, "Invalid access token")
        response.set_cookie("evidence_session", body.token, httponly=True, samesite="strict", max_age=28800)
        return {"ok": True}

    @app.get("/api/documents")
    def documents():
        with connect(settings) as db:
            return [document_view(db, row) for row in db.execute("SELECT * FROM documents ORDER BY created_at DESC LIMIT 1000")]

    @app.post("/api/documents", status_code=201)
    def upload(file: UploadFile):
        incoming = settings.data_dir / "incoming"
        incoming.mkdir(parents=True, exist_ok=True)
        digest, length = hashlib.sha256(), 0
        with tempfile.NamedTemporaryFile(dir=incoming, delete=False) as tmp:
            path = Path(tmp.name)
            try:
                while chunk := file.file.read(1024 * 1024):
                    length += len(chunk)
                    if length > settings.max_upload_bytes:
                        raise HTTPException(413, "File exceeds the 30 MB limit")
                    digest.update(chunk)
                    tmp.write(chunk)
                tmp.flush()
                if length == 0:
                    raise HTTPException(422, "Empty file")
                sha = digest.hexdigest()
                with connect(settings) as db:
                    existing = db.execute("SELECT * FROM documents WHERE sha256=?", (sha,)).fetchone()
                    if existing:
                        return {"document": document_view(db, existing), "duplicate": True}
                try:
                    count = inspect_file(path, settings)
                except Exception as exc:
                    raise HTTPException(422, "Unreadable, encrypted, oversized or unsupported document") from exc
                doc_id = str(uuid.uuid4())
                folder = settings.data_dir / "documents" / doc_id
                folder.mkdir(parents=True)
                shutil.copyfile(path, folder / "original")
                filename = Path(file.filename or "document").name[:180]
                try:
                    with connect(settings) as db:
                        db.execute("BEGIN IMMEDIATE")
                        if db.execute("SELECT count(*) FROM documents").fetchone()[0] >= settings.max_documents:
                            raise HTTPException(429, "Local document quota reached")
                        db.execute(
                            "INSERT INTO documents(id,sha256,filename,page_count,created_at) VALUES (?,?,?,?,?)",
                            (doc_id, sha, filename, count, time.time()),
                        )
                        doc = document_view(db, db.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone())
                except sqlite3.IntegrityError:
                    shutil.rmtree(folder)
                    with connect(settings) as db:
                        existing = db.execute("SELECT * FROM documents WHERE sha256=?", (sha,)).fetchone()
                        if existing:
                            return {"document": document_view(db, existing), "duplicate": True}
                    raise
                except BaseException:
                    shutil.rmtree(folder)
                    raise
                return {"document": doc, "duplicate": False}
            finally:
                path.unlink(missing_ok=True)
                file.file.close()

    @app.get("/api/documents/{doc_id}")
    def document(doc_id: uuid.UUID):
        with connect(settings) as db:
            row = db.execute("SELECT * FROM documents WHERE id=?", (str(doc_id),)).fetchone()
            if row is None:
                raise HTTPException(404, "Document not found")
            result = document_view(db, row)
            result["pages"] = [{**dict(page), "words": json.loads(page["words"])} for page in
                               db.execute("SELECT * FROM pages WHERE document_id=? ORDER BY number", (str(doc_id),))]
            return result

    @app.get("/api/documents/{doc_id}/pages/{number}/image")
    def page_image(doc_id: uuid.UUID, number: int):
        if not 1 <= number <= settings.max_pages:
            raise HTTPException(404, "Page not found")
        path = settings.data_dir / "documents" / str(doc_id) / f"page-{number}.png"
        if not path.is_file():
            raise HTTPException(404, "Page is not processed yet")
        return FileResponse(path, media_type="image/png")

    @app.post("/api/documents/{doc_id}/retry")
    def retry(doc_id: uuid.UUID):
        with connect(settings) as db:
            changed = db.execute("UPDATE documents SET status='queued',stage='queued',attempts=0,available_at=0,error=NULL "
                                 "WHERE id=? AND status='failed'", (str(doc_id),)).rowcount
            if not changed:
                raise HTTPException(409, "Only failed documents can be retried")
        return {"ok": True}

    @app.patch("/api/documents/{doc_id}/fields/{name}")
    def review(doc_id: uuid.UUID, name: str, body: Review):
        try:
            validate_value(name, body.value)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        with connect(settings) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT fields.*,documents.status FROM fields JOIN documents ON documents.id=fields.document_id "
                             "WHERE document_id=? AND name=?", (str(doc_id), name)).fetchone()
            if not row:
                raise HTTPException(404, "Field not found")
            if row["status"] not in {"ready", "needs_review"}:
                raise HTTPException(409, "Wait until processing completes")
            if row["version"] != body.version:
                raise HTTPException(409, "Field changed; reload before reviewing")
            db.execute("INSERT INTO review_events(document_id,field_name,old_value,new_value,created_at) VALUES(?,?,?,?,?)",
                       (str(doc_id), name, row["value"], body.value, time.time()))
            # Confidence and evidence remain machine provenance, not a fabricated 100% score.
            db.execute("UPDATE fields SET value=?,needs_review=0,reviewed=1,version=version+1 WHERE document_id=? AND name=?",
                       (body.value, str(doc_id), name))
            remaining = db.execute("SELECT count(*) FROM fields WHERE document_id=? AND needs_review=1", (str(doc_id),)).fetchone()[0]
            db.execute("UPDATE documents SET status=? WHERE id=?", ("needs_review" if remaining else "ready", str(doc_id)))
        return {"ok": True}

    @app.post("/api/ask")
    def ask(body: Question):
        with connect(settings) as db:
            allowed = {row[0] for row in db.execute("SELECT id FROM documents WHERE status IN ('ready','needs_review')")}
        if not allowed:
            return evidence_answer(body.question, [], allowed)
        try:
            hits = index.search(body.question)
        except Exception as exc:
            raise HTTPException(503, "Search unavailable; verify the Weaviate service") from exc
        return evidence_answer(body.question, hits, allowed)

    static = Path(__file__).resolve().parents[2] / "static"
    if not static.exists():
        static = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if static.exists():
        app.mount("/", StaticFiles(directory=static, html=True), name="frontend")
    return app


app = create_app()
