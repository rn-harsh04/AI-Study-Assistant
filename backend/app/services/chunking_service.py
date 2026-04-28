from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.schemas.document import DocumentRecord
from app.services.parser_service import ParsedPage


@dataclass(slots=True)
class IndexedChunk:
    text: str
    metadata: dict[str, Any]


class ChunkingService:
    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

    def build_chunks(self, document: DocumentRecord, pages: list[ParsedPage]) -> list[IndexedChunk]:
        chunks: list[IndexedChunk] = []
        chunk_index = 0
        for page in pages:
            split_texts = self._splitter.split_text(page.text)
            for split_text in split_texts:
                chunk_index += 1
                chunks.append(
                    IndexedChunk(
                        text=split_text,
                        metadata={
                            "document_id": document.id,
                            "filename": document.filename,
                            "stored_path": document.stored_path,
                            "chunk_id": chunk_index,
                            "page_number": page.page_number,
                        },
                    )
                )
        return chunks
