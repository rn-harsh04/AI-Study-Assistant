import type { DocumentRecord } from "../lib/api";

type DocumentsPanelProps = {
  documents: DocumentRecord[];
};

export default function DocumentsPanel({ documents }: DocumentsPanelProps) {
  return (
    <section className="card stack">
      <div className="section-heading">
        <span className="eyebrow">Library</span>
        <h2>Indexed documents</h2>
      </div>

      {documents.length === 0 ? (
        <p className="muted">No documents uploaded yet.</p>
      ) : (
        <ul className="document-list">
          {documents.map((document) => (
            <li key={document.id} className="document-item">
              <div>
                <strong>{document.filename}</strong>
                <p className="muted">{document.status}</p>
                {document.error_message ? <p className="error">{document.error_message}</p> : null}
              </div>
              <div className="document-stats">
                <span>{document.chunk_count} chunks</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
