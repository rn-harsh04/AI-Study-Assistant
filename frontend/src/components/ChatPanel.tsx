import { FormEvent, useMemo, useRef, useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import SourcesList from "./SourcesList";
import {
  askQuestion,
  type ChatMode,
  type ChatResponse,
  type DocumentRecord,
  type QuizPayload,
} from "../lib/api";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  quiz?: QuizPayload | null;
  sources?: ChatResponse["sources"];
  fallback?: boolean;
  fallbackReason?: string | null;
  timestamp: string;
};

type ChatPanelProps = {
  documentCount: number;
  activeDocument: DocumentRecord | null;
  allDocuments: DocumentRecord[];
  onSelectDocument: (doc: DocumentRecord | null) => void;
  mode: ChatMode;
  onSwitchToDocs: () => void;
};

export default function ChatPanel({
  documentCount,
  activeDocument,
  allDocuments,
  onSelectDocument,
  mode,
  onSwitchToDocs,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "👋 **Welcome to your AI Study Assistant!**\n\nUpload lecture slides, textbooks, or study notes, then ask questions to get grounded explanations, summaries, or interactive practice quizzes.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Active Quiz State
  const [activeQuiz, setActiveQuiz] = useState<QuizPayload | null>(null);
  const [selectedOptions, setSelectedOptions] = useState<Array<number | null>>([]);
  const [quizSubmitted, setQuizSubmitted] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const explainTemplates = [
    "Explain the core concepts in simple terms with examples.",
    "Summarize this document in 5 key takeaways.",
    "List all important definitions and formulas from this material.",
    "Compare and contrast the main theories presented.",
  ];

  const quizTemplates = [
    "Generate a 5-question practice quiz from the uploaded document.",
    "Create a challenging multiple choice quiz testing core concepts.",
    "Quiz me on key terms and definitions with explanations.",
  ];

  const currentTemplates = mode === "quiz" ? quizTemplates : explainTemplates;

  const canAsk = useMemo(
    () => question.trim().length > 0 && !busy && documentCount > 0,
    [question, busy, documentCount],
  );

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy, activeQuiz]);

  function applyTemplate(template: string) {
    setQuestion(template);
    textareaRef.current?.focus();
  }

  function clearHistory() {
    setMessages([
      {
        id: "welcome",
        role: "assistant",
        content: "Chat cleared. Ready for your next question or quiz prompt!",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
    setActiveQuiz(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || busy) {
      return;
    }

    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      timestamp: timeStr,
    };

    setMessages((current) => [...current, userMessage]);
    setQuestion("");
    setBusy(true);
    setError(null);

    try {
      const response = await askQuestion(trimmed, mode, activeDocument?.id ?? null);
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.answer,
        quiz: response.quiz,
        sources: response.sources,
        fallback: response.fallback,
        fallbackReason: response.fallback_reason,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((current) => [...current, assistantMsg]);

      if (mode === "quiz" && response.quiz) {
        setActiveQuiz(response.quiz);
        setSelectedOptions(new Array(response.quiz.questions.length).fill(null));
        setQuizSubmitted(false);
      }
    } catch (askError) {
      setError(askError instanceof Error ? askError.message : "Unable to reach the assistant");
    } finally {
      setBusy(false);
    }
  }

  // Quiz helper functions
  const allQuestionsAnswered = useMemo(() => {
    if (!activeQuiz || selectedOptions.length === 0) return false;
    return selectedOptions.every((val) => val !== null);
  }, [activeQuiz, selectedOptions]);

  const score = useMemo(() => {
    if (!quizSubmitted || !activeQuiz) return 0;
    return activeQuiz.questions.reduce((total, q, idx) => {
      return total + (selectedOptions[idx] === q.correct_option_index ? 1 : 0);
    }, 0);
  }, [quizSubmitted, activeQuiz, selectedOptions]);

  function chooseOption(questionIndex: number, optionIndex: number) {
    if (quizSubmitted) return;
    setSelectedOptions((current) => {
      const next = [...current];
      next[questionIndex] = optionIndex;
      return next;
    });
  }

  function submitQuiz() {
    if (!allQuestionsAnswered) return;
    setQuizSubmitted(true);
  }

  function retakeQuiz() {
    if (!activeQuiz) return;
    setSelectedOptions(new Array(activeQuiz.questions.length).fill(null));
    setQuizSubmitted(false);
  }

  function copyMessage(text: string) {
    navigator.clipboard.writeText(text);
  }

  return (
    <div className="chat-layout">
      {/* Top Context & Controls Bar */}
      <div className="chat-top-bar card">
        <div className="chat-top-info">
          <div className="chat-mode-indicator">
            <span className="mode-indicator-pill">
              {mode === "quiz" ? "🎯 Quiz Mode Active" : "💬 Explain & Chat Mode Active"}
            </span>
          </div>

          <div className="chat-top-actions">
            <div className="document-scope-box">
              <label htmlFor="doc-scope-select" className="scope-label">Context:</label>
              <select
                id="doc-scope-select"
                className="scope-select"
                aria-label="Select study document context scope"
                value={activeDocument?.id || "all"}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val === "all") {
                    onSelectDocument(null);
                  } else {
                    const found = allDocuments.find((d) => d.id === val);
                    if (found) onSelectDocument(found);
                  }
                }}
              >
                <option value="all">🌐 All Indexed Documents ({documentCount})</option>
                {allDocuments.map((doc) => (
                  <option key={doc.id} value={doc.id} disabled={doc.status !== "ready"}>
                    {doc.filename} {doc.status !== "ready" ? `(${doc.status})` : `(${doc.chunk_count} chunks)`}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="button"
              className="btn-clear-chat"
              onClick={clearHistory}
              title="Clear conversation"
              aria-label="Clear chat conversation"
            >
              🧹 Clear
            </button>
          </div>
        </div>

        {documentCount === 0 && (
          <div className="no-docs-warning">
            <span>⚠️ No documents indexed yet.</span>
            <button type="button" className="btn-link" onClick={onSwitchToDocs}>
              Upload a document
            </button>
          </div>
        )}
      </div>

      {/* Messages Feed */}
      <div className="messages-feed" aria-live="polite" aria-label="Conversation history">
        {messages.map((msg) => (
          <div key={msg.id} className={`message-row message-${msg.role}`}>
            <div className="message-avatar" aria-hidden="true">
              {msg.role === "assistant" ? "🤖" : "👤"}
            </div>
            <div className="message-bubble">
              <div className="message-header">
                <span className="message-sender">
                  {msg.role === "assistant" ? "Study Assistant" : "You"}
                </span>
                <span className="message-time">{msg.timestamp}</span>
              </div>

              <div className="message-content markdown-body">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content}
                </ReactMarkdown>
              </div>

              {msg.role === "assistant" && msg.id !== "welcome" && (
                <div className="message-footer">
                  <button
                    type="button"
                    className="btn-msg-action"
                    onClick={() => copyMessage(msg.content)}
                    title="Copy to clipboard"
                    aria-label="Copy response to clipboard"
                  >
                    📋 Copy
                  </button>
                </div>
              )}

              {msg.fallback && msg.fallbackReason && (
                <div className="fallback-note">
                  ℹ️ {msg.fallbackReason}
                </div>
              )}

              {msg.sources && msg.sources.length > 0 && (
                <SourcesList sources={msg.sources} />
              )}
            </div>
          </div>
        ))}

        {busy && (
          <div className="message-row message-assistant" aria-live="assertive">
            <div className="message-avatar" aria-hidden="true">🤖</div>
            <div className="message-bubble thinking-bubble">
              <span className="spinner-mini" aria-hidden="true"></span>
              <span>
                {mode === "quiz"
                  ? "Generating interactive quiz from your study materials..."
                  : "Searching document chunks and formulating answer..."}
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Active Interactive Quiz Card */}
      {activeQuiz && (
        <section className="card active-quiz-card" aria-label="Interactive practice quiz">
          <div className="quiz-card-header">
            <div>
              <span className="eyebrow">Interactive Assessment</span>
              <h3>{activeQuiz.title}</h3>
              {activeQuiz.instructions && (
                <p className="muted">{activeQuiz.instructions}</p>
              )}
            </div>
            {quizSubmitted && (
              <div className={`quiz-score-badge ${score >= activeQuiz.questions.length * 0.8 ? "score-high" : "score-mid"}`}>
                Score: {score} / {activeQuiz.questions.length} ({Math.round((score / activeQuiz.questions.length) * 100)}%)
              </div>
            )}
          </div>

          <div className="quiz-questions-list">
            {activeQuiz.questions.map((q, qIndex) => {
              const userChoice = selectedOptions[qIndex];
              const isCorrect = userChoice === q.correct_option_index;

              return (
                <article key={qIndex} className="quiz-question-item">
                  <div className="question-title-row">
                    <span className="q-number">Q{qIndex + 1}</span>
                    <h4 className="q-text">{q.question}</h4>
                  </div>

                  <div className="options-grid">
                    {q.options.map((opt, optIndex) => {
                      const selected = userChoice === optIndex;
                      const isOptionCorrect = q.correct_option_index === optIndex;

                      let optClass = "opt-btn";
                      if (selected) optClass += " opt-selected";
                      if (quizSubmitted) {
                        if (isOptionCorrect) optClass += " opt-correct";
                        else if (selected && !isOptionCorrect) optClass += " opt-wrong";
                      }

                      return (
                        <button
                          key={optIndex}
                          type="button"
                          className={optClass}
                          onClick={() => chooseOption(qIndex, optIndex)}
                          disabled={quizSubmitted}
                          aria-pressed={selected}
                        >
                          <span className="opt-letter" aria-hidden="true">
                            {String.fromCharCode(65 + optIndex)}
                          </span>
                          <span className="opt-label">{opt}</span>
                        </button>
                      );
                    })}
                  </div>

                  {quizSubmitted && (
                    <div className={`answer-feedback ${isCorrect ? "feedback-success" : "feedback-danger"}`} role="status">
                      <strong>{isCorrect ? "✅ Correct!" : "❌ Incorrect."}</strong>{" "}
                      {q.explanation && <span>{q.explanation}</span>}
                    </div>
                  )}
                </article>
              );
            })}
          </div>

          <div className="quiz-footer-actions">
            {!quizSubmitted ? (
              <button
                type="button"
                className="btn-primary"
                onClick={submitQuiz}
                disabled={!allQuestionsAnswered}
              >
                {allQuestionsAnswered
                  ? "🎯 Submit Quiz & Check Answers"
                  : `Answer all questions (${selectedOptions.filter((v) => v !== null).length}/${activeQuiz.questions.length})`}
              </button>
            ) : (
              <div className="quiz-completed-row">
                <button type="button" className="btn-secondary" onClick={retakeQuiz}>
                  🔄 Retake Quiz
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => {
                    setQuestion("Generate another practice quiz on different topics from this material.");
                    textareaRef.current?.focus();
                  }}
                >
                  ✨ Generate Another Quiz
                </button>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Suggested Prompt Chips */}
      <div className="prompt-chips-tray" aria-label="Suggested prompt templates">
        <span className="chips-label">💡 Suggested prompts:</span>
        <div className="chips-scroll">
          {currentTemplates.map((template) => (
            <button
              key={template}
              type="button"
              className="chip-prompt"
              onClick={() => applyTemplate(template)}
            >
              {template}
            </button>
          ))}
        </div>
      </div>

      {/* Input Box Form */}
      <form className="chat-input-form card" onSubmit={handleSubmit} aria-label="Chat input form">
        <label htmlFor="chat-prompt-input" className="sr-only" style={{ position: "absolute", width: 1, height: 1, padding: 0, margin: -1, overflow: "hidden", clip: "rect(0,0,0,0)", border: 0 }}>
          Study Assistant Prompt Input
        </label>
        <textarea
          id="chat-prompt-input"
          ref={textareaRef}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (canAsk) handleSubmit(e as unknown as FormEvent<HTMLFormElement>);
            }
          }}
          placeholder={
            documentCount === 0
              ? "Upload a document first to begin studying..."
              : mode === "quiz"
              ? "Ask to generate a quiz (e.g. 'Create a 5-question quiz on Chapter 3')..."
              : "Ask any question from your uploaded notes, slides, or books (Shift+Enter for newline)..."
          }
          rows={3}
          disabled={documentCount === 0}
        />
        <div className="chat-input-footer">
          <span className="input-hint">
            {activeDocument
              ? `🎯 Focused on ${activeDocument.filename}`
              : `🌐 Searching across all ${documentCount} indexed document${documentCount === 1 ? "" : "s"}`}
          </span>
          <button
            type="submit"
            className="btn-send"
            disabled={!canAsk}
          >
            {busy ? "Thinking..." : mode === "quiz" ? "🎯 Generate Quiz" : "💬 Ask Question"}
          </button>
        </div>
      </form>

      {error && <div className="alert alert-danger" role="alert">{error}</div>}
    </div>
  );
}