from __future__ import annotations
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, BackgroundTasks

from app.core.deps import get_document_service
from app.schemas.document import DocumentListResponse, DocumentRecord, DocumentUploadResponse
from app.services.document_service import DocumentService


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    try:
        document = await document_service.save_upload_file(file)
        background_tasks.add_task(document_service.finalize_processing, document.id)
        return DocumentUploadResponse(
            message="Upload received and indexing started in background.",
            document=document,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=DocumentListResponse)
def list_documents(document_service: DocumentService = Depends(get_document_service)) -> DocumentListResponse:
    return DocumentListResponse(documents=document_service.list_documents())


@router.get("/{document_id}", response_model=DocumentRecord)
def get_document(
    document_id: str,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentRecord:
    doc = document_service.get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(
    document_id: str,
    document_service: DocumentService = Depends(get_document_service),
) -> dict[str, Any]:
    success = document_service.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found or already deleted")
    return {"message": "Document and all associated vector embeddings deleted successfully", "document_id": document_id}