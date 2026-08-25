import { useState } from "react";
import UploadPanel from "./UploadPanel";
import { type DocumentRecord, type ChatMode } from "../lib/api";

type DocumentsPanelProps = {
  documents: DocumentRecord[];
  activeDocument: DocumentRecord | null;
  onSelectDocument: (doc: DocumentRecord | null) => void;
  onDeleteDocument: (id: string) => Promise<void>;
  onUploaded: (document: DocumentRecord) => void;
  onNavigateToChat: (mode?: ChatMode) => void;
};

export default function DocumentsPanel({
  documents,
  activeDocument,
  onSelectDocument,
  onDeleteDocument,
  onUploaded,
  onNavigateToChat,
}: DocumentsPanelProps) {
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const readyDocs = documents.filter((d) => d.status === "ready");
  const totalChunks = readyDocs.reduce((acc, d) => acc + d.chunk_count, 0);

  async function handleDelete(id: string) {
    setDeletingId(id);
    try {
      await onDeleteDocument(id);
    } finally {
      setDeletingId(null);
      setConfirmDeleteId(null);
    }
  }

  function getStatusBadge(status: string) {
    switch (status) {
      case "ready":
        return <span className="badge badge-success"><span className="badge-dot" aria-hidden="true"></span> Ready</span>;
      case "processing":
        return <span className="badge badge-warning"><span className="spinner-mini" aria-hidden="true"></span> Indexing</span>;
      case "failed":
        return <span className="badge badge-danger"><span className="badge-dot" aria-hidden="true"></span> Failed</span>;
      default:
        return <span className="badge badge-count">{status}</span>;
    }
  }

  return (
    <div className="stack-lg">
      <div className="grid-split">
        {/* Upload Form Card */}
        <UploadPanel onUploaded={onUploaded} />

        {/* Overview Stats Card */}
        <div className="card overview-card stack">
          <div className="section-heading">
            <span className="eyebrow">Vector Knowledge Base</span>
            <h2>Knowledge Base Overview</h2>
            <p className="muted">All uploaded study materials are indexed into FAISS vector embeddings.</p>
          </div>

          <div className="stats-grid">
            <div className="stat-box">
              <span className="stat-number">{documents.length}</span>
              <span className="stat-label">Total Files</span>
            </div>
            <div className="stat-box">
              <span className="stat-number">{readyDocs.length}</span>
              <span className="stat-label">Ready</span>
            </div>
            <div className="stat-box">
              <span className="stat-number">{totalChunks}</span>
              <span className="stat-label">Vector Chunks</span>
            </div>
          </div>

          <div className="overview-actions">
            {activeDocument ? (
              <div className="active-focus-banner">
                <span>🎯 Active Focus: <strong>{activeDocument.filename}</strong></span>
                <button
                  type="button"
                  className="btn-action"
                  onClick={() => onSelectDocument(null)}
                >
                  Clear Selection
                </button>
              </div>
            ) : (
              <button
                type="button"
                className="chip chip-lg"
                onClick={() => onSelectDocument(null)}
              >
                🌐 Scope: Searching across all {readyDocs.length} ready documents
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Indexed Documents Library Grid */}
      <section className="card library-card" aria-label="Indexed Documents Library">
        <div className="library-header">
          <div>
            <h3>Indexed Documents Library</h3>
            <p className="muted">Manage your uploaded materials, select active context, or remove old files.</p>
          </div>
          <span className="badge badge-count">{documents.length} document{documents.length === 1 ? "" : "s"}</span>
        </div>

        {documents.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon" aria-hidden="true">📂</span>
            <h4>No documents uploaded yet</h4>
            <p className="muted">Upload your first PDF, lecture slides, or notes above to begin studying.</p>
          </div>
        ) : (
          <div className="document-grid">
            {documents.map((doc) => {
              const isSelected = activeDocument?.id === doc.id;
              const isDeleting = deletingId === doc.id;

              return (
                <article
                  key={doc.id}
                  className={`doc-card ${isSelected ? "doc-card-active" : ""}`}
                >
                  <div className="doc-card-header">
                    <div className="doc-type-icon" aria-hidden="true">
                      {doc.filename.endsWith(".pdf") ? "📕" : doc.filename.endsWith(".txt") ? "📝" : "🖼️"}
                    </div>
                    <div className="doc-title-box">
                      <h4 className="doc-title" title={doc.filename}>{doc.filename}</h4>
                      <span className="doc-time">
                        {new Date(doc.created_at).toLocaleDateString()} at {new Date(doc.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                  </div>

                  <div className="doc-badges">
                    {getStatusBadge(doc.status)}
                    {doc.chunk_count > 0 && (
                      <span className="badge badge-primary">{doc.chunk_count} chunks</span>
                    )}
                  </div>

                  {doc.error_message && (
                    <p className="doc-error-msg" role="alert">⚠️ {doc.error_message}</p>
                  )}

                  <div className="doc-card-footer">
                    <div className="doc-main-actions">
                      <button
                        type="button"
                        className={`btn-action ${isSelected ? "btn-action-active" : ""}`}
                        onClick={() => {
                          onSelectDocument(isSelected ? null : doc);
                          onNavigateToChat("explain");
                        }}
                        disabled={doc.status !== "ready"}
                        aria-label={`Ask questions about ${doc.filename}`}
                      >
                        💬 Chat
                      </button>
                      <button
                        type="button"
                        className="btn-action"
                        onClick={() => {
                          onSelectDocument(doc);
                          onNavigateToChat("quiz");
                        }}
                        disabled={doc.status !== "ready"}
                        aria-label={`Generate quiz from ${doc.filename}`}
                      >
                        🎯 Quiz
                      </button>
                    </div>

                    {confirmDeleteId === doc.id ? (
                      <div className="confirm-delete-row">
                        <span className="confirm-label">Delete?</span>
                        <button
                          type="button"
                          className="btn-delete-confirm"
                          onClick={() => handleDelete(doc.id)}
                          disabled={isDeleting}
                          aria-label={`Confirm delete of ${doc.filename}`}
                        >
                          {isDeleting ? "..." : "Yes"}
                        </button>
                        <button
                          type="button"
                          className="btn-delete-cancel"
                          onClick={() => setConfirmDeleteId(null)}
                          disabled={isDeleting}
                          aria-label="Cancel deletion"
                        >
                          No
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        className="btn-delete"
                        onClick={() => setConfirmDeleteId(doc.id)}
                        title="Delete document and vector embeddings"
                        aria-label={`Delete ${doc.filename}`}
                      >
                        🗑️
                      </button>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}