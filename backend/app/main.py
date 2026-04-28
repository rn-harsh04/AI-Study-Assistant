from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.rag.graph import RAGPipeline
from app.services.chunking_service import ChunkingService
from app.services.document_service import DocumentService
from app.services.document_service import DocumentTextExtractionError
from app.services.embedding_service import EmbeddingService
from app.services.file_store import DocumentRepository
from app.services.parser_service import DocumentParser
from app.services.vector_store import VectorStoreService


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DocumentTextExtractionError)
async def document_text_extraction_error_handler(request: Request, exc: DocumentTextExtractionError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.on_event("startup")
def startup() -> None:
    embeddings = EmbeddingService(settings.gemini_api_key, settings.gemini_embedding_model)
    vector_store = VectorStoreService(embeddings.embeddings, settings.vector_store_dir)
    repository = DocumentRepository(settings.metadata_path)
    parser = DocumentParser(api_key=settings.gemini_api_key, vision_model=settings.gemini_chat_model)
    chunker = ChunkingService(settings.chunk_size, settings.chunk_overlap)
    document_service = DocumentService(repository, parser, chunker, vector_store, settings.uploads_dir)
    rag_pipeline = RAGPipeline(
        api_key=settings.gemini_api_key,
        chat_model=settings.gemini_chat_model,
        vector_store=vector_store,
        top_k=settings.top_k,
        min_relevance_score=settings.min_relevance_score,
    )

    app.state.settings = settings
    app.state.vector_store = vector_store
    app.state.document_service = document_service
    app.state.rag_pipeline = rag_pipeline


app.include_router(api_router, prefix=settings.api_prefix)

