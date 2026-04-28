import { useEffect, useState } from "react";
import ChatPanel from "./components/ChatPanel";
import UploadPanel from "./components/UploadPanel";
import { listDocuments, type DocumentRecord } from "./lib/api";

export default function App() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [activeDocument, setActiveDocument] = useState<DocumentRecord | null>(null);
  const [uploadTrigger, setUploadTrigger] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refreshDocuments() {
    setError(null);
    try {
      const currentDocuments = await listDocuments();
      setDocuments(currentDocuments);
      setActiveDocument(currentDocuments[0] ?? null);
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Unable to load documents");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshDocuments();
  }, []);

  return (
    <main className="app-shell">
      <section className="hero card">
        <div className="eyebrow">AI Study Assistant</div>
        <h1>Upload once. Explain anything. Turn notes into quizzes.</h1>
        <p>
          This workspace is built for students: add a PDF or notes, ask for explanations, and
          generate quick practice quizzes from the same material.
        </p>
        <div className="hero-metrics">
          <div>
            <strong>Upload</strong>
            <span>PDFs and notes</span>
          </div>
          <div>
            <strong>Chat</strong>
            <span>Ask for explanations</span>
          </div>
          <div>
            <strong>Quiz</strong>
            <span>Practice on demand</span>
          </div>
        </div>
      </section>

      <section className="workflow card">
        <div className="workflow-step">
          <span>1</span>
          <div>
            <strong>Upload your study material</strong>
            <p>PDFs are parsed, chunked, and indexed for retrieval.</p>
          </div>
        </div>
        <div className="workflow-step">
          <span>2</span>
          <div>
            <strong>Ask for explanations</strong>
            <p>Use the chat to get summaries, concept breakdowns, and clarifications.</p>
          </div>
        </div>
        <div className="workflow-step">
          <span>3</span>
          <div>
            <strong>Generate quizzes</strong>
            <p>Turn the same content into quick practice questions with answers.</p>
          </div>
        </div>
      </section>

      <section className="simple-layout">
        <div className="upload-center stack">
          <UploadPanel
            onUploaded={(document) => {
              setDocuments((current) => [document, ...current.filter((item) => item.id !== document.id)]);
              setActiveDocument(document);
              setUploadTrigger((n) => n + 1);
            }}
          />
        </div>

        <div className="stack">
          <ChatPanel documentCount={documents.length} activeDocument={activeDocument} uploadTrigger={uploadTrigger} />
          <section className="card stack quick-note">
            <div className="section-heading">
              <span className="eyebrow">Tips</span>
              <h2>What to ask next</h2>
            </div>
            <p className="muted">Try: explain this PDF in simple words, or quiz me from this PDF.</p>
          </section>
          {loading ? <p className="muted">Loading documents...</p> : null}
          {error ? <p className="error">{error}</p> : null}
        </div>
      </section>
    </main>
  );
}

