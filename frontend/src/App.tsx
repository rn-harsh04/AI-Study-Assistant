import { useEffect, useState, useRef } from "react";
import ChatPanel from "./components/ChatPanel";
import DocumentsPanel from "./components/DocumentsPanel";
import {
  listDocuments,
  deleteDocument as apiDeleteDocument,
  type DocumentRecord,
  type ChatMode,
} from "./lib/api";

type ActiveTab = "chat" | "quiz" | "documents";

export default function App() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [activeDocument, setActiveDocument] = useState<DocumentRecord | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>("chat");
  const [chatMode, setChatMode] = useState<ChatMode>("explain");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const pollingRef = useRef<number | null>(null);

  async function fetchDocuments(quiet = false) {
    if (!quiet) setError(null);
    try {
      const currentDocuments = await listDocuments();
      setDocuments(currentDocuments);

      // Keep active document in sync if it was updated or deleted
      if (activeDocument) {
        const stillExists = currentDocuments.find((d) => d.id === activeDocument.id);
        setActiveDocument(stillExists || null);
      }
    } catch (fetchError) {
      if (!quiet) {
        setError(fetchError instanceof Error ? fetchError.message : "Unable to load indexed documents");
      }
    } finally {
      if (!quiet) setLoading(false);
    }
  }

  // Initial load
  useEffect(() => {
    void fetchDocuments();
  }, []);

  // Poll when any document is in "processing" state
  useEffect(() => {
    const hasProcessing = documents.some((d) => d.status === "processing");
    if (hasProcessing) {
      pollingRef.current = window.setInterval(() => {
        void fetchDocuments(true);
      }, 2500);
    } else if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [documents]);

  async function handleDeleteDocument(id: string) {
    try {
      await apiDeleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      if (activeDocument?.id === id) {
        setActiveDocument(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete document");
    }
  }

  function handleUploaded(newDoc: DocumentRecord) {
    setDocuments((prev) => [newDoc, ...prev.filter((d) => d.id !== newDoc.id)]);
    setActiveDocument(newDoc);
    // Switch to documents view or keep on current view
    void fetchDocuments(true);
  }

  function navigateToChat(mode: ChatMode = "explain") {
    setChatMode(mode);
    setActiveTab(mode === "quiz" ? "quiz" : "chat");
  }

  const processingCount = documents.filter((d) => d.status === "processing").length;
  const readyCount = documents.filter((d) => d.status === "ready").length;

  return (
    <div className="app-container">
      {/* Top Glassmorphic Navigation Bar */}
      <header className="app-header">
        <div className="header-brand">
          <div className="brand-logo">🧠</div>
          <div className="brand-titles">
            <h1 className="brand-name">StudyAssistant<span className="brand-ai">AI</span></h1>
            <span className="brand-tagline">Grounded Multimodal RAG</span>
          </div>
        </div>

        {/* Center Tab Navigation */}
        <nav className="nav-tabs" role="tablist" aria-label="Main Navigation">
          <button
            type="button"
            className={`nav-tab ${activeTab === "chat" ? "nav-tab-active" : ""}`}
            onClick={() => {
              setChatMode("explain");
              setActiveTab("chat");
            }}
          >
            <span className="tab-icon">💬</span>
            <span className="tab-text">Explain & Chat</span>
          </button>
          <button
            type="button"
            className={`nav-tab ${activeTab === "quiz" ? "nav-tab-active" : ""}`}
            onClick={() => {
              setChatMode("quiz");
              setActiveTab("quiz");
            }}
          >
            <span className="tab-icon">🎯</span>
            <span className="tab-text">Practice Quiz</span>
          </button>
          <button
            type="button"
            className={`nav-tab ${activeTab === "documents" ? "nav-tab-active" : ""}`}
            onClick={() => setActiveTab("documents")}
          >
            <span className="tab-icon">📚</span>
            <span className="tab-text">Library & Files</span>
            <span className="tab-badge">{documents.length}</span>
          </button>
        </nav>

        {/* Header Right Status Badges */}
        <div className="header-status">
          {processingCount > 0 ? (
            <span className="status-pill status-pill-warning">
              <span className="spinner-mini"></span> Indexing {processingCount} doc{processingCount > 1 ? "s" : ""}
            </span>
          ) : readyCount > 0 ? (
            <span className="status-pill status-pill-success">
              <span className="status-dot"></span> {readyCount} Document{readyCount > 1 ? "s" : ""} Ready
            </span>
          ) : (
            <span className="status-pill status-pill-neutral">
              No docs uploaded
            </span>
          )}
        </div>
      </header>

      {/* Main App Workspace */}
      <main className="app-main-content">
        {error && (
          <div className="alert alert-danger global-alert">
            <span>{error}</span>
            <button type="button" className="btn-close" onClick={() => setError(null)}>✕</button>
          </div>
        )}

        {loading ? (
          <div className="loading-state card">
            <span className="spinner-lg"></span>
            <p>Loading study assistant workspace...</p>
          </div>
        ) : (
          <>
            {(activeTab === "chat" || activeTab === "quiz") && (
              <ChatPanel
                documentCount={readyCount}
                activeDocument={activeDocument}
                allDocuments={documents}
                onSelectDocument={setActiveDocument}
                initialMode={chatMode}
                onSwitchToDocs={() => setActiveTab("documents")}
              />
            )}

            {activeTab === "documents" && (
              <DocumentsPanel
                documents={documents}
                activeDocument={activeDocument}
                onSelectDocument={setActiveDocument}
                onDeleteDocument={handleDeleteDocument}
                onUploaded={handleUploaded}
                onNavigateToChat={navigateToChat}
              />
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <p>AI Study Assistant • Grounded with Gemini & FAISS • Upload notes, ask questions, ace quizzes.</p>
      </footer>
    </div>
  );
}