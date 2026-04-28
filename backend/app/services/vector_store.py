from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.services.chunking_service import IndexedChunk


class VectorStoreService:
    def __init__(self, embeddings: Any, store_dir: Path) -> None:
        self._embeddings = embeddings
        self._store_dir = store_dir
        self._index_path = store_dir / "faiss_index"
        self._lock = RLock()
        self._store: FAISS | None = None
        self._load()

    def _load(self) -> None:
        if not (self._index_path / "index.faiss").exists():
            self._store = None
            return

        self._store = FAISS.load_local(
            str(self._index_path),
            self._embeddings,
            allow_dangerous_deserialization=True,
        )

    def persist(self) -> None:
        if self._store is None:
            return
        self._index_path.mkdir(parents=True, exist_ok=True)
        self._store.save_local(str(self._index_path))

    def add_chunks(self, chunks: list[IndexedChunk]) -> None:
        if not chunks:
            return

        documents = [Document(page_content=chunk.text, metadata=chunk.metadata) for chunk in chunks]
        with self._lock:
            if self._store is None:
                self._store = FAISS.from_documents(documents, self._embeddings)
            else:
                self._store.add_documents(documents)
            self.persist()

    def search(
        self,
        query: str,
        top_k: int,
        min_relevance_score: float,
        document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            if self._store is None:
                return []

            # Pull a wider candidate set so filtering by document still has enough results.
            search_k = top_k * 8 if document_id else top_k
            results = self._store.similarity_search_with_relevance_scores(query, k=search_k)

        matches: list[dict[str, Any]] = []
        for document, score in results:
            if score < min_relevance_score:
                continue
            metadata = dict(document.metadata)
            if document_id and str(metadata.get("document_id", "")) != document_id:
                continue
            matches.append(
                {
                    "content": document.page_content,
                    "score": float(score),
                    "metadata": metadata,
                }
            )
            if len(matches) >= top_k:
                break
        return matches

