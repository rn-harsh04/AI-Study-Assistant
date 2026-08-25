export type DocumentRecord = {
  id: string;
  filename: string;
  stored_path: string;
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

const envBaseUrl = import.meta.env.VITE_API_BASE_URL;
const API_BASE_URL =
  typeof envBaseUrl === "string" && envBaseUrl.trim().length > 0
    ? envBaseUrl.trim().replace(/\/+$/, "")
    : "/api/v1";

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    try {
      const parsed = JSON.parse(text) as { detail?: string };
      throw new Error(parsed.detail || text || "Request failed");
    } catch (e) {
      if (e instanceof Error && e.message !== text) {
        throw e;
      }
      throw new Error(text || `Request failed with status ${response.status}`);
    }
  }
  return response.json() as Promise<T>;
}

export async function listDocuments(): Promise<DocumentRecord[]> {
  const response = await fetch(`${API_BASE_URL}/documents`);
  const payload = await parseResponse<{ documents: DocumentRecord[] }>(response);
  return payload.documents;
}

export async function getDocument(documentId: string): Promise<DocumentRecord> {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}`);
  return parseResponse<DocumentRecord>(response);
}

export async function uploadDocument(file: File): Promise<DocumentRecord> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    body: formData,
  });
  const payload = await parseResponse<DocumentUploadResponse>(response);
  return payload.document;
}

export async function deleteDocument(documentId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
    method: "DELETE",
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
    },
    body: JSON.stringify({ question, mode, document_id: documentId }),
  });
  return parseResponse<ChatResponse>(response);
}