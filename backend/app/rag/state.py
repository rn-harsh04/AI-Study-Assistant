from __future__ import annotations

from typing import TypedDict


class RetrievedChunk(TypedDict, total=False):
    document_id: str
    filename: str
    chunk_id: int
    page_number: int | None
    score: float
    excerpt: str


class GraphState(TypedDict, total=False):
    question: str
    mode: str
    document_id: str | None
    retrieved_chunks: list[RetrievedChunk]
    answer: str
    quiz: dict
    sources: list[RetrievedChunk]
    fallback: bool
    fallback_reason: str
    confidence: float | None
