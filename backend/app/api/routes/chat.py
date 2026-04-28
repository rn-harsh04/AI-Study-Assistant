from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_rag_pipeline
from app.rag.graph import RAGPipeline
from app.schemas.chat import ChatRequest, ChatResponse, QuizPayload
from app.schemas.document import SourceChunk


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def ask_question(
    payload: ChatRequest,
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline),
) -> ChatResponse:
    result = rag_pipeline.ask_mode(payload.question, payload.mode, payload.document_id)
    sources = [SourceChunk.model_validate(item) for item in result.get("sources", [])]
    quiz_payload = result.get("quiz")
    quiz = QuizPayload.model_validate(quiz_payload) if quiz_payload else None
    return ChatResponse(
        answer=result.get("answer", ""),
        quiz=quiz,
        sources=sources,
        fallback=bool(result.get("fallback", False)),
        retrieved_chunks=len(result.get("retrieved_chunks", [])),
        confidence=result.get("confidence"),
        fallback_reason=result.get("fallback_reason"),
    )
