from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentRecord(BaseModel):
    id: str
    filename: str
    stored_path: str
    mime_type: str | None = None
    status: str = "ready"
    chunk_count: int = 0
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class SourceChunk(BaseModel):
    document_id: str
    filename: str
    chunk_id: int
    page_number: int | None = None
    score: float | None = None
    excerpt: str = Field(default="")


class DocumentUploadResponse(BaseModel):
    message: str = "Document indexed successfully"
    document: DocumentRecord


class DocumentListResponse(BaseModel):
    documents: list[DocumentRecord] = Field(default_factory=list)
