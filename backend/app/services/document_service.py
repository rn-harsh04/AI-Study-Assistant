from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.schemas.document import DocumentRecord
from app.services.chunking_service import ChunkingService
from app.services.file_store import DocumentRepository
from app.services.parser_service import DocumentParser
from app.services.vector_store import VectorStoreService


class DocumentTextExtractionError(ValueError):
    pass


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        parser: DocumentParser,
        chunker: ChunkingService,
        vector_store: VectorStoreService,
        uploads_dir: Path,
    ) -> None:
        self._repository = repository
        self._parser = parser
        self._chunker = chunker
        self._vector_store = vector_store
        self._uploads_dir = uploads_dir

    async def ingest_upload(self, upload_file: UploadFile) -> DocumentRecord:
        # Backwards-compatible single-call ingestion (kept for compatibility).
        # This method now delegates to the save + synchronous processing functions.
        record = await self.save_upload_file(upload_file)
        # perform processing synchronously (blocking) - kept for callers that expect ingestion to finish
        try:
            self.finalize_processing(record.id)
            return self._repository.get(record.id)
        except Exception:
            # re-raise to preserve previous behaviour
            raise

    async def save_upload_file(self, upload_file: UploadFile) -> DocumentRecord:
        """Save upload to disk and create a processing record. Does NOT run indexing.

        Call `finalize_processing(document_id)` later (e.g., via BackgroundTasks) to complete indexing.
        """
        document_id = uuid4().hex
        safe_name = Path(upload_file.filename or "document").name
        destination_dir = self._uploads_dir / document_id
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination_path = destination_dir / safe_name

        content = await upload_file.read()
        destination_path.write_bytes(content)

        now = datetime.now(timezone.utc)
        record = DocumentRecord(
            id=document_id,
            filename=safe_name,
            stored_path=str(destination_path),
            mime_type=upload_file.content_type,
            status="processing",
            chunk_count=0,
            created_at=now,
            updated_at=now,
        )
        self._repository.upsert(record)
        return record

    def finalize_processing(self, document_id: str) -> None:
        """Process a previously saved upload: parse, chunk and index. Synchronous/blocking."""
        record = self._repository.get(document_id)
        if record is None:
            return

        try:
            pages = self._parser.parse(Path(record.stored_path))
            chunks = self._chunker.build_chunks(record, pages)
            if not chunks:
                failed_record = record.model_copy(
                    update={
                        "status": "failed",
                        "error_message": "No extractable text was found in the uploaded file.",
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
                self._repository.upsert(failed_record)
                return

            self._vector_store.add_chunks(chunks)

            final_record = record.model_copy(
                update={
                    "status": "ready",
                    "chunk_count": len(chunks),
                    "error_message": None,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            self._repository.upsert(final_record)
        except Exception as exc:
            failed_record = record.model_copy(
                update={
                    "status": "failed",
                    "error_message": str(exc),
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            self._repository.upsert(failed_record)

    def list_documents(self) -> list[DocumentRecord]:
        return self._repository.list()
