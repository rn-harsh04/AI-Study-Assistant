from __future__ import annotations

import csv
import io
import json
import logging
import random
import re
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
import genanki
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import get_settings
from app.core.deps import get_document_service, get_vector_store_service
from app.core.llm import invoke_gemini_with_fallback
from app.rag.graph import _extract_text_content
from app.schemas.flashcard import (
    FlashcardDeck,
    FlashcardExportRequest,
    FlashcardGenerateRequest,
    FlashcardItem,
)
from app.services.document_service import DocumentService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger("studyassistant.flashcards")
router = APIRouter(prefix="/flashcards", tags=["flashcards"])


def _parse_flashcards_json(text: str) -> list[dict[str, Any]]:
    fenced = re.search(r"```(?:json)?\s*(\[[\s\S]*\]|\{[\s\S]*\})\s*```", text, re.IGNORECASE)
    raw = fenced.group(1) if fenced else text

    start_arr = raw.find("[")
    end_arr = raw.rfind("]")
    if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
        try:
            return json.loads(raw[start_arr : end_arr + 1])
        except Exception:
            pass

    start_obj = raw.find("{")
    end_obj = raw.rfind("}")
    if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
        try:
            data = json.loads(raw[start_obj : end_obj + 1])
            if isinstance(data, dict) and "cards" in data and isinstance(data["cards"], list):
                return data["cards"]
        except Exception:
            pass

    raise ValueError("Could not parse flashcards JSON from model response")


@router.post(
    "/generate",
    response_model=FlashcardDeck,
    status_code=status.HTTP_200_OK,
)
def generate_flashcards(
    payload: FlashcardGenerateRequest,
    session_id: str | None = Header(default=None, alias="X-Session-ID"),
    vector_store: VectorStoreService = Depends(get_vector_store_service),
    document_service: DocumentService = Depends(get_document_service),
) -> FlashcardDeck:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GEMINI_API_KEY is not configured.",
        )

    target_session = payload.session_id or session_id
    filename = "Study Materials"
    chunk_texts: list[str] = []

    if payload.document_id:
        doc = document_service.get_document(payload.document_id, session_id=target_session)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {payload.document_id} not found.",
            )
        filename = doc.filename
        raw_chunks = vector_store.get_document_chunks(payload.document_id, limit=20, session_id=target_session)
        for item in raw_chunks:
            if isinstance(item, dict) and "content" in item:
                chunk_texts.append(str(item["content"]).strip())
            else:
                chunk_texts.append(str(item).strip())
    else:
        query = payload.topic or "key concepts definitions formulas main ideas"
        matches = vector_store.search(query, top_k=15, session_id=target_session)
        for m in matches:
            if isinstance(m, dict) and "content" in m:
                chunk_texts.append(str(m["content"]).strip())
            else:
                chunk_texts.append(str(m).strip())

    if not chunk_texts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No document context found to generate flashcards. Please upload and index documents first.",
        )

    context = "\n\n---\n\n".join(chunk_texts[:12])

    system_prompt = (
        "You are an expert tutor specializing in active recall and spaced repetition flashcards. "
        "Create concise, high-yield study flashcards based strictly on the provided context.\n"
        "Rules:\n"
        "- Front: Clear question, definition prompt, or concept (1-2 lines max).\n"
        "- Back: Concise, precise answer or explanation (1-3 sentences max).\n"
        "- Output strictly valid JSON with no markdown formatting or fences."
    )

    human_prompt = (
        f"Context from study material:\n{context}\n\n"
        f"Task: Generate exactly {payload.count} high-yield active-recall flashcards.\n"
        f"Focus topic: {payload.topic or 'All core concepts'}\n\n"
        "Return a JSON array formatted exactly like this:\n"
        "[\n"
        '  {"front": "What is the primary function of Mitochondria?", "back": "Generates most of the chemical energy (ATP) needed to power biochemical reactions via cellular respiration.", "topic": "Cell Biology"},\n'
        '  {"front": "Define Supervised Learning", "back": "A machine learning paradigm where models are trained on labeled data pairs (input-output) to learn a mapping function.", "topic": "Machine Learning"}\n'
        "]"
    )

    try:
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
        result = invoke_gemini_with_fallback(
            messages=messages,
            api_key=settings.gemini_api_key,
            preferred_model=settings.gemini_chat_model,
            temperature=0.3,
        )
        raw_text = _extract_text_content(result.content)
        parsed_cards = _parse_flashcards_json(raw_text)
    except Exception as exc:
        err_msg = str(exc)
        logger.error(f"Flashcard generation failed: {err_msg}")
        friendly_err = (
            "Google Gemini Free Tier daily limit reached (429 RESOURCE_EXHAUSTED). "
            "Please paste a fresh API key in backend/.env from a new Google AI Studio project or enable billing."
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg
            else f"Flashcard generation failed: {err_msg}"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS if "429" in err_msg else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=friendly_err,
        )

    cards = []
    for item in parsed_cards:
        if isinstance(item, dict) and "front" in item and "back" in item:
            cards.append(
                FlashcardItem(
                    front=str(item["front"]).strip(),
                    back=str(item["back"]).strip(),
                    topic=str(item.get("topic", "")).strip() or None,
                )
            )

    deck_title = f"{filename} - Study Deck"
    return FlashcardDeck(
        title=deck_title,
        document_id=payload.document_id,
        filename=filename,
        cards=cards,
    )


@router.post("/export/anki")
def export_anki(payload: FlashcardExportRequest) -> Response:
    deck_data = payload.deck
    if not deck_data.cards:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deck contains no cards to export.")

    deck_id = random.randrange(1 << 30, 1 << 31)
    deck_title = deck_data.title or "AI Study Assistant Deck"
    deck = genanki.Deck(deck_id, deck_title)

    model_id = 1607392319
    anki_model = genanki.Model(
        model_id,
        "AI Study Assistant Flashcard Model",
        fields=[
            {"name": "Front"},
            {"name": "Back"},
            {"name": "Topic"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": (
                    '<div class="card front-card">'
                    '<div class="badge">{{Topic}}</div>'
                    '<div class="question">{{Front}}</div>'
                    "</div>"
                ),
                "afmt": (
                    '{{FrontSide}}<hr id="answer">'
                    '<div class="card back-card">'
                    '<div class="answer">{{Back}}</div>'
                    "</div>"
                ),
            },
        ],
        css="""
        .card {
            font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
            text-align: center;
            color: #f8fafc;
            background-color: #0f172a;
            padding: 24px;
            border-radius: 12px;
            font-size: 18px;
            line-height: 1.6;
        }
        .badge {
            display: inline-block;
            font-size: 12px;
            font-weight: 700;
            color: #38bdf8;
            background: rgba(56, 189, 248, 0.15);
            padding: 4px 10px;
            border-radius: 999px;
            margin-bottom: 16px;
            text-transform: uppercase;
        }
        .question {
            font-weight: 700;
            color: #ffffff;
            font-size: 20px;
        }
        .answer {
            color: #e2e8f0;
            margin-top: 12px;
        }
        hr#answer {
            border: none;
            border-top: 1px solid rgba(255, 255, 255, 0.15);
            margin: 16px 0;
        }
        """,
    )

    for card in deck_data.cards:
        note = genanki.Note(
            model=anki_model,
            fields=[card.front, card.back, card.topic or "Study"],
        )
        deck.add_note(note)

    package = genanki.Package(deck)
    buf = io.BytesIO()
    package.write_to_file(buf)
    apkg_bytes = buf.getvalue()

    safe_filename = re.sub(r"[^\w\-_.]", "_", deck_title) + ".apkg"
    return Response(
        content=apkg_bytes,
        media_type="application/apkg",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.post("/export/csv")
def export_csv(payload: FlashcardExportRequest) -> Response:
    deck_data = payload.deck
    if not deck_data.cards:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deck contains no cards to export.")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Front", "Back", "Topic"])
    for card in deck_data.cards:
        writer.writerow([card.front, card.back, card.topic or ""])

    csv_bytes = output.getvalue().encode("utf-8")
    safe_filename = re.sub(r"[^\w\-_.]", "_", deck_data.title or "flashcards") + ".csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )