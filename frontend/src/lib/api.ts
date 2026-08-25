export type DocumentRecord = {
  id: string;
  filename: string;
  stored_path: string;
  session_id?: string | null;
  mime_type: string | null;
  status: "ready" | "processing" | "failed" | string;
  chunk_count: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type SourceChunk = {
  document_id: string;
  filename: string;
  chunk_id: number;
  page_number: number | null;
  score: number | null;
  excerpt: string;
};

export type QuizQuestion = {
  question: string;
  options: string[];
  correct_option_index: number;
  explanation: string | null;
};

export type QuizPayload = {
  title: string;
  instructions: string | null;
  questions: QuizQuestion[];
};

export type FlashcardItem = {
  front: string;
  back: string;
  topic?: string | null;
};

export type FlashcardDeck = {
  title: string;
  document_id?: string | null;
  filename?: string | null;
  cards: FlashcardItem[];
};

export type ChatMode = "explain" | "quiz";

export type ChatResponse = {
  answer: string;
  quiz: QuizPayload | null;
  sources: SourceChunk[];
  fallback: boolean;
  retrieved_chunks: number;
  confidence: number | null;
  fallback_reason: string | null;
};

export type DocumentUploadResponse = {
  message: string;
  document: DocumentRecord;
};

export function getSessionId(): string {
  const key = "studyassistant_session_id";
  try {
    let sessionId = localStorage.getItem(key);
    if (!sessionId || sessionId.trim().length === 0) {
      sessionId = "sess_" + crypto.randomUUID().replace(/-/g, "").slice(0, 16);
      localStorage.setItem(key, sessionId);
    }
    return sessionId;
  } catch {
    return "sess_default_client";
  }
}

const envBaseUrl = import.meta.env.VITE_API_BASE_URL;
const API_BASE_URL =
  typeof envBaseUrl === "string" && envBaseUrl.trim().length > 0
    ? envBaseUrl.trim().replace(/\/+$/, "")
    : import.meta.env.DEV
    ? "http://127.0.0.1:8000/api/v1"
    : "/api/v1";

async function parseResponse<T>(response: Response): Promise<T> {
  const text = await response.text();
  if (!response.ok) {
    try {
      const parsed = JSON.parse(text) as { detail?: string };
      throw new Error(parsed.detail || text || `Request failed with status ${response.status}`);
    } catch (e) {
      if (e instanceof Error && e.message !== text) {
        throw e;
      }
      throw new Error(text || `Request failed with status ${response.status}`);
    }
  }

  if (text.trim().startsWith("<")) {
    throw new Error("Unable to connect to FastAPI backend at " + API_BASE_URL + ". Please ensure the backend is running on port 8000.");
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`Invalid JSON response: ${text.slice(0, 100)}`);
  }
}

export async function listDocuments(): Promise<DocumentRecord[]> {
  const response = await fetch(`${API_BASE_URL}/documents`, {
    headers: {
      "X-Session-ID": getSessionId(),
    },
  });
  const payload = await parseResponse<{ documents: DocumentRecord[] }>(response);
  return payload.documents;
}

export async function getDocument(documentId: string): Promise<DocumentRecord> {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
    headers: {
      "X-Session-ID": getSessionId(),
    },
  });
  return parseResponse<DocumentRecord>(response);
}

export async function uploadDocument(file: File): Promise<DocumentRecord> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    headers: {
      "X-Session-ID": getSessionId(),
    },
    body: formData,
  });
  const payload = await parseResponse<DocumentUploadResponse>(response);
  return payload.document;
}

export async function deleteDocument(documentId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
    method: "DELETE",
    headers: {
      "X-Session-ID": getSessionId(),
    },
  });
  await parseResponse<{ message: string; document_id: string }>(response);
}

export async function askQuestion(
  question: string,
  mode: ChatMode = "explain",
  documentId: string | null = null,
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Session-ID": getSessionId(),
    },
    body: JSON.stringify({ question, mode, document_id: documentId, session_id: getSessionId() }),
  });
  return parseResponse<ChatResponse>(response);
}

export async function generateFlashcards(
  documentId: string | null = null,
  count: number = 10,
  topic: string | null = null,
): Promise<FlashcardDeck> {
  const response = await fetch(`${API_BASE_URL}/flashcards/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Session-ID": getSessionId(),
    },
    body: JSON.stringify({ document_id: documentId, count, topic, session_id: getSessionId() }),
  });
  return parseResponse<FlashcardDeck>(response);
}

export async function downloadAnkiDeck(deck: FlashcardDeck): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/flashcards/export/anki`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Session-ID": getSessionId(),
    },
    body: JSON.stringify({ deck }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Failed to generate Anki .apkg export");
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const safeName = (deck.title || "flashcards").replace(/[^\w\-_.]/g, "_");
  a.download = `${safeName}.apkg`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

export async function downloadCsvDeck(deck: FlashcardDeck): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/flashcards/export/csv`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Session-ID": getSessionId(),
    },
    body: JSON.stringify({ deck }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Failed to generate CSV export");
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const safeName = (deck.title || "flashcards").replace(/[^\w\-_.]/g, "_");
  a.download = `${safeName}.csv`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}