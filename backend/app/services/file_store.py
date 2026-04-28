from __future__ import annotations

import json
from pathlib import Path
from threading import RLock

from app.schemas.document import DocumentRecord


class DocumentRepository:
    def __init__(self, metadata_path: Path) -> None:
        self._metadata_path = metadata_path
        self._lock = RLock()
        self._documents: dict[str, DocumentRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self._metadata_path.exists():
            self._documents = {}
            return

        raw = self._metadata_path.read_text(encoding="utf-8")
        if not raw.strip():
            self._documents = {}
            return

        payload = json.loads(raw)
        self._documents = {
            item["id"]: DocumentRecord.model_validate(item)
            for item in payload
        }

    def _persist(self) -> None:
        self._metadata_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [document.model_dump(mode="json") for document in self._documents.values()]
        self._metadata_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def list(self) -> list[DocumentRecord]:
        with self._lock:
            return sorted(self._documents.values(), key=lambda item: item.created_at, reverse=True)

    def get(self, document_id: str) -> DocumentRecord | None:
        with self._lock:
            return self._documents.get(document_id)

    def upsert(self, record: DocumentRecord) -> DocumentRecord:
        with self._lock:
            self._documents[record.id] = record
            self._persist()
            return record
