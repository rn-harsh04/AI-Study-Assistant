import { useState } from "react";
import type { SourceChunk } from "../lib/api";

type SourcesListProps = {
  sources: SourceChunk[];
};

export default function SourcesList({ sources }: SourcesListProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (sources.length === 0) {
    return null;
  }

  return (
    <section className="sources-container">
      <button
        type="button"
        className="sources-toggle-btn"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
      >
        <span className="sources-toggle-title">
          📌 Grounded Source References ({sources.length})
        </span>
        <span className="sources-toggle-arrow">{isOpen ? "▲ Hide" : "▼ Show"}</span>
      </button>

      {isOpen && (
        <div className="sources-grid">
          {sources.map((source, index) => (
            <article key={`${source.document_id}-${source.chunk_id}-${index}`} className="source-card">
              <div className="source-meta">
                <span className="source-file">📄 {source.filename}</span>
                {source.page_number && (
                  <span className="source-page">Page {source.page_number}</span>
                )}
                <span className="source-chunk">Chunk #{source.chunk_id}</span>
                {source.score !== null && source.score !== undefined && (
                  <span className="source-score" title="Relevance Score">
                    Score: {Math.round(source.score * 100)}%
                  </span>
                )}
              </div>
              <p className="source-text">{source.excerpt}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}