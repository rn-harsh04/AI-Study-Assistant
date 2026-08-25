from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
import shutil
from uuid import uuid4

from fastapi import UploadFile

from app.schemas.document import DocumentRecord
from app.services.chunking_service import ChunkingService
from app.services.file_store import DocumentRepository
from app.services.parser_service import DocumentParser
from app.services.vector_store import VectorStoreService

logger = logging.getLogger("studyassistant.document_service")


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
        record = await self.save_upload_file(upload_file)
        try:
            self.finalize_processing(record.id)
            updated = self._repository.get(record.id)
            return updated if updated is not None else record
        except Exception:
            raise

    async def save_upload_file(self, upload_file: UploadFile) -> DocumentRecord:
        """Save upload to disk and create a processing record. Does NOT block for indexing."""
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
        """Process a previously saved upload: parse, chunk and index."""
        record = self._repository.get(document_id)
        if record is None:
            return

        try:
            logger.info(f"Starting processing for document {record.filename} ({document_id})")
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
            logger.info(f"Document {record.filename} successfully indexed with {len(chunks)} chunks.")
        except Exception as exc:
            logger.error(f"Error processing document {document_id}: {exc}", exc_info=True)
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

    def get_document(self, document_id: str) -> DocumentRecord | None:
        return self._repository.get(document_id)

    def delete_document(self, document_id: str) -> bool:
        record = self._repository.get(document_id)
        if record is None:
            return False

        # 1. Delete vectors from FAISS
        try:
            self._vector_store.delete_document(document_id)
        except Exception as exc:
            logger.error(f"Error deleting vectors for {document_id}: {exc}")

        # 2. Delete file storage
        try:
            doc_dir = self._uploads_dir / document_id
            if doc_dir.exists() and doc_dir.is_dir():
                shutil.rmtree(doc_dir, ignore_errors=True)
            elif record.stored_path and Path(record.stored_path).exists():
                Path(record.stored_path).unlink(missing_ok=True)
        except Exception as exc:
            logger.error(f"Error deleting files for {document_id}: {exc}")

        # 3. Delete metadata record
        return self._repository.delete(document_id)