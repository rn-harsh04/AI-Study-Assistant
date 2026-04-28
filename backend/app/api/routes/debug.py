from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from pydantic import BaseModel, Field

from app.core.deps import get_rag_pipeline, get_document_service
from app.rag.graph import RAGPipeline
from app.services.vector_store import VectorStoreService


router = APIRouter(prefix="/debug", tags=["debug"])


class RetrieveRequest(BaseModel):
    question: str = Field(min_length=1)
    document_id: str | None = None
    top_k: int = 12


class RetrieveHit(BaseModel):
    content: str
    score: float
    metadata: dict[str, Any]


class RetrieveResponse(BaseModel):
    hits: list[RetrieveHit]


@router.post("/retrieve", response_model=RetrieveResponse)
def debug_retrieve(
    payload: RetrieveRequest,
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline),
) -> RetrieveResponse:
    # Access the vector store from the pipeline
    vector_store: VectorStoreService = rag_pipeline._vector_store  # type: ignore[attr-defined]

    # Defensive: ensure vector store exists
    if vector_store is None:
        raise HTTPException(status_code=500, detail="Vector store is not initialized")

    results = vector_store.search(payload.question, payload.top_k, 0.0, payload.document_id)

    hits = [RetrieveHit(content=item["content"], score=item["score"], metadata=item["metadata"]) for item in results]
    return RetrieveResponse(hits=hits)
