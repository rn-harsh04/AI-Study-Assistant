from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, BackgroundTasks

from app.core.deps import get_document_service
from app.schemas.document import DocumentListResponse, DocumentUploadResponse
from app.services.document_service import DocumentService


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = Depends(),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    try:
        # Save file synchronously and schedule background indexing to speed up response.
        document = await document_service.save_upload_file(file)
        # schedule background processing (non-blocking)
        background_tasks.add_task(document_service.finalize_processing, document.id)
        # return early while indexing continues
        return DocumentUploadResponse(document=document)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=DocumentListResponse)
def list_documents(document_service: DocumentService = Depends(get_document_service)) -> DocumentListResponse:
    return DocumentListResponse(documents=document_service.list_documents())
