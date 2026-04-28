# AI Study Assistant

Production-oriented study assistant scaffold with FastAPI, React/Vite, LangChain, LangGraph, Gemini, and FAISS.

## Implemented
- PDF and text uploads
- Parsing, chunking, and FAISS indexing
- LangGraph retrieve -> generate -> validate -> fallback pipeline
- React upload and chat UI with source display

## Structure
- `backend/` FastAPI RAG service
- `frontend/` React chat UI
- `data/` persisted uploads and vector store files

## Setup
1. Copy `backend/.env.example` to `backend/.env` and set `GEMINI_API_KEY`.
2. Run `npm install` in `frontend/`.
3. Start the backend from `backend/` with Uvicorn.
4. Start the frontend from `frontend/` with Vite.

## Environment
- `GEMINI_API_KEY`
- `GEMINI_CHAT_MODEL` (default: `gemini-3.1-flash-lite`)
- `GEMINI_EMBEDDING_MODEL` (default: `gemini-embedding-001`)
- `ALLOWED_ORIGINS` (default: `http://localhost:5173`)
- `VITE_API_BASE_URL` (default: `http://localhost:8000/api/v1`)

