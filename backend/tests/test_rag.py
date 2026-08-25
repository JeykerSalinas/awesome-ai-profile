import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from pydantic import ValidationError
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from schemas.chat import ChatStreamRequest
from schemas.documents import DocumentUploadResponse
from services.vector_store_service import EmptyDocumentError, VectorStoreService


class VectorStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.settings = SimpleNamespace(
            google_api_key="test-key",
            vector_store_path=str(Path(self.temporary_directory.name) / "chroma"),
            embedding_model="models/gemini-embedding-001",
            rag_chunk_size=120,
            rag_chunk_overlap=20,
            rag_result_limit=5,
            upload_ttl_minutes=30,
        )
        self.profile_store = MagicMock()
        self.profile_store.get.return_value = {"ids": []}
        self.upload_store = MagicMock()
        self.settings_patch = patch("services.vector_store_service.get_settings", return_value=self.settings)
        self.chroma_patch = patch(
            "services.vector_store_service.Chroma",
            side_effect=[self.profile_store, self.upload_store],
        )
        self.embeddings_patch = patch("services.vector_store_service.GoogleGenerativeAIEmbeddings")
        self.ephemeral_patch = patch("services.vector_store_service.chromadb.EphemeralClient")
        self.settings_patch.start()
        self.chroma_patch.start()
        self.embeddings_patch.start()
        self.ephemeral_patch.start()
        self.addCleanup(self.settings_patch.stop)
        self.addCleanup(self.chroma_patch.stop)
        self.addCleanup(self.embeddings_patch.stop)
        self.addCleanup(self.ephemeral_patch.stop)
        self.addCleanup(self.temporary_directory.cleanup)
        self.service = VectorStoreService()

    def test_indexes_existing_json_and_markdown_knowledge_with_metadata(self) -> None:
        call = self.profile_store.add_documents.call_args
        documents = call.kwargs["documents"]
        sources = {document.metadata["source"] for document in documents}
        self.assertIn("knowledge/profile.json", sources)
        self.assertIn("knowledge/projects/educational-rag-platform.md", sources)
        self.assertTrue(all(document.metadata["scope"] == "profile" for document in documents))

    def test_skips_existing_profile_embeddings(self) -> None:
        known_ids = self.profile_store.add_documents.call_args.kwargs["ids"]
        self.profile_store.reset_mock()
        self.profile_store.get.return_value = {"ids": known_ids}
        self.service._ensure_profile_knowledge()
        self.profile_store.add_documents.assert_not_called()

    def test_ingests_heterogeneous_pdf_with_page_and_document_type(self) -> None:
        pages = [SimpleNamespace(extract_text=lambda: "We need a Vue engineer with RAG experience.")]
        with patch("services.vector_store_service.PdfReader", return_value=SimpleNamespace(pages=pages)):
            result = self.service.ingest_pdf(b"%PDF-1.4", "opening.pdf", "job_offer")

        self.assertEqual(result.document_type, "job_offer")
        self.assertEqual(result.pages, 1)
        documents = self.upload_store.add_documents.call_args.args[0]
        self.assertEqual(documents[0].metadata["page"], 1)
        self.assertEqual(documents[0].metadata["document_type"], "job_offer")
        self.assertEqual(documents[0].metadata["document_id"], result.id)
        self.assertEqual(self.profile_store.add_documents.call_count, 1)
        self.assertIn(result.id, self.service.upload_expirations)

    def test_rejects_scanned_pdfs_without_selectable_text(self) -> None:
        pages = [SimpleNamespace(extract_text=lambda: "")]
        with patch("services.vector_store_service.PdfReader", return_value=SimpleNamespace(pages=pages)):
            with self.assertRaisesRegex(EmptyDocumentError, "require OCR"):
                self.service.ingest_pdf(b"%PDF-1.4", "scan.pdf", "other")

    def test_retrieval_is_limited_to_profile_and_current_chat_documents(self) -> None:
        self.profile_store.similarity_search_with_relevance_scores.return_value = []
        self.upload_store.similarity_search_with_relevance_scores.return_value = []
        self.service.upload_expirations["my-document"] = float("inf")
        self.service.search("Does Jeyker match this role?", ["my-document"])
        query_filter = self.upload_store.similarity_search_with_relevance_scores.call_args.kwargs["filter"]
        self.assertEqual(query_filter, {"document_id": {"$in": ["my-document"]}})
        self.profile_store.similarity_search_with_relevance_scores.assert_called_once()

    def test_retrieval_without_uploads_excludes_all_uploaded_documents(self) -> None:
        self.profile_store.similarity_search_with_relevance_scores.return_value = []
        self.service.search("Vue and TypeScript")
        self.profile_store.similarity_search_with_relevance_scores.assert_called_once()
        self.upload_store.similarity_search_with_relevance_scores.assert_not_called()

    def test_expired_documents_are_deleted_from_memory(self) -> None:
        self.profile_store.similarity_search_with_relevance_scores.return_value = []
        self.service.upload_expirations["expired-document"] = 0
        self.service.search("Compare the old offer", ["expired-document"])
        self.upload_store.delete.assert_called_once_with(where={"document_id": "expired-document"})
        self.upload_store.similarity_search_with_relevance_scores.assert_not_called()
        self.assertNotIn("expired-document", self.service.upload_expirations)

    def test_removing_document_deletes_its_temporary_vectors(self) -> None:
        self.service.upload_expirations["document-to-delete"] = float("inf")
        self.assertTrue(self.service.remove_upload("document-to-delete"))
        self.upload_store.delete.assert_called_once_with(where={"document_id": "document-to-delete"})
        self.assertNotIn("document-to-delete", self.service.upload_expirations)


class DocumentUploadEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        from main import app
        self.client = TestClient(app)

    def test_uploads_a_pdf_and_returns_indexing_metadata(self) -> None:
        indexed = DocumentUploadResponse(
            id="document-123", filename="opening.pdf", document_type="job_offer", pages=2, chunks=4
        )
        service = MagicMock()
        service.ingest_pdf.return_value = indexed
        with patch("routes.documents.get_vector_store_service", return_value=service):
            response = self.client.post(
                "/documents",
                files={"file": ("opening.pdf", b"%PDF-1.4 sample", "application/pdf")},
                data={"document_type": "job_offer"},
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["chunks"], 4)

    def test_rejects_non_pdf_uploads(self) -> None:
        response = self.client.post(
            "/documents", files={"file": ("notes.txt", b"hello", "text/plain")}
        )
        self.assertEqual(response.status_code, 415)

    def test_rejects_scanned_pdfs_with_clear_error(self) -> None:
        service = MagicMock()
        service.ingest_pdf.side_effect = EmptyDocumentError("Scanned PDFs require OCR.")
        with patch("routes.documents.get_vector_store_service", return_value=service):
            response = self.client.post(
                "/documents", files={"file": ("scan.pdf", b"%PDF-1.4", "application/pdf")}
            )
        self.assertEqual(response.status_code, 422)
        self.assertIn("OCR", response.json()["detail"])

    def test_deletes_temporary_document_when_removed_from_chat(self) -> None:
        service = MagicMock()
        service.remove_upload.return_value = True
        with patch("routes.documents.get_vector_store_service", return_value=service):
            response = self.client.delete("/documents/document-123")
        self.assertEqual(response.status_code, 204)
        service.remove_upload.assert_called_once_with("document-123")

    def test_reports_already_expired_document(self) -> None:
        service = MagicMock()
        service.remove_upload.return_value = False
        with patch("routes.documents.get_vector_store_service", return_value=service):
            response = self.client.delete("/documents/missing")
        self.assertEqual(response.status_code, 404)


class DocumentScopedChatTests(unittest.TestCase):
    def test_preserves_document_ids_for_retrieval(self) -> None:
        request = ChatStreamRequest.model_validate({"message": "Compare my offer", "documents": ["abc"]})
        self.assertEqual(request.documents, ["abc"])

    def test_limits_active_documents_per_request(self) -> None:
        with self.assertRaises(ValidationError):
            ChatStreamRequest.model_validate({"message": "Compare", "documents": [str(i) for i in range(11)]})


class RealChromaIntegrationTests(unittest.TestCase):
    def test_indexes_real_pdf_only_in_memory_while_profile_persists(self) -> None:
        class LocalEmbeddings:
            def embed_documents(self, documents):
                return [self.embed_query(document) for document in documents]

            def embed_query(self, document):
                normalized = document.lower()
                return [float(normalized.count(term)) for term in ("vue", "python", "rag", "engineer")] or [0.0] * 4

        writer = PdfWriter()
        page = writer.add_blank_page(width=300, height=300)
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})
        })
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 20 250 Td (Hiring a Vue engineer with Python and RAG experience.) Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
        buffer = BytesIO()
        writer.write(buffer)

        with tempfile.TemporaryDirectory() as directory:
            settings = SimpleNamespace(
                google_api_key="test-key",
                vector_store_path=str(Path(directory) / "chroma"),
                embedding_model="test-embedding",
                rag_chunk_size=900,
                rag_chunk_overlap=150,
                rag_result_limit=25,
                upload_ttl_minutes=30,
            )
            with patch("services.vector_store_service.get_settings", return_value=settings):
                with patch("services.vector_store_service.GoogleGenerativeAIEmbeddings", return_value=LocalEmbeddings()):
                    service = VectorStoreService()
                    uploaded = service.ingest_pdf(buffer.getvalue(), "real-job-offer.pdf", "job_offer")
                    results = service.search("Vue engineer Python RAG", [uploaded.id])
                    persistent_uploads = service.profile_store.get(
                        where={"scope": {"$eq": "upload"}},
                        include=[],
                    )

            matching = [item for item in results["results"] if item["filename"] == "real-job-offer.pdf"]
            self.assertEqual(len(matching), 1)
            self.assertEqual(matching[0]["page"], 1)
            self.assertIn("Vue engineer", matching[0]["content"])
            self.assertEqual(persistent_uploads["ids"], [])
            self.assertTrue((Path(directory) / "chroma" / "chroma.sqlite3").is_file())


if __name__ == "__main__":
    unittest.main()
