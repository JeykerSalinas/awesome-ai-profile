from __future__ import annotations

import hashlib
import io
import json
from functools import lru_cache
from pathlib import Path
from threading import RLock
from time import monotonic
from uuid import uuid4

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from schemas.documents import DocumentType, DocumentUploadResponse
from settings import get_settings


KNOWLEDGE_ROOT = Path(__file__).resolve().parent.parent / "knowledge"
PROFILE_COLLECTION_NAME = "professional_documents"
UPLOAD_COLLECTION_NAME = "temporary_visitor_documents"
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
        self.profile_store = Chroma(
            collection_name=PROFILE_COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=str(persist_directory),
            collection_metadata={"hnsw:space": "cosine"},
        )
        self.upload_store = Chroma(
            collection_name=UPLOAD_COLLECTION_NAME,
            embedding_function=embeddings,
            client=chromadb.EphemeralClient(),
            collection_metadata={"hnsw:space": "cosine"},
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        self.result_limit = settings.rag_result_limit
        self.upload_ttl_seconds = settings.upload_ttl_minutes * 60
        self.upload_expirations: dict[str, float] = {}
        self.upload_lock = RLock()
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

        existing_ids = set(self.profile_store.get(ids=ids, include=[])["ids"]) if ids else set()
        pending = [(identifier, document) for identifier, document in zip(ids, documents) if identifier not in existing_ids]
        if pending:
            self.profile_store.add_documents(
                documents=[document for _, document in pending],
                ids=[identifier for identifier, _ in pending],
            )

    def ingest_pdf(self, content: bytes, filename: str, document_type: DocumentType) -> DocumentUploadResponse:
        self._remove_expired_uploads()
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
        with self.upload_lock:
            self.upload_store.add_documents(
                chunks,
                ids=[f"upload:{document_id}:{index}" for index in range(len(chunks))],
            )
            self.upload_expirations[document_id] = monotonic() + self.upload_ttl_seconds
        return DocumentUploadResponse(
            id=document_id,
            filename=filename,
            document_type=document_type,
            pages=len(reader.pages),
            chunks=len(chunks),
        )

    def search(self, query: str, document_ids: list[str] | None = None) -> dict[str, object]:
        self._remove_expired_uploads()
        matches = self.profile_store.similarity_search_with_relevance_scores(
            query, k=self.result_limit
        )
        with self.upload_lock:
            allowed_ids = [
                identifier
                for identifier in dict.fromkeys(document_ids or [])
                if identifier in self.upload_expirations
            ]
            if allowed_ids:
                matches.extend(self.upload_store.similarity_search_with_relevance_scores(
                    query,
                    k=self.result_limit,
                    filter={"document_id": {"$in": allowed_ids}},
                ))
                for identifier in allowed_ids:
                    self.upload_expirations[identifier] = monotonic() + self.upload_ttl_seconds

        matches.sort(key=lambda match: match[1], reverse=True)
        matches = matches[:self.result_limit]
        results = [{
            "content": document.page_content,
            "source": document.metadata["source"],
            "filename": document.metadata["filename"],
            "document_type": document.metadata["document_type"],
            "page": document.metadata.get("page") or None,
            "score": round(float(score), 4),
        } for document, score in matches]
        return {"query": query, "count": len(results), "results": results}

    def remove_upload(self, document_id: str) -> bool:
        with self.upload_lock:
            if document_id not in self.upload_expirations:
                return False
            self.upload_store.delete(where={"document_id": document_id})
            del self.upload_expirations[document_id]
            return True

    def _remove_expired_uploads(self) -> None:
        now = monotonic()
        with self.upload_lock:
            expired = [
                document_id
                for document_id, expires_at in self.upload_expirations.items()
                if expires_at <= now
            ]
            for document_id in expired:
                self.upload_store.delete(where={"document_id": document_id})
                del self.upload_expirations[document_id]


@lru_cache(maxsize=1)
def get_vector_store_service() -> VectorStoreService:
    return VectorStoreService()
