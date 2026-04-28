import type { SourceChunk } from "../lib/api";

type SourcesListProps = {
  sources: SourceChunk[];
};

export default function SourcesList({ sources }: SourcesListProps) {
  if (sources.length === 0) {
    return (
      <div className="sources">
        <p className="muted">No sources yet. Answers will appear here once you ask a question.</p>
      </div>
    );
  }

  return (
    <div className="sources">
      <h3>Sources</h3>
      <ul>
        {sources.map((source) => (
          <li key={`${source.document_id}-${source.chunk_id}`} className="source-item">
            <div className="source-meta">
              <strong>{source.filename}</strong>
              <span>
                chunk {source.chunk_id}
                {source.page_number ? ` · page ${source.page_number}` : ""}
                {source.score !== null ? ` · score ${source.score.toFixed(2)}` : ""}
              </span>
            </div>
            <p>{source.excerpt}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
