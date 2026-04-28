from __future__ import annotations

from collections.abc import Callable
import json
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph

from app.rag.state import GraphState, RetrievedChunk
from app.schemas.chat import QuizPayload
from app.services.vector_store import VectorStoreService


SUPPORTED_CHAT_MODEL = "gemini-2.5-flash"


class RAGPipeline:
    def __init__(
        self,
        *,
        api_key: str,
        chat_model: str,
        vector_store: VectorStoreService,
        top_k: int,
        min_relevance_score: float,
    ) -> None:
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required to initialize the RAG pipeline.")

        self._vector_store = vector_store
        self._top_k = top_k
        self._min_relevance_score = min_relevance_score
        self._llm = ChatGoogleGenerativeAI(
            model=self._normalize_model(chat_model),
            google_api_key=api_key,
            temperature=0.2,
        )
        self._graph = self._build_graph()

    def _normalize_model(self, model: str) -> str:
        legacy_models = {
            "gemini-3.1-flash-lite",
            "gemini-3.1-flash",
            "models/gemini-3.1-flash-lite",
            "models/gemini-3.1-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
        }
        if model in legacy_models:
            return SUPPORTED_CHAT_MODEL
        return model

    def _parse_quiz_payload(self, raw_text: str) -> dict[str, Any]:
        text = raw_text.strip()

        # First try direct JSON.
        try:
            return json.loads(text)
        except Exception:
            pass

        # Try markdown code block extraction.
        fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text, re.IGNORECASE)
        if fenced:
            try:
                return json.loads(fenced.group(1))
            except Exception:
                pass

        # Fallback: parse first JSON object-shaped substring.
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

    def ask_mode(self, question: str, mode: str, document_id: str | None = None) -> dict[str, Any]:
        return self._graph.invoke({"question": question, "mode": mode, "document_id": document_id})

    def _retrieve_context(self, state: GraphState) -> GraphState:
        question = state["question"]
        matches = self._vector_store.search(
            question,
            self._top_k,
            self._min_relevance_score,
            state.get("document_id"),
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
                    "excerpt": str(item["content"]).strip()[:1200],
                }
            )
        return {"retrieved_chunks": chunks, "sources": chunks}

    def _generate_answer(self, state: GraphState) -> GraphState:
        chunks = state.get("retrieved_chunks", [])
        if not chunks:
            return {
                "answer": "I don't know",
                "fallback": True,
                "fallback_reason": "No relevant chunks were retrieved.",
                "confidence": 0.0,
            }

        context_lines = []
        for chunk in chunks:
            page_label = f"page {chunk['page_number']}" if chunk.get("page_number") else "no page"
            context_lines.append(
                f"Source: {chunk['filename']} | chunk {chunk['chunk_id']} | {page_label}\n{chunk['excerpt']}"
            )
        context = "\n\n".join(context_lines)
        mode = state.get("mode", "explain")

        if mode == "quiz":
            system_prompt = (
                "You are a careful study assistant that creates multiple-choice quizzes from the provided context. "
                "Only use facts present in the context. Return valid JSON only, with no markdown fences or extra text."
            )
            human_prompt = (
                "Context:\n{context}\n\n"
                "Create a 5-question quiz with exactly 4 options per question.\n"
                "Return JSON with this shape:\n"
                "{{\n"
                '  "title": "string",\n'
                '  "instructions": "string",\n'
                '  "questions": [\n'
                "    {{\n"
                '      "question": "string",\n'
                '      "options": ["option 1", "option 2", "option 3", "option 4"],\n'
                '      "correct_option_index": 0,\n'
                '      "explanation": "short reason"\n'
                "    }}\n"
                "  ]\n"
                "}}\n"
                "Rules: questions must be grounded in the context, options must be plausible, and correct_option_index must be 0-3."
            )
        else:
            system_prompt = (
                "You are a friendly study buddy. Answer only using the provided context from the uploaded document. "
                "Keep the tone casual, simple, and human. Use short explanations and avoid jargon. "
                "If the context doesn't include the answer, say that clearly in a polite way."
            )
            human_prompt = (
                "Context:\n{context}\n\nQuestion:\n{question}\n\n"
                "Give a basic, easy-to-understand explanation in 3-6 sentences."
            )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", human_prompt),
            ]
        )
        chain = prompt | self._llm
        try:
            result = chain.invoke({"context": context, "question": state["question"]})
            answer = getattr(result, "content", str(result)).strip()
        except Exception as exc:  # pragma: no cover - network/credential failures
            return {
                "answer": "I could not generate a grounded answer because the language model call failed.",
                "fallback": True,
                "fallback_reason": f"Generation failed: {exc}",
                "confidence": 0.0,
            }

        if mode == "quiz":
            try:
                payload = self._parse_quiz_payload(answer)
                quiz = QuizPayload.model_validate(payload)
                return {
                    "answer": "Quiz generated successfully. Solve all questions and submit to see your score.",
                    "quiz": quiz.model_dump(),
                    "confidence": max(chunk["score"] for chunk in chunks),
                }
            except Exception as exc:
                return {
                    "answer": "I could not generate a valid quiz format from the retrieved context.",
                    "fallback": True,
                    "fallback_reason": f"Quiz parsing failed: {exc}",
                    "confidence": 0.0,
                }

        return {"answer": answer, "confidence": max(chunk["score"] for chunk in chunks)}

    def _validate_answer(self, state: GraphState) -> GraphState:
        if state.get("fallback"):
            return state

        answer = state.get("answer", "").strip()
        chunks = state.get("retrieved_chunks", [])
        if not answer or not chunks:
            return {
                "answer": "I don't know",
                "fallback": True,
                "fallback_reason": "Validation found no grounded answer.",
                "confidence": 0.0,
            }

        low_confidence = any(term in answer.lower() for term in ["i'm not sure", "cannot answer", "don't know"])
        if low_confidence:
            return {
                "answer": "I don't know",
                "fallback": True,
                "fallback_reason": "Generated answer appeared ungrounded.",
                "confidence": state.get("confidence", 0.0),
            }

        return {"fallback": False, "fallback_reason": None}

    def _fallback_answer(self, state: GraphState) -> GraphState:
        answer = state.get("answer") or "I don't know"
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
