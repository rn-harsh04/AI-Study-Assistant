from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.rag.graph import RAGPipeline
from app.services.document_service import DocumentService
from app.services.vector_store import VectorStoreService


def get_app_settings() -> Settings:
    return get_settings()


def get_document_service(request: Request) -> DocumentService:
    service = getattr(request.app.state, "document_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document service is unavailable. Please set the GEMINI_API_KEY environment variable.",
        )
    return service


def get_vector_store_service(request: Request) -> VectorStoreService:
    service = getattr(request.app.state, "vector_store", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store service is unavailable.",
        )
    return service


def get_rag_pipeline(request: Request) -> RAGPipeline:
    pipeline = getattr(request.app.state, "rag_pipeline", None)
    if pipeline is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG pipeline is unavailable. Please set the GEMINI_API_KEY environment variable.",
        )
    return pipeline