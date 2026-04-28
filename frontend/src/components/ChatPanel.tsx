import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { askQuestion, type ChatMode, type ChatResponse, type DocumentRecord, type QuizPayload } from "../lib/api";
import SourcesList from "./SourcesList";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type ChatPanelProps = {
  documentCount: number;
  activeDocument: DocumentRecord | null;
  uploadTrigger?: number;
};

export default function ChatPanel({ documentCount, activeDocument, uploadTrigger = 0 }: ChatPanelProps) {
  // Focus chat input and add a short assistant prompt when a new upload completes
  const prevUpload = useRef<number>(0);

  useEffect(() => {
    if (uploadTrigger && uploadTrigger > prevUpload.current) {
      prevUpload.current = uploadTrigger;
      // add a short assistant signal and focus the textarea
      setMessages((current) => [
        ...current.filter((m) => m.id !== "welcome"),
        { id: `uploaded-${uploadTrigger}`, role: "assistant", content: "Document indexed — ask anything about it." },
      ]);
      // focus the input after a short delay to ensure UI updated
      setTimeout(() => textareaRef.current?.focus(), 80);
    }
  }, [uploadTrigger]);
  const [mode, setMode] = useState<ChatMode>("explain");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Upload documents first, then ask questions. I will answer only from retrieved context.",
    },
  ]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sources, setSources] = useState<ChatResponse["sources"]>([]);
  const [fallback, setFallback] = useState(false);
  const [fallbackReason, setFallbackReason] = useState<string | null>(null);
  const [quiz, setQuiz] = useState<QuizPayload | null>(null);
  const [selectedOptions, setSelectedOptions] = useState<Array<number | null>>([]);
  const [quizSubmitted, setQuizSubmitted] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const promptTemplates = [
    "Explain the most important ideas in simple terms.",
    "Generate a 5-question quiz with answers from the uploaded document.",
    "Summarize the document in short study notes and call out any key terms.",
  ];

  const canAsk = useMemo(
    () => question.trim().length > 0 && !busy && Boolean(activeDocument),
    [question, busy, activeDocument],
  );

  function applyTemplate(template: string) {
    setQuestion(template);
    textareaRef.current?.focus();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || busy) {
      return;
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
    };

    setMessages((current) => [...current, userMessage]);
    setQuestion("");
    setBusy(true);
    setError(null);

    try {
      const response = await askQuestion(trimmed, mode, activeDocument?.id ?? null);
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: "assistant", content: response.answer },
      ]);
      if (mode === "quiz" && response.quiz) {
        setQuiz(response.quiz);
        setSelectedOptions(new Array(response.quiz.questions.length).fill(null));
        setQuizSubmitted(false);
      } else {
        setQuiz(null);
        setSelectedOptions([]);
        setQuizSubmitted(false);
      }
      setSources(response.sources);
      setFallback(response.fallback);
      setFallbackReason(response.fallback_reason);
    } catch (askError) {
      setError(askError instanceof Error ? askError.message : "Unable to reach the assistant");
    } finally {
      setBusy(false);
    }
  }

  const allQuestionsAnswered = useMemo(() => {
    if (!quiz || selectedOptions.length === 0) {
      return false;
    }
    return selectedOptions.every((value) => value !== null);
  }, [quiz, selectedOptions]);

  const score = useMemo(() => {
    if (!quizSubmitted || !quiz) {
      return 0;
    }
    return quiz.questions.reduce((total, question, index) => {
      return total + (selectedOptions[index] === question.correct_option_index ? 1 : 0);
    }, 0);
  }, [quizSubmitted, quiz, selectedOptions]);

  function chooseOption(questionIndex: number, optionIndex: number) {
    if (quizSubmitted) {
      return;
    }
    setSelectedOptions((current) => {
      const next = [...current];
      next[questionIndex] = optionIndex;
      return next;
    });
  }

  function submitQuiz() {
    if (!allQuestionsAnswered) {
      return;
    }
    setQuizSubmitted(true);
  }

  return (
    <section className="card chat-shell">
      <div className="section-heading">
        <span className="eyebrow">Chat</span>
        <h2>Explain or quiz the material</h2>
        <p className="muted">{documentCount} document{documentCount === 1 ? "" : "s"} indexed</p>
        {activeDocument ? <p className="muted">Using context: {activeDocument.filename}</p> : null}
      </div>

      <div className="mode-toggle" role="tablist" aria-label="assistant mode">
        <button type="button" className={mode === "explain" ? "chip active" : "chip"} onClick={() => setMode("explain")}>
          Explain
        </button>
        <button type="button" className={mode === "quiz" ? "chip active" : "chip"} onClick={() => setMode("quiz")}>
          Quiz me
        </button>
      </div>

      <div className="prompt-chips" aria-label="study prompts">
        {promptTemplates.map((template) => (
          <button key={template} type="button" className="chip" onClick={() => applyTemplate(template)}>
            {template}
          </button>
        ))}
      </div>

      <div className="messages" aria-live="polite">
        {messages.map((message) => (
          <article key={message.id} className={`message ${message.role}`}>
            {message.content}
          </article>
        ))}
      </div>

      <form className="stack" onSubmit={handleSubmit}>
        <textarea
          ref={textareaRef}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder={mode === "quiz" ? "Ask for a quiz or practice questions" : "Ask for an explanation, summary, or concept breakdown"}
          rows={4}
        />
        <button type="submit" disabled={!canAsk}>
          {busy ? "Thinking..." : mode === "quiz" ? "Generate quiz" : "Ask"}
        </button>
      </form>

      {!activeDocument ? <p className="muted">Upload a PDF first so explanations come from that file.</p> : null}

      {quiz ? (
        <section className="quiz-shell">
          <div className="quiz-header">
            <h3>{quiz.title}</h3>
            {quiz.instructions ? <p className="muted">{quiz.instructions}</p> : null}
          </div>

          <div className="quiz-list">
            {quiz.questions.map((item, questionIndex) => (
              <article key={`${item.question}-${questionIndex}`} className="quiz-item">
                <p className="quiz-question">
                  {questionIndex + 1}. {item.question}
                </p>
                <div className="quiz-options">
                  {item.options.map((option, optionIndex) => {
                    const selected = selectedOptions[questionIndex] === optionIndex;
                    const isCorrect = item.correct_option_index === optionIndex;
                    const showCorrect = quizSubmitted && isCorrect;
                    const showWrong =
                      quizSubmitted &&
                      selected &&
                      selectedOptions[questionIndex] !== item.correct_option_index;

                    const classes = [
                      "quiz-option",
                      selected ? "selected" : "",
                      showCorrect ? "correct" : "",
                      showWrong ? "wrong" : "",
                    ]
                      .filter(Boolean)
                      .join(" ");

                    return (
                      <button
                        key={`${option}-${optionIndex}`}
                        type="button"
                        className={classes}
                        onClick={() => chooseOption(questionIndex, optionIndex)}
                      >
                        {option}
                      </button>
                    );
                  })}
                </div>
                {quizSubmitted && item.explanation ? <p className="quiz-explanation">{item.explanation}</p> : null}
              </article>
            ))}
          </div>

          <div className="quiz-actions">
            <button type="button" onClick={submitQuiz} disabled={!allQuestionsAnswered || quizSubmitted}>
              {quizSubmitted ? "Submitted" : "Submit quiz"}
            </button>
            {quizSubmitted ? (
              <p className="quiz-score">
                Score: {score}/{quiz.questions.length}
              </p>
            ) : (
              <p className="muted">Select one option per question to submit.</p>
            )}
          </div>
        </section>
      ) : null}

      {error ? <p className="error">{error}</p> : null}
      {fallback ? <p className="fallback">Fallback used{fallbackReason ? `: ${fallbackReason}` : ""}</p> : null}
      <SourcesList sources={sources} />
    </section>
  );
}

