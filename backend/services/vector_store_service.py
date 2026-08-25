from __future__ import annotations

import hashlib
import io
import json
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from schemas.documents import DocumentType, DocumentUploadResponse
from settings import get_settings


KNOWLEDGE_ROOT = Path(__file__).resolve().parent.parent / "knowledge"
COLLECTION_NAME = "professional_documents"
PROFILE_SCOPE = "profile"
UPLOAD_SCOPE = "upload"


class EmptyDocumentError(ValueError):
    pass


class VectorStoreService:
    """Ingest heterogeneous documents and retrieve semantically related chunks."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY is not configured.")

        persist_directory = Path(settings.vector_store_path)
        persist_directory.mkdir(parents=True, exist_ok=True)
        embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.embedding_model,
            google_api_key=settings.google_api_key,
        )
        self.store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=str(persist_directory),
            collection_metadata={"hnsw:space": "cosine"},
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        self.result_limit = settings.rag_result_limit
        self._ensure_profile_knowledge()

    def _ensure_profile_knowledge(self) -> None:
        documents: list[Document] = []
        ids: list[str] = []

        for path in sorted(KNOWLEDGE_ROOT.rglob("*")):
            if path.suffix not in {".json", ".md"} or path.name == "README.md":
                continue

            raw_text = path.read_text(encoding="utf-8")
            if path.suffix == ".json":
                raw_text = json.dumps(json.loads(raw_text), ensure_ascii=False, indent=2)

            relative_source = f"knowledge/{path.relative_to(KNOWLEDGE_ROOT).as_posix()}"
            content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:16]
            chunks = self.splitter.split_text(raw_text)
            for index, chunk in enumerate(chunks):
                ids.append(f"profile:{relative_source}:{content_hash}:{index}")
                documents.append(Document(page_content=chunk, metadata={
                    "document_id": relative_source,
                    "document_type": "profile",
                    "filename": path.name,
                    "source": relative_source,
                    "scope": PROFILE_SCOPE,
                    "page": 0,
                    "chunk_index": index,
                }))

        existing_ids = set(self.store.get(ids=ids, include=[])["ids"]) if ids else set()
        pending = [(identifier, document) for identifier, document in zip(ids, documents) if identifier not in existing_ids]
        if pending:
            self.store.add_documents(
                documents=[document for _, document in pending],
                ids=[identifier for identifier, _ in pending],
            )

    def ingest_pdf(self, content: bytes, filename: str, document_type: DocumentType) -> DocumentUploadResponse:
        try:
            reader = PdfReader(io.BytesIO(content))
        except Exception as exc:
            raise ValueError("The uploaded file is not a readable PDF.") from exc

        document_id = uuid4().hex
        page_documents: list[Document] = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            page_documents.append(Document(page_content=text, metadata={
                "document_id": document_id,
                "document_type": document_type,
                "filename": filename,
                "source": filename,
                "scope": UPLOAD_SCOPE,
                "page": page_number,
            }))

        if not page_documents:
            raise EmptyDocumentError("No selectable text was found. Scanned PDFs require OCR before indexing.")

        chunks = self.splitter.split_documents(page_documents)
        for index, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = index
        self.store.add_documents(chunks, ids=[f"upload:{document_id}:{index}" for index in range(len(chunks))])
        return DocumentUploadResponse(
            id=document_id,
            filename=filename,
            document_type=document_type,
            pages=len(reader.pages),
            chunks=len(chunks),
        )

    def search(self, query: str, document_ids: list[str] | None = None) -> dict[str, object]:
        allowed_ids = list(dict.fromkeys(document_ids or []))
        filters: list[dict[str, object]] = [{"scope": {"$eq": PROFILE_SCOPE}}]
        filters.extend({"document_id": {"$eq": document_id}} for document_id in allowed_ids)
        metadata_filter: dict[str, object] = filters[0] if len(filters) == 1 else {"$or": filters}
        matches = self.store.similarity_search_with_relevance_scores(
            query, k=self.result_limit, filter=metadata_filter
        )
        results = [{
            "content": document.page_content,
            "source": document.metadata["source"],
            "filename": document.metadata["filename"],
            "document_type": document.metadata["document_type"],
            "page": document.metadata.get("page") or None,
            "score": round(float(score), 4),
        } for document, score in matches]
        return {"query": query, "count": len(results), "results": results}


@lru_cache(maxsize=1)
def get_vector_store_service() -> VectorStoreService:
    return VectorStoreService()
