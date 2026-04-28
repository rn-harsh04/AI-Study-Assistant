# AI Study Assistant

An AI study assistant that turns uploaded PDFs into a searchable RAG knowledge base. It supports text, PDF images, quiz generation, and grounded explanations powered by FastAPI, LangChain, LangGraph, Gemini, FAISS, and React/Vite.

## Features
- Upload PDF, text, and image files.
- Extract PDF text and PDF images.
- Generate searchable descriptions for images with a vision model.
- Chunk and embed content into FAISS for semantic retrieval.
- Ask for explanations, summaries, or quizzes from the uploaded document.
- Return source snippets so answers stay traceable.
- Show a simple flow: upload once, then chat.

## Project Structure
- `backend/` FastAPI app, RAG pipeline, document parsing, embeddings, and vector store.
- `frontend/` React + Vite UI for upload and chat.
- `data/` persisted uploads, metadata, and FAISS index files.

## Setup
1. Copy `backend/.env.example` to `backend/.env` and set `GEMINI_API_KEY`.
2. Copy `frontend/.env.example` to `frontend/.env` if you want a custom API base URL.
3. Install frontend dependencies:

```bash
cd frontend
npm install
```

4. Install backend dependencies if needed:

```bash
cd backend
pip install -e .
```

5. Start the backend:

```bash
cd backend
uvicorn app.main:app --reload
```

6. Start the frontend:

```bash
cd frontend
npm run dev
```

## Environment Variables
Backend (`backend/.env`):
- `GEMINI_API_KEY` - required.
- `GEMINI_CHAT_MODEL` - default: `gemini-2.5-flash`.
- `GEMINI_EMBEDDING_MODEL` - default: `gemini-embedding-001`.
- `ALLOWED_ORIGINS` - default: `http://localhost:5173`.

Frontend (`frontend/.env`):
- `VITE_API_BASE_URL` - default: `http://127.0.0.1:8000/api/v1`.

## API
- `GET /api/v1/health` - health check.
- `GET /api/v1/documents` - list uploaded documents.
- `POST /api/v1/documents/upload` - upload and index a document.
- `POST /api/v1/chat` - ask a grounded question or request a quiz.
- `POST /api/v1/debug/retrieve` - inspect retrieval results for debugging.

## How It Works
1. Upload a file.
2. The backend saves it and starts parsing/indexing.
3. PDF text and image descriptions are split into chunks.
4. Chunks are embedded and stored in FAISS.
5. Chat requests retrieve the best matching chunks.
6. The LLM answers only from retrieved context.
7. If the answer is not found, the assistant returns: `I don't know`.

## Notes
- Chat is intentionally simple and stateless.
- Image content is searchable through generated descriptions.
- The UI is designed for a single-document upload-to-chat flow.
- Indexing can take a few moments for large PDFs because image description and embedding are done during ingestion.

