from __future__ import annotations

import logging
from typing import Any

from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

logger = logging.getLogger("studyassistant.embeddings")

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


class EmbeddingService:
    def __init__(self, api_key: str | None = None, model: str = DEFAULT_EMBEDDING_MODEL) -> None:
        """Local CPU-based embedding service using FastEmbed.

        Runs 100% offline with zero Google API rate limits and high retrieval accuracy.
        """
        self._model = model if model and "gemini" not in model else DEFAULT_EMBEDDING_MODEL
        try:
            self._embeddings = FastEmbedEmbeddings(model_name=self._model)
            logger.info(f"Initialized local FastEmbed embeddings model: {self._model}")
        except Exception as exc:
            logger.warning(f"Error loading FastEmbed model '{self._model}': {exc}. Using default '{DEFAULT_EMBEDDING_MODEL}'.")
            self._embeddings = FastEmbedEmbeddings(model_name=DEFAULT_EMBEDDING_MODEL)

    @property
    def embeddings(self) -> Any:
        return self._embeddings