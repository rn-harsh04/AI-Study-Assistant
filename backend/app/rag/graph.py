from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.core.llm import invoke_gemini_with_fallback
from app.rag.state import GraphState, RetrievedChunk
from app.schemas.chat import QuizPayload
from app.services.vector_store import VectorStoreService

logger = logging.getLogger("studyassistant.rag")
DEFAULT_CHAT_MODEL = "gemini-3.6-flash"


def _extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, str):
                texts.append(block)
            elif isinstance(block, dict) and "text" in block:
                texts.append(str(block["text"]))
            elif hasattr(block, "text"):
                texts.append(str(getattr(block, "text", "")))
        return "\n".join(texts).strip()
    return str(content).strip()


class RAGPipeline:
    def __init__(
        self,
        *,
        api_key: str,
        chat_model: str = DEFAULT_CHAT_MODEL,
        vector_store: VectorStoreService,
        top_k: int = 6,
        min_relevance_score: float = 0.25,
    ) -> None:
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required to initialize the RAG pipeline.")

        self._api_key = api_key
        self._chat_model = chat_model or DEFAULT_CHAT_MODEL
        self._vector_store = vector_store
        self._top_k = top_k
        self._min_relevance_score = min_relevance_score
        self._graph = self._build_graph()

    def _parse_quiz_payload(self, text: str) -> dict[str, Any]:
        fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text, re.IGNORECASE)
        if fenced:
            try:
                return json.loads(fenced.group(1))
            except Exception:
                pass

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            return json.loads(candidate)

        raise ValueError("No JSON object found in quiz response")

    def _build_graph(self):
        graph = StateGraph(GraphState)
        graph.add_node("retrieve", self._retrieve_context)
        graph.add_node("generate", self._generate_answer)
        graph.add_node("validate", self._validate_answer)
        graph.add_node("fallback", self._fallback_answer)

        graph.add_edge(START, "retrieve")
        graph.add_conditional_edges("retrieve", self._route_after_retrieval)
        graph.add_edge("generate", "validate")
        graph.add_conditional_edges("validate", self._route_after_validation)
        graph.add_edge("fallback", END)
        return graph.compile()

    def ask(self, question: str) -> dict[str, Any]:
        return self._graph.invoke({"question": question, "mode": "explain"})

    def ask_mode(
        self,
        question: str,
        mode: str,
        document_id: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        return self._graph.invoke(
            {
                "question": question,
                "mode": mode,
                "document_id": document_id,
                "session_id": session_id,
            }
        )

    def _retrieve_context(self, state: GraphState) -> GraphState:
        question = state["question"]
        mode = state.get("mode", "explain")
        
        is_summary_query = any(w in question.lower() for w in ["summarize", "summary", "overview", "main ideas", "quiz", "topics"])
        effective_k = max(self._top_k + 4, 8) if (mode == "quiz" or is_summary_query) else self._top_k

        matches = self._vector_store.search(
            query=question,
            top_k=effective_k,
            min_relevance_score=self._min_relevance_score,
            document_id=state.get("document_id"),
            session_id=state.get("session_id"),
        )
        chunks: list[RetrievedChunk] = []
        for item in matches:
            metadata = item["metadata"]
            chunks.append(
                {
                    "document_id": str(metadata.get("document_id", "")),
                    "filename": str(metadata.get("filename", "")),
                    "chunk_id": int(metadata.get("chunk_id", 0)),
                    "page_number": metadata.get("page_number"),
                    "score": float(item["score"]),
                    "excerpt": str(item["content"]).strip()[:1400],
                }
            )
        return {"retrieved_chunks": chunks, "sources": chunks}

    def _generate_answer(self, state: GraphState) -> GraphState:
        chunks = state.get("retrieved_chunks", [])
        if not chunks:
            return {
                "answer": "No relevant context was found in your indexed documents to answer this question.",
                "fallback": True,
                "fallback_reason": "No relevant document chunks retrieved.",
                "confidence": 0.0,
            }

        context_lines = []
        for chunk in chunks:
            page_label = f"Page {chunk['page_number']}" if chunk.get("page_number") else "Document"
            context_lines.append(
                f"[{chunk['filename']} | {page_label} | Chunk #{chunk['chunk_id']}]:\n{chunk['excerpt']}"
            )
        context = "\n\n".join(context_lines)
        mode = state.get("mode", "explain")

        if mode == "quiz":
            system_prompt = (
                "You are an expert tutor creating study quizzes. Construct a multiple-choice practice quiz based strictly "
                "on the provided context from the user's uploaded documents. "
                "Output valid JSON only with NO Markdown formatting, explanations, or fences."
            )
            human_prompt = (
                f"Document Context:\n{context}\n\n"
                "Task: Create a 5-question multiple choice quiz with exactly 4 options per question grounded in the text above.\n"
                "Return JSON with this exact format:\n"
                "{\n"
                '  "title": "Practice Quiz: Key Concepts",\n'
                '  "instructions": "Select the single best answer for each question.",\n'
                '  "questions": [\n'
                "    {\n"
                '      "question": "Question text here?",\n'
                '      "options": ["Option A", "Option B", "Option C", "Option D"],\n'
                '      "correct_option_index": 0,\n'
                '      "explanation": "Clear explanation of why this answer is correct based on the text."\n'
                "    }\n"
                "  ]\n"
                "}"
            )
        else:
            system_prompt = (
                "You are an intelligent, approachable AI study assistant. "
                "Answer the user's question clearly, thoroughly, and accurately using ONLY the provided document context. "
                "Structure your answer with clean formatting (bullet points, clear paragraphs, key takeaways) when helpful. "
                "If the context does not contain enough information to answer completely, answer what is known from the context "
                "and clearly mention what information is missing from the document."
            )
            human_prompt = (
                f"Document Context:\n{context}\n\n"
                f"Question: {state['question']}\n\n"
                "Please provide a grounded, comprehensive, and easy-to-understand explanation."
            )

        try:
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
            result = invoke_gemini_with_fallback(
                messages=messages,
                api_key=self._api_key,
                preferred_model=self._chat_model,
                temperature=0.2,
            )
            raw_content = getattr(result, "content", result)
            answer = _extract_text_content(raw_content)
        except Exception as exc:
            err_msg = str(exc)
            logger.error(f"LLM generation failed: {err_msg}")
            friendly_err = (
                "Google Gemini Free Tier daily limit reached (429 RESOURCE_EXHAUSTED). "
                "Please paste a fresh API key in backend/.env from a new Google AI Studio project or enable billing."
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg
                else f"Generation error: {err_msg}"
            )
            return {
                "answer": f"⚠️ **Service Notice**: {friendly_err}",
                "fallback": True,
                "fallback_reason": friendly_err,
                "confidence": 0.0,
            }

        if mode == "quiz":
            try:
                payload = self._parse_quiz_payload(answer)
                quiz = QuizPayload.model_validate(payload)
                return {
                    "answer": "✨ Quiz generated successfully! Answer the questions below and submit to check your score.",
                    "quiz": quiz.model_dump(),
                    "confidence": max(chunk["score"] for chunk in chunks),
                }
            except Exception as exc:
                logger.warning(f"Quiz parsing failed ({exc}), raw response: {answer}")
                return {
                    "answer": answer,
                    "quiz": None,
                    "fallback": False,
                    "confidence": max(chunk["score"] for chunk in chunks),
                }

        return {"answer": answer, "confidence": max(chunk["score"] for chunk in chunks)}

    def _validate_answer(self, state: GraphState) -> GraphState:
        if state.get("fallback"):
            return state

        answer = state.get("answer", "").strip()
        chunks = state.get("retrieved_chunks", [])
        if not answer or not chunks:
            return {
                "answer": "I was unable to find sufficient grounded context in the document to answer your question.",
                "fallback": True,
                "fallback_reason": "No grounded answer produced.",
                "confidence": 0.0,
            }

        return {"fallback": False, "fallback_reason": None}

    def _fallback_answer(self, state: GraphState) -> GraphState:
        answer = state.get("answer") or "I could not find enough relevant context in the uploaded documents."
        return {
            "answer": answer,
            "sources": state.get("sources", []),
            "fallback": True,
            "fallback_reason": state.get("fallback_reason") or "Fallback response used.",
            "confidence": state.get("confidence", 0.0),
        }

    def _route_after_retrieval(self, state: GraphState) -> str:
        if not state.get("retrieved_chunks"):
            return "fallback"
        return "generate"

    def _route_after_validation(self, state: GraphState) -> str:
        if state.get("fallback"):
            return "fallback"
        return END