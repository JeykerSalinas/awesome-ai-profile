from typing import Literal

from pydantic import BaseModel


DocumentType = Literal["cv", "job_offer", "letter", "other"]


class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    document_type: DocumentType
    pages: int
    chunks: int

