from __future__ import annotations

from fastapi import APIRouter, Depends, Header

from app.core.deps import get_rag_pipeline
from app.rag.graph import RAGPipeline
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def ask_question(
    payload: ChatRequest,
    session_id: str | None = Header(default=None, alias="X-Session-ID"),
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline),
) -> ChatResponse:
    target_session = payload.session_id or session_id
    result = rag_pipeline.ask_mode(
        question=payload.question,
        mode=payload.mode,
        document_id=payload.document_id,
        session_id=target_session,
    )
    return ChatResponse(
        answer=result["answer"],
        quiz=result.get("quiz"),
        sources=result.get("sources", []),
        fallback=result.get("fallback", False),
        retrieved_chunks=len(result.get("retrieved_chunks", [])),
        confidence=result.get("confidence"),
        fallback_reason=result.get("fallback_reason"),
    )