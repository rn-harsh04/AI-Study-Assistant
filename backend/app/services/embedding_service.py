from __future__ import annotations

from langchain_google_genai import GoogleGenerativeAIEmbeddings


SUPPORTED_EMBEDDING_MODEL = "gemini-embedding-001"


class EmbeddingService:
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required to initialize embeddings.")

        normalized_model = self._normalize_model(model)
        self._embeddings = GoogleGenerativeAIEmbeddings(model=normalized_model, google_api_key=api_key)

    def _normalize_model(self, model: str) -> str:
        legacy_models = {"models/text-embedding-004", "text-embedding-004", "models/embedding-001"}
        if model in legacy_models:
            return SUPPORTED_EMBEDDING_MODEL
        return model

    @property
    def embeddings(self) -> GoogleGenerativeAIEmbeddings:
        return self._embeddings
