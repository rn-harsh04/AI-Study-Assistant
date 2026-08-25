# AI Study Assistant

An AI study assistant that turns uploaded PDFs into a searchable RAG knowledge base. It supports text extraction, PDF images, practice quiz generation, and grounded explanations powered by FastAPI, LangChain, LangGraph, Google Gemini, FAISS, and React/Vite.

---

## Deploy to Render (1-Click Blueprint)

This repository includes a ready-to-use Render Blueprint (`render.yaml`).

### Deployment Steps:
1. Push this repository to your **GitHub** or **GitLab** account.
2. Go to your [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** in the top right and select **Blueprint**.
4. Connect your repository. Render will automatically detect `render.yaml`.
5. Under Environment Variables, enter your **`GEMINI_API_KEY`** (get one at [Google AI Studio](https://aistudio.google.com/)).
6. Click **Apply**.

Render will automatically build the frontend, install backend dependencies, and launch your live application with health checks enabled!

---

## Features
- **Multimodal Document Ingestion**: Upload PDF, plain text, and image files.
- **Smart Vision Extraction**: Extracts embedded PDF images and generates searchable descriptions with Gemini Vision.
- **Semantic RAG Pipeline**: Chunks and embeds content into FAISS for fast similarity retrieval.
- **Explanations & Quizzes**: Ask for conceptual explanations, summaries, or generate multiple-choice quizzes with answer keys.
- **Traceable Answers**: Displays source snippets and chunk references for transparency.
- **Single Full-Stack Service**: The FastAPI backend serves the React production SPA directly with complete client-side routing.

---

## Project Structure
```
studyassistant/
├── backend/                  # FastAPI app & RAG pipeline
│   ├── app/
│   │   ├── api/              # API routes (chat, documents, health, debug)
│   │   ├── core/             # Configuration & dependency injection
│   │   ├── rag/              # LangGraph RAG pipeline & state
│   │   ├── schemas/          # Pydantic request/response models
│   │   └── services/         # Document parsing, chunking, embedding, vector store
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/                 # React + Vite UI
│   ├── src/                  # Components, API client, styles
│   ├── package.json
│   └── vite.config.ts
├── render.yaml               # Render Blueprint configuration
└── README.md
```

---

## Local Development Setup

### 1. Backend Setup
1. Navigate to `backend/`:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your environment variables:
   ```bash
   cp .env.example .env
   ```
   Set `GEMINI_API_KEY` in `backend/.env`.
5. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### 2. Frontend Setup
1. In a new terminal, navigate to `frontend/`:
   ```bash
   cd frontend
   npm install
   ```
2. Start the Vite dev server:
   ```bash
   npm run dev
   ```
3. Open `http://localhost:5173` in your browser. (The dev server automatically proxies `/api` requests to backend port 8000).

---

## Running with Docker Compose

To run both services in Docker containers:

1. Create `backend/.env` with your `GEMINI_API_KEY`.
2. Run:
   ```bash
   docker compose up --build
   ```
3. Open `http://localhost:5173` in your browser.

---

## Environment Variables

| Variable | Scope | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | Backend | *(Required)* | Google Gemini API key |
| `GEMINI_CHAT_MODEL` | Backend | `gemini-2.5-flash` | Chat and vision model |
| `GEMINI_EMBEDDING_MODEL` | Backend | `gemini-embedding-001` | Text embedding model |
| `DATA_DIR` | Backend | `data` | Directory for uploads and FAISS index |
| `ALLOWED_ORIGINS` | Backend | `*` | Allowed CORS origins |
| `VITE_API_BASE_URL` | Frontend | `/api/v1` | Backend API base URL (defaults to relative `/api/v1`) |

---

## API Endpoints

- `GET /api/v1/health` - Health check & status.
- `GET /api/v1/documents` - List all indexed documents.
- `POST /api/v1/documents/upload` - Upload and index a document.
- `POST /api/v1/chat` - Ask a grounded question or generate a quiz.
- `POST /api/v1/debug/retrieve` - Inspect vector store retrieval for debugging.