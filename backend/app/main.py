from __future__ import annotations

import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.rag.graph import RAGPipeline
from app.services.chunking_service import ChunkingService
from app.services.document_service import DocumentService, DocumentTextExtractionError
from app.services.embedding_service import EmbeddingService
from app.services.file_store import DocumentRepository
from app.services.parser_service import DocumentParser
from app.services.vector_store import VectorStoreService

logger = logging.getLogger("studyassistant")
settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DocumentTextExtractionError)
async def document_text_extraction_error_handler(request: Request, exc: DocumentTextExtractionError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.on_event("startup")
def startup() -> None:
    repository = DocumentRepository(settings.metadata_path)
    chunker = ChunkingService(settings.chunk_size, settings.chunk_overlap)

    if settings.gemini_api_key and settings.gemini_api_key.strip():
        try:
            embeddings = EmbeddingService(settings.gemini_api_key, settings.gemini_embedding_model)
            vector_store = VectorStoreService(embeddings.embeddings, settings.vector_store_dir)
            parser = DocumentParser(api_key=settings.gemini_api_key, vision_model=settings.gemini_chat_model)
            document_service = DocumentService(repository, parser, chunker, vector_store, settings.uploads_dir)
            rag_pipeline = RAGPipeline(
                api_key=settings.gemini_api_key,
                chat_model=settings.gemini_chat_model,
                vector_store=vector_store,
                top_k=settings.top_k,
                min_relevance_score=settings.min_relevance_score,
            )
            app.state.vector_store = vector_store
            app.state.document_service = document_service
            app.state.rag_pipeline = rag_pipeline
            logger.info("StudyAssistant services initialized successfully with Gemini API Key.")
        except Exception as exc:
            logger.error(f"Failed to initialize Gemini services: {exc}")
            app.state.vector_store = None
            app.state.document_service = None
            app.state.rag_pipeline = None
    else:
        logger.warning("GEMINI_API_KEY is not set. Service running in degraded mode.")
        app.state.vector_store = None
        app.state.document_service = None
        app.state.rag_pipeline = None

    app.state.settings = settings


app.include_router(api_router, prefix=settings.api_prefix)

frontend_dist: Path | None = None
for candidate in [
    Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
    Path(__file__).resolve().parent.parent / "frontend" / "dist",
    Path("/app/frontend/dist"),
    Path.cwd() / "frontend" / "dist",
    Path.cwd() / "dist",
]:
    if candidate.exists() and candidate.is_dir() and (candidate / "index.html").exists():
        frontend_dist = candidate
        break

if frontend_dist is not None:
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists() and assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        assert frontend_dist is not None
        file_target = frontend_dist / full_path
        if full_path and file_target.exists() and file_target.is_file():
            return FileResponse(file_target)
        return FileResponse(frontend_dist / "index.html")