import { useState } from "react";
import type { DocumentRecord } from "../lib/api";
import UploadPanel from "./UploadPanel";

type DocumentsPanelProps = {
  documents: DocumentRecord[];
  activeDocument: DocumentRecord | null;
  onSelectDocument: (doc: DocumentRecord | null) => void;
  onDeleteDocument: (docId: string) => Promise<void>;
  onUploaded: (doc: DocumentRecord) => void;
  onNavigateToChat: (mode?: "explain" | "quiz") => void;
};

export default function DocumentsPanel({
  documents,
  activeDocument,
  onSelectDocument,
  onDeleteDocument,
  onUploaded,
  onNavigateToChat,
}: DocumentsPanelProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  async function handleDelete(id: string) {
    setDeletingId(id);
    try {
      await onDeleteDocument(id);
      setConfirmDeleteId(null);
    } finally {
      setDeletingId(null);
    }
  }

  function formatTime(iso: string) {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  }

  function getFileIcon(filename: string) {
    const ext = filename.split(".").pop()?.toLowerCase();
    if (ext === "pdf") return "📄";
    if (["png", "jpg", "jpeg", "webp"].includes(ext || "")) return "🖼️";
    return "📝";
  }

  return (
    <div className="documents-container stack-lg">
      <div className="grid-split">
        {/* Upload Card */}
        <UploadPanel onUploaded={onUploaded} />

        {/* Overview Stats Card */}
        <div className="card overview-card">
          <div className="section-heading">
            <span className="eyebrow">Knowledge Base Stats</span>
            <h2>Document Overview</h2>
          </div>
          <div className="stats-grid">
            <div className="stat-box">
              <span className="stat-number">{documents.length}</span>
              <span className="stat-label">Total Documents</span>
            </div>
            <div className="stat-box">
              <span className="stat-number">
                {documents.reduce((acc, d) => acc + (d.chunk_count || 0), 0)}
              </span>
              <span className="stat-label">Indexed Chunks</span>
            </div>
            <div className="stat-box">
              <span className="stat-number">
                {documents.filter((d) => d.status === "ready").length}
              </span>
              <span className="stat-label">Ready for RAG</span>
            </div>
          </div>
          <div className="overview-actions">
            <button
              type="button"
              className={`chip chip-lg ${!activeDocument ? "active" : ""}`}
              onClick={() => onSelectDocument(null)}
            >
              🌐 Search Across All Documents
            </button>
          </div>
        </div>
      </div>

      {/* Document Library Section */}
      <section className="card library-card">
        <div className="library-header">
          <div>
            <span className="eyebrow">Library</span>
            <h2>Indexed Study Materials</h2>
          </div>
          <span className="badge badge-count">{documents.length} Total</span>
        </div>

        {documents.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon">📂</span>
            <h3>No documents in your library yet</h3>
            <p className="muted">
              Upload a PDF lecture slide, study notes, or diagrams above to start asking questions or generating practice quizzes.
            </p>
          </div>
        ) : (
          <div className="document-grid">
            {documents.map((doc) => {
              const isActive = activeDocument?.id === doc.id;
              const isDeleting = deletingId === doc.id;
              const isConfirming = confirmDeleteId === doc.id;

              return (
                <div
                  key={doc.id}
                  className={`doc-card ${isActive ? "doc-card-active" : ""}`}
                >
                  <div className="doc-card-header">
                    <span className="doc-type-icon">{getFileIcon(doc.filename)}</span>
                    <div className="doc-title-box">
                      <h4 className="doc-title" title={doc.filename}>
                        {doc.filename}
                      </h4>
                      <span className="doc-time">{formatTime(doc.created_at)}</span>
                    </div>
                  </div>

                  <div className="doc-badges">
                    {doc.status === "ready" && (
                      <span className="badge badge-success">
                        <span className="badge-dot"></span> Ready • {doc.chunk_count} chunks
                      </span>
                    )}
                    {doc.status === "processing" && (
                      <span className="badge badge-warning">
                        <span className="spinner-mini"></span> Indexing...
                      </span>
                    )}
                    {doc.status === "failed" && (
                      <span className="badge badge-danger">
                        Failed to index
                      </span>
                    )}
                    {isActive && (
                      <span className="badge badge-primary">Active Context</span>
                    )}
                  </div>

                  {doc.error_message ? (
                    <p className="doc-error-msg">{doc.error_message}</p>
                  ) : null}

                  <div className="doc-card-footer">
                    <div className="doc-main-actions">
                      <button
                        type="button"
                        className={`btn-action ${isActive ? "btn-active" : ""}`}
                        onClick={() => {
                          onSelectDocument(doc);
                          onNavigateToChat("explain");
                        }}
                        disabled={doc.status !== "ready"}
                        title="Chat with this document"
                      >
                        💬 Explain
                      </button>
                      <button
                        type="button"
                        className="btn-action"
                        onClick={() => {
                          onSelectDocument(doc);
                          onNavigateToChat("quiz");
                        }}
                        disabled={doc.status !== "ready"}
                        title="Generate quiz from this document"
                      >
                        🎯 Quiz
                      </button>
                    </div>

                    <div className="doc-delete-box">
                      {isConfirming ? (
                        <div className="confirm-delete-row">
                          <span className="confirm-label">Delete?</span>
                          <button
                            type="button"
                            className="btn-delete-confirm"
                            onClick={() => handleDelete(doc.id)}
                            disabled={isDeleting}
                          >
                            {isDeleting ? "..." : "Yes"}
                          </button>
                          <button
                            type="button"
                            className="btn-delete-cancel"
                            onClick={() => setConfirmDeleteId(null)}
                            disabled={isDeleting}
                          >
                            No
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          className="btn-delete"
                          onClick={() => setConfirmDeleteId(doc.id)}
                          title="Remove document from library"
                        >
                          🗑️
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}