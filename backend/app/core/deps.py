from __future__ import annotations

from fastapi import Request

from app.core.config import Settings, get_settings
from app.rag.graph import RAGPipeline
from app.services.document_service import DocumentService


def get_app_settings() -> Settings:
    return get_settings()


def get_document_service(request: Request) -> DocumentService:
    return request.app.state.document_service


def get_rag_pipeline(request: Request) -> RAGPipeline:
    return request.app.state.rag_pipeline
