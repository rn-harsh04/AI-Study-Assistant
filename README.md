# AI Study Assistant

An AI-powered study assistant that transforms uploaded study materials (PDFs, plain text, and images) into an interactive, searchable RAG (Retrieval-Augmented Generation) knowledge base. It provides conceptual explanations, grounded summaries, and practice quizzes with answers and explanations powered by FastAPI, LangChain, LangGraph, Google Gemini, FAISS vector search, and React/Vite.

---

## Features

- **Multimodal Document Parsing**: Ingests PDF documents, plain text notes, and image files.
- **Vision-Powered Diagram Extraction**: Automatically detects embedded PDF images and generates searchable semantic descriptions using Gemini Vision models.
- **Semantic Vector Retrieval**: Chunks content and embeds it into a local FAISS index for high-precision similarity retrieval.
- **Interactive Explanations & Quizzes**:
  - **Explain Mode**: Provides concise, grounded answers and concept breakdowns.
  - **Quiz Mode**: Automatically generates multiple-choice quizzes with options, correct answers, and explanations.
- **Source Traceability**: Displays source snippets and document references alongside answers so students can verify facts.
- **Unified Full-Stack App**: FastAPI directly serves the React SPA production build with complete client-side routing and fallback support.

---

## Architecture & How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                       React / Vite UI                       │
│  (Upload Panel, Document Selection, Chat & Quiz Interface)  │
└──────────────────────────────┬──────────────────────────────┘
                               │ REST API (/api/v1)
┌──────────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend Router                   │
└──────┬──────────────────────┬──────────────────────┬────────┘
       │                      │                      │
┌──────▼──────┐       ┌───────▼────────┐      ┌──────▼───────┐
│ /documents  │       │     /chat      │      │   /health    │
└──────┬──────┘       └───────┬────────┘      └──────────────┘
       │                      │
┌──────▼──────────────────────▼───────────────────────────────┐
│                      Document Service                       │
│  - DocumentParser (pypdf + Gemini Vision)                   │
│  - ChunkingService (Token / Character Splitting)            │
│  - VectorStoreService (Google GenAI Embeddings + FAISS)     │
│  - FileStore (Metadata Repository)                          │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                 LangGraph RAG State Pipeline                │
│  1. Retrieve relevant chunks from FAISS                     │
│  2. Build grounded context prompt                           │
│  3. Generate Explanation / Quiz via ChatGoogleGenerativeAI   │
└─────────────────────────────────────────────────────────────┘
```

### Pipeline Flow:
1. **Upload & Ingestion**:
   - Files are uploaded to `/api/v1/documents/upload`.
   - Text is extracted from PDF pages. Embedded images are sent to Gemini Vision to generate textual descriptions.
   - Text and image descriptions are chunked and tagged with page numbers and document IDs.
2. **Indexing**:
   - Chunks are embedded with `gemini-embedding-001` and indexed in FAISS (`data/vector_store/faiss_index`).
   - Document metadata is stored in `data/documents.json`.
3. **Retrieval & Chat (RAG)**:
   - Queries are submitted to `/api/v1/chat` with either `explain` or `quiz` mode.
   - The RAG pipeline performs similarity search in FAISS against the selected document or full corpus.
   - Retrieved chunks and the query are passed to the Gemini LLM graph to construct a grounded response or structured quiz.

---

## Project Structure

```
studyassistant/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── router.py          # API route aggregator
│   │   │   └── routes/            # Route handlers (chat, documents, health, debug)
│   │   ├── core/
│   │   │   ├── config.py          # App settings & dynamic path configuration
│   │   │   └── deps.py            # FastAPI dependency injection
│   │   ├── rag/
│   │   │   ├── graph.py           # LangGraph RAG pipeline definition
│   │   │   └── state.py           # Typed graph state definitions
│   │   ├── schemas/               # Pydantic data validation schemas
│   │   ├── services/              # Ingestion, parsing, chunking, embeddings, FAISS
│   │   └── main.py                # FastAPI app & static SPA server
│   ├── tests/                     # Backend API & unit tests
│   ├── Dockerfile                 # Backend container definition
│   ├── pyproject.toml             # Python build configuration
│   └── requirements.txt           # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/            # React UI components (Upload, Chat, Sources)
│   │   ├── lib/api.ts             # API client functions & TypeScript types
│   │   ├── App.tsx                # Main application component
│   │   ├── main.tsx               # React DOM root entrypoint
│   │   └── styles.css             # Application styling
│   ├── package.json               # Node dependencies & build scripts
│   └── vite.config.ts             # Vite configuration & dev server proxy
├── data/                          # Uploads, metadata, and FAISS indices
├── docker-compose.yml             # Multi-container orchestration
└── render.yaml                    # Cloud deployment blueprint
```

---

## Running Locally

### 1. Backend Setup

1. Open a terminal and navigate to `backend/`:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set your environment variables in `backend/.env`:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_CHAT_MODEL=gemini-2.5-flash
   GEMINI_EMBEDDING_MODEL=gemini-embedding-001
   ```
5. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### 2. Frontend Setup

1. In a separate terminal, navigate to `frontend/`:
   ```bash
   cd frontend
   ```
2. Install frontend dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
4. Open `http://localhost:5173` in your browser. (The development server proxies `/api` requests to `http://127.0.0.1:8000`).

---

## Running with Docker Compose

To build and start both the frontend and backend with Docker:

```bash
docker compose up --build
```

Access the application:
- **Web UI**: `http://localhost:5173`
- **Backend API**: `http://localhost:8000/api/v1`

---

## Environment Variables

| Variable | Scope | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | Backend | *(Required)* | Google Gemini API key from Google AI Studio |
| `GEMINI_CHAT_MODEL` | Backend | `gemini-2.5-flash` | LLM for chat explanations, quizzes, and vision parsing |
| `GEMINI_EMBEDDING_MODEL` | Backend | `gemini-embedding-001` | Embedding model for semantic vector indexing |
| `DATA_DIR` | Backend | `data` | Directory for persisted uploads, metadata, and FAISS vectors |
| `ALLOWED_ORIGINS` | Backend | `*` | Allowed CORS origins |
| `VITE_API_BASE_URL` | Frontend | `/api/v1` | Base URL for API requests (defaults to relative `/api/v1`) |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Health check endpoint |
| `GET` | `/api/v1/documents` | List all uploaded documents and their processing status |
| `POST` | `/api/v1/documents/upload` | Upload and trigger asynchronous document indexing |
| `POST` | `/api/v1/chat` | Query the RAG pipeline in `explain` or `quiz` mode |
| `POST` | `/api/v1/debug/retrieve` | Inspect raw vector search hits and relevance scores |