from __future__ import annotations
from pydantic import BaseModel, Field


class FlashcardItem(BaseModel):
    front: str = Field(..., description="Front of the card (question, term, or concept)")
    back: str = Field(..., description="Back of the card (definition, formula, or explanation)")
    topic: str | None = Field(default=None, description="Optional topic or tag")


class FlashcardDeck(BaseModel):
    title: str = Field(default="Study Flashcards", description="Deck title")
    document_id: str | None = Field(default=None)
    filename: str | None = Field(default=None)
    cards: list[FlashcardItem] = Field(default_factory=list)


class FlashcardGenerateRequest(BaseModel):
    document_id: str | None = Field(default=None, description="Optional document ID to focus on")
    session_id: str | None = Field(default=None, description="Optional session ID")
    count: int = Field(default=10, ge=3, le=30, description="Number of flashcards to generate")
    topic: str | None = Field(default=None, description="Optional specific topic/chapter focus")


class FlashcardExportRequest(BaseModel):
    deck: FlashcardDeck