from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Any
import logging

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.services.chunking_service import IndexedChunk

logger = logging.getLogger("studyassistant.vector_store")


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

        try:
            self._store = FAISS.load_local(
                str(self._index_path),
                self._embeddings,
                allow_dangerous_deserialization=True,
            )
        except Exception as exc:
            logger.error(f"Error loading vector store: {exc}")
            self._store = None

    def persist(self) -> None:
        if self._store is None:
            return
        try:
            self._index_path.mkdir(parents=True, exist_ok=True)
            self._store.save_local(str(self._index_path))
        except Exception as exc:
            logger.error(f"Error persisting vector store: {exc}")

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

    def delete_document(self, document_id: str) -> None:
        with self._lock:
            if self._store is None or not hasattr(self._store, "docstore"):
                return
            try:
                docstore_dict = getattr(self._store.docstore, "_dict", {})
                ids_to_delete = [
                    doc_id for doc_id, doc in docstore_dict.items()
                    if str(getattr(doc, "metadata", {}).get("document_id", "")) == document_id
                ]
                if ids_to_delete:
                    self._store.delete(ids_to_delete)
                    self.persist()
                    logger.info(f"Deleted {len(ids_to_delete)} vectors for document {document_id}")
            except Exception as exc:
                logger.error(f"Error deleting vectors for document {document_id}: {exc}")

    def get_document_chunks(self, document_id: str, limit: int = 10, session_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            if self._store is None or not hasattr(self._store, "docstore"):
                return []
            docstore_dict = getattr(self._store.docstore, "_dict", {})
            matching_docs = []
            for doc in docstore_dict.values():
                meta = getattr(doc, "metadata", {})
                if str(meta.get("document_id", "")) == document_id:
                    if session_id and meta.get("session_id") and meta.get("session_id") != session_id:
                        continue
                    matching_docs.append(doc)

            if not matching_docs:
                return []
            
            matching_docs.sort(key=lambda d: int(d.metadata.get("chunk_id", 0)))
            
            if len(matching_docs) <= limit:
                selected = matching_docs
            else:
                step = len(matching_docs) / float(limit)
                selected = [matching_docs[int(i * step)] for i in range(limit)]

            return [
                {
                    "content": doc.page_content,
                    "score": 1.0,
                    "metadata": dict(doc.metadata),
                }
                for doc in selected
            ]

    def search(
        self,
        query: str,
        top_k: int = 6,
        min_relevance_score: float = 0.25,
        document_id: str | None = None,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            if self._store is None:
                return []

            is_broad_query = any(w in query.lower() for w in ["summarize", "summary", "overview", "main ideas", "what is this", "quiz", "tell me about"])
            search_k = max(top_k * 15, 60) if document_id else max(top_k * 4, 30)
            
            try:
                raw_results = self._store.similarity_search_with_relevance_scores(query, k=search_k)
            except Exception as exc:
                logger.warning(f"similarity_search_with_relevance_scores failed ({exc}), falling back to regular similarity_search")
                docs = self._store.similarity_search(query, k=search_k)
                raw_results = [(doc, 0.5) for doc in docs]

        all_candidates: list[dict[str, Any]] = []
        for document, score in raw_results:
            metadata = dict(document.metadata)
            if document_id and str(metadata.get("document_id", "")) != document_id:
                continue
            if session_id:
                doc_session = metadata.get("session_id")
                if doc_session and doc_session != session_id:
                    continue

            all_candidates.append(
                {
                    "content": document.page_content,
                    "score": float(score),
                    "metadata": metadata,
                }
            )

        filtered_matches = [item for item in all_candidates if item["score"] >= min_relevance_score]
        
        if len(filtered_matches) >= min(top_k, 3):
            matches = filtered_matches[:top_k]
        elif all_candidates:
            matches = all_candidates[:top_k]
        elif document_id:
            matches = self.get_document_chunks(document_id, limit=top_k, session_id=session_id)
        else:
            matches = []

        if is_broad_query and document_id and len(matches) < top_k:
            overview_chunks = self.get_document_chunks(document_id, limit=top_k - len(matches), session_id=session_id)
            existing_contents = {m["content"] for m in matches}
            for oc in overview_chunks:
                if oc["content"] not in existing_contents:
                    matches.append(oc)

        return matches[:top_k]