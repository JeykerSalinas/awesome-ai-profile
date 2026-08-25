from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from schemas.documents import DocumentType, DocumentUploadResponse
from services.vector_store_service import EmptyDocumentError, get_vector_store_service
from settings import get_settings


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: Annotated[UploadFile, File(description="A text-based PDF")],
    document_type: Annotated[DocumentType, Form()] = "other",
) -> DocumentUploadResponse:
    settings = get_settings()
    max_bytes = settings.max_pdf_size_mb * 1024 * 1024
    content = file.file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"PDF files are limited to {settings.max_pdf_size_mb} MB.")
    if file.content_type != "application/pdf" or not content.startswith(b"%PDF"):
        raise HTTPException(status_code=415, detail="Only PDF files are supported.")

    safe_filename = Path(file.filename or "document.pdf").name
    try:
        return get_vector_store_service().ingest_pdf(content, safe_filename, document_type)
    except EmptyDocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
