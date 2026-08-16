from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

from app.schemas.document import SourceChunk


class QuizQuestion(BaseModel):
    question: str = Field(min_length=1)
    options: list[str] = Field(min_length=2)
    correct_option_index: int = Field(ge=0)
    explanation: str | None = None


class QuizPayload(BaseModel):
    title: str = Field(min_length=1)
    instructions: str | None = None
    questions: list[QuizQuestion] = Field(min_length=1)


class IngestRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    mode: Literal["explain", "quiz"] = "explain"
    document_id: str | None = None
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    quiz: QuizPayload | None = None
    sources: list[SourceChunk] = Field(default_factory=list)
    fallback: bool = False
    retrieved_chunks: int = 0
    confidence: float | None = None
    fallback_reason: str | None = None
