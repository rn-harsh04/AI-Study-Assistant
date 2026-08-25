import { useState, useEffect, useCallback } from "react";
import {
  generateFlashcards,
  downloadAnkiDeck,
  downloadCsvDeck,
  type DocumentRecord,
  type FlashcardDeck,
} from "../lib/api";

type FlashcardsPanelProps = {
  documents: DocumentRecord[];
  activeDocument: DocumentRecord | null;
  onSelectDocument: (doc: DocumentRecord | null) => void;
  onSwitchToDocs: () => void;
};

export default function FlashcardsPanel({
  documents,
  activeDocument,
  onSelectDocument,
  onSwitchToDocs,
}: FlashcardsPanelProps) {
  const [deck, setDeck] = useState<FlashcardDeck | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [count, setCount] = useState(10);
  const [topic, setTopic] = useState("");
  const [busy, setBusy] = useState(false);
  const [exportingAnki, setExportingAnki] = useState(false);
  const [exportingCsv, setExportingCsv] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [masteredIndices, setMasteredIndices] = useState<Set<number>>(new Set());

  const readyDocs = documents.filter((d) => d.status === "ready");

  const handleGenerate = async () => {
    if (readyDocs.length === 0) return;
    setBusy(true);
    setError(null);
    setIsFlipped(false);
    setCurrentIndex(0);
    setMasteredIndices(new Set());

    try {
      const generatedDeck = await generateFlashcards(
        activeDocument?.id ?? null,
        count,
        topic.trim() || null,
      );
      setDeck(generatedDeck);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate flashcard deck");
    } finally {
      setBusy(false);
    }
  };

  const handleExportAnki = async () => {
    if (!deck || deck.cards.length === 0) return;
    setExportingAnki(true);
    try {
      await downloadAnkiDeck(deck);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to download Anki deck");
    } finally {
      setExportingAnki(false);
    }
  };

  const handleExportCsv = async () => {
    if (!deck || deck.cards.length === 0) return;
    setExportingCsv(true);
    try {
      await downloadCsvDeck(deck);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to download CSV");
    } finally {
      setExportingCsv(false);
    }
  };

  const nextCard = useCallback(() => {
    if (!deck || deck.cards.length === 0) return;
    setIsFlipped(false);
    setCurrentIndex((prev) => (prev + 1) % deck.cards.length);
  }, [deck]);

  const prevCard = useCallback(() => {
    if (!deck || deck.cards.length === 0) return;
    setIsFlipped(false);
    setCurrentIndex((prev) => (prev - 1 + deck.cards.length) % deck.cards.length);
  }, [deck]);

  const toggleFlip = useCallback(() => {
    setIsFlipped((prev) => !prev);
  }, []);

  const shuffleDeck = () => {
    if (!deck) return;
    const shuffled = [...deck.cards].sort(() => Math.random() - 0.5);
    setDeck({ ...deck, cards: shuffled });
    setCurrentIndex(0);
    setIsFlipped(false);
    setMasteredIndices(new Set());
  };

  const markMastered = (index: number) => {
    setMasteredIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  // Keyboard navigation shortcuts
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      if (e.code === "Space") {
        e.preventDefault();
        toggleFlip();
      } else if (e.code === "ArrowRight") {
        e.preventDefault();
        nextCard();
      } else if (e.code === "ArrowLeft") {
        e.preventDefault();
        prevCard();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [toggleFlip, nextCard, prevCard]);

  const currentCard = deck?.cards[currentIndex];
  const totalCards = deck?.cards.length || 0;
  const progressPercent = totalCards > 0 ? Math.round(((currentIndex + 1) / totalCards) * 100) : 0;

  return (
    <div className="flashcards-layout stack-lg">
      {/* Flashcard Generation Settings Card */}
      <section className="card flashcards-generator-card stack" aria-label="Flashcard Deck Configuration">
        <div className="section-heading">
          <span className="eyebrow">Active Recall & Spaced Repetition</span>
          <h2>Flashcards & Anki Deck Generator</h2>
          <p className="muted">
            Auto-generate high-yield conceptual flashcards from your study materials with 1-click Anki (.apkg) & CSV exports.
          </p>
        </div>

        <div className="generator-controls-grid">
          <div className="control-group">
            <label htmlFor="deck-doc-select" className="control-label">Source Document:</label>
            <select
              id="deck-doc-select"
              className="scope-select"
              aria-label="Select source document for flashcards"
              value={activeDocument?.id || "all"}
              onChange={(e) => {
                const val = e.target.value;
                if (val === "all") onSelectDocument(null);
                else {
                  const found = documents.find((d) => d.id === val);
                  if (found) onSelectDocument(found);
                }
              }}
            >
              <option value="all">🌐 All Indexed Documents ({readyDocs.length})</option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id} disabled={doc.status !== "ready"}>
                  {doc.filename} {doc.status !== "ready" ? `(${doc.status})` : ""}
                </option>
              ))}
            </select>
          </div>

          <div className="control-group">
            <label htmlFor="deck-count-select" className="control-label">Card Count:</label>
            <select
              id="deck-count-select"
              className="scope-select"
              aria-label="Select number of cards to generate"
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
            >
              <option value={5}>5 High-Yield Cards</option>
              <option value={10}>10 Core Concept Cards</option>
              <option value={15}>15 Comprehensive Cards</option>
              <option value={20}>20 In-Depth Cards</option>
            </select>
          </div>

          <div className="control-group flex-grow">
            <label htmlFor="deck-topic-input" className="control-label">Specific Topic / Focus (Optional):</label>
            <input
              id="deck-topic-input"
              type="text"
              className="topic-input"
              placeholder="e.g. Chapter 3, Formulas, Key Definitions..."
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              aria-label="Optional topic or chapter focus"
            />
          </div>

          <div className="control-group-actions">
            <button
              type="button"
              className="btn-primary btn-generate-deck"
              onClick={handleGenerate}
              disabled={busy || readyDocs.length === 0}
              aria-label="Generate flashcard deck"
            >
              {busy ? (
                <>
                  <span className="spinner-mini" aria-hidden="true"></span> Generating...
                </>
              ) : (
                "✨ Generate Deck"
              )}
            </button>
          </div>
        </div>

        {readyDocs.length === 0 && (
          <div className="no-docs-warning">
            <span>⚠️ No documents ready yet.</span>
            <button type="button" className="btn-link" onClick={onSwitchToDocs}>
              Upload a document first
            </button>
          </div>
        )}

        {error && <div className="alert alert-danger" role="alert">{error}</div>}
      </section>

      {/* Interactive 3D Study Card Area */}
      {deck && deck.cards.length > 0 ? (
        <section className="card flashcards-study-area stack" aria-label="Interactive Flashcard Practice">
          {/* Deck Header & Exports */}
          <div className="deck-header-bar">
            <div>
              <span className="eyebrow">Study Deck</span>
              <h3>{deck.title}</h3>
              <p className="muted">
                {deck.cards.length} cards generated • {masteredIndices.size} mastered
              </p>
            </div>

            <div className="deck-export-buttons">
              <button
                type="button"
                className="btn-action btn-export-anki"
                onClick={handleExportAnki}
                disabled={exportingAnki}
                title="Download genuine .apkg package importable into Anki app"
                aria-label="Export to Anki .apkg"
              >
                {exportingAnki ? "Packing..." : "📥 Download Anki Deck (.apkg)"}
              </button>
              <button
                type="button"
                className="btn-action btn-export-csv"
                onClick={handleExportCsv}
                disabled={exportingCsv}
                title="Export as standard CSV file for Quizlet or Notion"
                aria-label="Export to CSV"
              >
                {exportingCsv ? "Exporting..." : "📄 Export CSV"}
              </button>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="deck-progress-container" aria-label="Deck study progress">
            <div className="progress-label-row">
              <span>Card {currentIndex + 1} of {totalCards}</span>
              <span>{progressPercent}% Completed</span>
            </div>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${progressPercent}%` }}></div>
            </div>
          </div>

          {/* 3D Flip Card Container */}
          <div className="flashcard-scene" onClick={toggleFlip} tabIndex={0} role="button" aria-label={`Flashcard: ${isFlipped ? "Answer side" : "Question side"}. Click or press space to flip.`}>
            <div className={`flashcard-object ${isFlipped ? "is-flipped" : ""}`}>
              {/* Front Side */}
              <div className="flashcard-face flashcard-front">
                <div className="card-face-header">
                  <span className="card-topic-pill">
                    {currentCard?.topic || "Concept"}
                  </span>
                  <span className="card-side-label">FRONT (Question / Term)</span>
                </div>
                <div className="card-face-body">
                  <p className="card-front-text">{currentCard?.front}</p>
                </div>
                <div className="card-face-footer">
                  <span className="flip-hint">🔄 Click or Press Space to Flip</span>
                </div>
              </div>

              {/* Back Side */}
              <div className="flashcard-face flashcard-back">
                <div className="card-face-header">
                  <span className="card-topic-pill">
                    {currentCard?.topic || "Concept"}
                  </span>
                  <span className="card-side-label">BACK (Explanation / Answer)</span>
                </div>
                <div className="card-face-body">
                  <p className="card-back-text">{currentCard?.back}</p>
                </div>
                <div className="card-face-footer">
                  <span className="flip-hint">🔄 Click or Press Space to Flip</span>
                </div>
              </div>
            </div>
          </div>

          {/* Flashcard Study Navigation Controls */}
          <div className="flashcard-controls-row">
            <button
              type="button"
              className="btn-secondary"
              onClick={prevCard}
              title="Previous card (Left Arrow)"
              aria-label="Previous card"
            >
              ◀ Previous
            </button>

            <button
              type="button"
              className={`btn-action ${masteredIndices.has(currentIndex) ? "btn-mastered-active" : ""}`}
              onClick={() => markMastered(currentIndex)}
              aria-label="Mark card as mastered"
            >
              {masteredIndices.has(currentIndex) ? "⭐ Mastered" : "☆ Mark Mastered"}
            </button>

            <button
              type="button"
              className="btn-primary btn-flip-action"
              onClick={toggleFlip}
              aria-label="Flip flashcard"
            >
              🔄 Flip Card (Space)
            </button>

            <button
              type="button"
              className="btn-secondary"
              onClick={shuffleDeck}
              title="Shuffle all cards"
              aria-label="Shuffle cards"
            >
              🔀 Shuffle
            </button>

            <button
              type="button"
              className="btn-secondary"
              onClick={nextCard}
              title="Next card (Right Arrow)"
              aria-label="Next card"
            >
              Next ▶
            </button>
          </div>

          {/* Quick List Preview */}
          <details className="deck-quick-table-details">
            <summary className="deck-summary-toggle">
              📋 View all {deck.cards.length} cards in this deck
            </summary>
            <div className="deck-cards-list-table">
              {deck.cards.map((c, i) => (
                <div
                  key={i}
                  className={`deck-row-item ${i === currentIndex ? "deck-row-active" : ""}`}
                  onClick={() => {
                    setCurrentIndex(i);
                    setIsFlipped(false);
                  }}
                >
                  <span className="row-num">#{i + 1}</span>
                  <div className="row-texts">
                    <strong className="row-front">{c.front}</strong>
                    <span className="row-back">{c.back}</span>
                  </div>
                  {c.topic && <span className="badge badge-primary">{c.topic}</span>}
                </div>
              ))}
            </div>
          </details>
        </section>
      ) : (
        !busy && (
          <div className="empty-state card">
            <span className="empty-icon" aria-hidden="true">🗂️</span>
            <h3>No Flashcard Deck Generated Yet</h3>
            <p className="muted">
              Select your study material and click <strong>✨ Generate Deck</strong> above to create active-recall cards with Anki export.
            </p>
          </div>
        )
      )}
    </div>
  );
}