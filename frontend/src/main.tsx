import React, { useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowUpRight,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  FileText,
  FolderOpen,
  Layers3,
  Loader2,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import "./style.css";

import { api } from "./api";
import { FieldCard } from "./components/FieldCard";
import type { Answer, Document, ExtractedField } from "./types";

function App() {
  const [mode, setMode] = useState("Local workspace");
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selected, setSelected] = useState<Document | null>(null);
  const [page, setPage] = useState(1);
  const [focused, setFocused] = useState<string | null>(null);
  const [view, setView] = useState<"documents" | "review">("documents");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [uploading, setUploading] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [asking, setAsking] = useState(false);
  const [edit, setEdit] = useState("");
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const selectedId = useRef<string | null>(null);
  const reviewCount = documents.reduce(
    (n, d) => n + d.fields.filter((f) => f.needs_review).length,
    0,
  );
  const active = documents.filter((d) =>
    ["queued", "processing"].includes(d.status),
  );
  const machineEvidenceCount = documents
    .flatMap((d) => d.fields)
    .filter((f) => f.quote && f.boxes.length).length;

  const refresh = useCallback(async () => {
    try {
      const docs = await api<Document[]>("/documents");
      setDocuments(docs);
      if (selectedId.current) {
        const detail = await api<Document>(`/documents/${selectedId.current}`);
        if (selectedId.current === detail.id) setSelected(detail);
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);
  useEffect(() => {
    void api<{ extractor: string }>("/health")
      .then((health) =>
        setMode(
          health.extractor === "recorded"
            ? "Recorded fixture demo"
            : "Local model workspace",
        ),
      )
      .catch(() => {});
  }, []);
  useEffect(() => {
    void refresh();
    const timer = setInterval(refresh, 2000);
    return () => clearInterval(timer);
  }, [refresh]);

  async function openDocument(doc: Document, targetPage = 1) {
    selectedId.current = doc.id;
    setPage(targetPage);
    setFocused(null);
    try {
      setSelected(await api<Document>(`/documents/${doc.id}`));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function upload(files: FileList | null) {
    if (!files?.length) return;
    setUploading(true);
    setError("");
    setNotice("");
    let added = 0,
      duplicates = 0;
    try {
      for (const file of Array.from(files)) {
        const form = new FormData();
        form.append("file", file);
        const result = await api<{ document: Document; duplicate: boolean }>(
          "/documents",
          { method: "POST", body: form },
        );
        if (result.duplicate) duplicates++;
        else added++;
        if (!selectedId.current) await openDocument(result.document);
      }
      setNotice(
        `${added} document${added === 1 ? "" : "s"} queued${duplicates ? ` · ${duplicates} duplicate${duplicates === 1 ? "" : "s"} skipped` : ""}.`,
      );
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }
  function focusField(field: ExtractedField) {
    setFocused(field.name);
    setEdit(field.value || "");
    if (field.page) setPage(field.page);
  }
  async function saveReview(field: ExtractedField) {
    if (!selected) return;
    setBusy(true);
    try {
      await api(`/documents/${selected.id}/fields/${field.name}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: edit, version: field.version }),
      });
      setNotice(
        "Field verified. Your correction is saved in the review history.",
      );
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function ask(event: React.FormEvent) {
    event.preventDefault();
    if (!question.trim()) return;
    setAsking(true);
    setError("");
    try {
      setAnswer(
        await api<Answer>("/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question }),
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAsking(false);
    }
  }
  const currentField = selected?.fields.find((f) => f.name === focused);
  const visibleDocs =
    view === "review"
      ? documents.filter((d) => d.fields.some((f) => f.needs_review))
      : documents;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="Folio home">
          <div className="brand-mark">
            <Layers3 size={23} />
          </div>
          folio<span> / evidence</span>
        </a>
        <div className="workspace-label">YOUR WORKSPACE</div>
        <button
          className={`nav-item ${view === "documents" ? "active" : ""}`}
          onClick={() => setView("documents")}
        >
          <FolderOpen size={18} />
          Documents<span>{documents.length}</span>
        </button>
        <button
          className={`nav-item ${view === "review" ? "active" : ""}`}
          onClick={() => setView("review")}
        >
          <ShieldCheck size={18} />
          Review queue
          {reviewCount > 0 && <span className="count-warm">{reviewCount}</span>}
        </button>
        <div className="sidebar-bottom">
          <div className="privacy-icon">
            <ShieldCheck size={20} />
          </div>
          <strong>Your documents stay here.</strong>
          <p>
            Local OCR and evidence search. Trace fields and answers back to the
            page.
          </p>
          <div className="local-dot">Private local workspace</div>
        </div>
      </aside>
      <main>
        <header>
          <div className="breadcrumb">
            Workspace <span>/</span>{" "}
            {view === "documents" ? "Documents" : "Review queue"}
          </div>
          <span className="reference-badge">{mode.toUpperCase()}</span>
        </header>
        <div className="content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">FROM PAPER TO PROOF</div>
              <h1>
                {view === "documents"
                  ? "Every document. Every detail."
                  : "A second look, where it matters."}
              </h1>
              <p>
                Turn scanned pages into useful data — with the evidence
                attached.
              </p>
            </div>
            <button
              className="primary"
              onClick={() => fileInput.current?.click()}
              disabled={uploading}
            >
              {uploading ? (
                <Loader2 size={17} className="spin" />
              ) : (
                <Upload size={17} />
              )}{" "}
              Upload documents
            </button>
          </div>
          <input
            ref={fileInput}
            type="file"
            multiple
            accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff"
            aria-label="Upload files"
            hidden
            onChange={(e) => void upload(e.target.files)}
          />
          {error && (
            <div className="alert" role="alert">
              {error}
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          {error.includes("token") && (
            <form
              className="token-form"
              onSubmit={async (e) => {
                e.preventDefault();
                try {
                  await api("/session", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ token }),
                  });
                  setError("");
                  setToken("");
                  await refresh();
                } catch (e) {
                  setError((e as Error).message);
                }
              }}
            >
              <input
                type="password"
                aria-label="Access token"
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
              <button className="primary">Unlock workspace</button>
            </form>
          )}
          {notice && (
            <div className="notice" role="status">
              <Check size={16} />
              {notice}
              <button aria-label="Dismiss notice" onClick={() => setNotice("")}>
                <X size={16} />
              </button>
            </div>
          )}
          <div className="metrics">
            <div>
              <span className="metric-icon">
                <FileText size={19} />
              </span>
              <div>
                <strong>{documents.length.toString().padStart(2, "0")}</strong>
                <span>Documents</span>
              </div>
            </div>
            <div>
              <span className="metric-icon">
                <Layers3 size={19} />
              </span>
              <div>
                <strong>
                  {documents
                    .reduce((n, d) => n + d.processed_pages, 0)
                    .toString()
                    .padStart(2, "0")}
                </strong>
                <span>Pages processed</span>
              </div>
            </div>
            <div>
              <span className="metric-icon amber">
                <CircleHelp size={19} />
              </span>
              <div>
                <strong>{reviewCount.toString().padStart(2, "0")}</strong>
                <span>Fields to review</span>
              </div>
            </div>
            <div>
              <span className="metric-icon">
                <ShieldCheck size={19} />
              </span>
              <div>
                <strong>
                  {machineEvidenceCount.toString().padStart(2, "0")}
                </strong>
                <span title="Fields with original machine quotes and boxes; human edits are not re-grounded.">
                  Machine evidence
                </span>
              </div>
            </div>
          </div>
          <section
            className="document-section"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              void upload(e.dataTransfer.files);
            }}
          >
            <div className="section-title">
              <h2>
                {view === "review"
                  ? "Needs your attention"
                  : "Document library"}{" "}
                <span>{visibleDocs.length}</span>
              </h2>
              <span className="subtle">
                PDF, PNG, JPEG, TIFF · up to 400 pages per file
              </span>
            </div>
            {visibleDocs.length === 0 ? (
              <div className="empty">
                <div className="empty-icon">
                  <Upload size={25} />
                </div>
                <h3>
                  {view === "review"
                    ? "All caught up"
                    : "Give your documents a place to work."}
                </h3>
                <p>
                  {view === "review"
                    ? "Uncertain and missing fields will appear here."
                    : "Drop a batch here, or choose files to get started."}
                </p>
                {view === "documents" && (
                  <button
                    className="secondary"
                    onClick={() => fileInput.current?.click()}
                  >
                    Choose files <ArrowUpRight size={15} />
                  </button>
                )}
              </div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>DOCUMENT</th>
                      <th>TYPE</th>
                      <th>PAGES</th>
                      <th>STATUS</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleDocs.map((doc) => (
                      <tr
                        key={doc.id}
                        className={
                          selected?.id === doc.id ? "selected-row" : ""
                        }
                      >
                        <td>
                          <button
                            className="doc-button"
                            onClick={() => void openDocument(doc)}
                          >
                            <span className="file-icon">
                              <FileText size={20} />
                            </span>
                            <div>
                              <strong>{doc.filename}</strong>
                              <small>
                                {doc.fields.length
                                  ? `${doc.fields.length} extracted fields`
                                  : doc.stage === "extracting"
                                    ? `Extracting ${doc.extracted_pages} / ${doc.page_count} pages…`
                                    : "Preparing your document"}
                              </small>
                            </div>
                          </button>
                        </td>
                        <td>
                          <span className="type-tag">{doc.document_type}</span>
                        </td>
                        <td>
                          {doc.processed_pages}
                          <span className="muted"> / {doc.page_count}</span>
                        </td>
                        <td>
                          <span className={`status ${doc.status}`}>
                            <i />
                            {
                              (
                                {
                                  queued: "Queued",
                                  processing:
                                    doc.stage === "extracting"
                                      ? "Extracting"
                                      : doc.stage === "indexing"
                                        ? "Indexing"
                                        : "Reading pages",
                                  needs_review: "Needs review",
                                  ready: "Ready",
                                  failed: "Failed",
                                } as Record<string, string>
                              )[doc.status]
                            }
                          </span>
                          {["queued", "processing"].includes(doc.status) && (
                            <progress
                              value={doc.processed_pages}
                              max={doc.page_count}
                            />
                          )}
                        </td>
                        <td>
                          {doc.status === "failed" ? (
                            <button
                              className="text-button"
                              onClick={async () => {
                                try {
                                  await api(`/documents/${doc.id}/retry`, {
                                    method: "POST",
                                  });
                                  await refresh();
                                } catch (e) {
                                  setError((e as Error).message);
                                }
                              }}
                            >
                              Retry
                            </button>
                          ) : (
                            <button
                              className="icon-button"
                              aria-label={`Open ${doc.filename}`}
                              onClick={() => void openDocument(doc)}
                            >
                              <ArrowUpRight size={18} />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {active.length > 0 && (
              <div className="queue-status">
                <Loader2 size={14} className="spin" />
                {active.length} document{active.length === 1 ? "" : "s"} in the
                processing queue. You can keep working.
              </div>
            )}
          </section>
          <div className="work-area">
            <section className="review-panel">
              <div className="section-title">
                <h2>{selected ? selected.filename : "Document inspector"}</h2>
                {selected && (
                  <span className="subtle">{selected.document_type}</span>
                )}
              </div>
              {!selected ? (
                <div className="inspector-empty">
                  <FileText size={30} />
                  <h3>The details are in the document.</h3>
                  <p>
                    Select a file to inspect extracted fields
                    <br />
                    and see exactly where they came from.
                  </p>
                </div>
              ) : (
                <>
                  <div className="review-layout">
                    <div className="page-viewer">
                      <div className="page-toolbar">
                        <span>SOURCE DOCUMENT</span>
                        <div>
                          <button
                            aria-label="Previous page"
                            disabled={page <= 1}
                            onClick={() => {
                              setPage((p) => p - 1);
                              setFocused(null);
                            }}
                          >
                            <ChevronLeft size={16} />
                          </button>
                          <span>
                            Page {page} of {selected.page_count}
                          </span>
                          <button
                            aria-label="Next page"
                            disabled={page >= selected.page_count}
                            onClick={() => {
                              setPage((p) => p + 1);
                              setFocused(null);
                            }}
                          >
                            <ChevronRight size={16} />
                          </button>
                        </div>
                      </div>
                      {selected.pages?.some((p) => p.number === page) ? (
                        <div className="paper">
                          <img
                            src={`/api/documents/${selected.id}/pages/${page}/image`}
                            alt={`Source page ${page} of ${selected.filename}`}
                          />
                          {currentField?.page === page &&
                            currentField.boxes.map((box, i) => (
                              <span
                                key={i}
                                className="highlight"
                                style={{
                                  left: `${box[0] * 100}%`,
                                  top: `${box[1] * 100}%`,
                                  width: `${box[2] * 100}%`,
                                  height: `${box[3] * 100}%`,
                                }}
                              />
                            ))}
                        </div>
                      ) : (
                        <div className="page-pending">
                          <Loader2 className="spin" />
                          <p>This page is waiting for OCR.</p>
                        </div>
                      )}
                    </div>
                    <div className="fields-panel">
                      <div className="fields-heading">
                        EXTRACTED FIELDS <span>Click to locate source</span>
                      </div>
                      {selected.fields.length === 0 ? (
                        <p className="subtle">
                          Fields appear after extraction completes.
                        </p>
                      ) : (
                        selected.fields.map((field) => (
                          <FieldCard
                            key={field.name}
                            field={field}
                            focused={focused === field.name}
                            edit={edit}
                            busy={busy}
                            canReview={["ready", "needs_review"].includes(
                              selected.status,
                            )}
                            onFocus={() => focusField(field)}
                            onEdit={setEdit}
                            onSave={() => void saveReview(field)}
                          />
                        ))
                      )}
                    </div>
                  </div>
                  {selected.error && (
                    <div className="alert">
                      Processing error: {selected.error}. Check local services,
                      then retry.
                    </div>
                  )}
                </>
              )}
            </section>
            <section className="search-panel">
              <div className="search-title">
                <span className="spark-icon">
                  <Sparkles size={18} />
                </span>
                <h2>Ask your documents</h2>
              </div>
              <p className="search-intro">
                Find the answer. Keep the evidence.
              </p>
              <form onSubmit={ask}>
                <label htmlFor="question">What would you like to know?</label>
                <textarea
                  id="question"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="What is the total amount on the invoice?"
                  rows={3}
                />
                <button
                  className="primary"
                  disabled={asking || !question.trim()}
                >
                  {asking ? (
                    <Loader2 size={16} className="spin" />
                  ) : (
                    <Search size={16} />
                  )}{" "}
                  Find evidence
                </button>
              </form>
              {answer ? (
                <div className="answer">
                  <div className="answer-label">EVIDENCE-BASED ANSWER</div>
                  {answer.citations.length ? (
                    answer.citations.map((c) => (
                      <div className="citation" key={c.id}>
                        <p>“{c.quote}”</p>
                        <button
                          onClick={() => {
                            const doc = documents.find(
                              (d) => d.id === c.document_id,
                            );
                            if (doc) void openDocument(doc, c.page);
                          }}
                        >
                          <FileText size={13} />[{c.id}] {c.filename} · p.{" "}
                          {c.page}
                          <ArrowUpRight size={13} />
                        </button>
                      </div>
                    ))
                  ) : (
                    <p>{answer.answer}</p>
                  )}
                  <small>
                    Exact source excerpts. Always verify against the original
                    page.
                  </small>
                </div>
              ) : (
                <div className="search-hint">
                  <ShieldCheck size={17} />
                  <p>
                    Answers cite the document and page. If there is no
                    supporting evidence, we say so.
                  </p>
                </div>
              )}
            </section>
          </div>
          <footer>
            <span>Folio / Document Evidence Pipeline</span>
            <span>Synthetic demo data only · Built for traceability</span>
          </footer>
        </div>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
