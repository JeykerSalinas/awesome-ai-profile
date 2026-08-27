import json
import re
import unittest

from pydantic import ValidationError

from schemas.chat import ChatRequest, ChatStreamRequest
from services.knowledge_service import (
    KNOWLEDGE_ROOT,
    get_profile_section_data,
    search_professional_experience,
)
from services.prompt_service import build_professional_system_prompt
from services.public_contact import public_contact_details


class KnowledgeSectionTests(unittest.TestCase):
    def test_loads_all_supported_sections(self) -> None:
        for section in ("profile", "experience", "education", "skills", "projects"):
            with self.subTest(section=section):
                result = get_profile_section_data(section)
                self.assertEqual(result["section"], section)
                self.assertTrue(str(result["source"]).startswith("knowledge/"))
                self.assertIsInstance(result["data"], dict)

    def test_rejects_unknown_sections_and_path_traversal(self) -> None:
        for section in ("contact", "../settings", "../../.env"):
            with self.subTest(section=section), self.assertRaises(ValueError):
                get_profile_section_data(section)

    def test_arttac_employment_has_verified_end_date(self) -> None:
        data = get_profile_section_data("experience")["data"]
        position = next(item for item in data["positions"] if item["id"] == "arttac-solutions")
        self.assertEqual(position["start_date"], "2025-04")
        self.assertEqual(position["end_date"], "2026-05")

    def test_knowledge_excludes_private_contact_details(self) -> None:
        documents = list(KNOWLEDGE_ROOT.rglob("*.json")) + list(KNOWLEDGE_ROOT.rglob("*.md"))
        combined = "\n".join(path.read_text(encoding="utf-8") for path in documents)

        self.assertIsNone(re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", combined))
        self.assertIsNone(re.search(r"(?:\+\d{1,3}[\s-]?)?\d(?:[\s-]?\d){8,}", combined))

        forbidden_keys = {"email", "phone", "telephone", "street_address", "home_address"}
        for path in KNOWLEDGE_ROOT.rglob("*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(forbidden_keys.isdisjoint(payload))

    def test_project_metadata_points_to_existing_documents(self) -> None:
        data = get_profile_section_data("projects")["data"]

        for project in data["projects"]:
            with self.subTest(project=project["id"]):
                self.assertTrue((KNOWLEDGE_ROOT / project["document"]).is_file())


class KnowledgeSearchTests(unittest.TestCase):
    def test_finds_rag_project_from_english_query(self) -> None:
        result = search_professional_experience("educational RAG information retrieval")
        ids = {item["id"] for item in result["results"]}
        self.assertIn("educational-rag-platform", ids)

    def test_finds_rag_project_from_spanish_query(self) -> None:
        result = search_professional_experience("plataforma educativa recuperación aumentada")
        ids = {item["id"] for item in result["results"]}
        self.assertIn("educational-rag-platform", ids)

    def test_finds_monitoring_experience_from_spanish_query(self) -> None:
        result = search_professional_experience("visualización de datos y monitoreo")
        ids = {item["id"] for item in result["results"]}
        self.assertIn("realtime-monitoring-platform", ids)

    def test_returns_source_paths_without_full_document_content(self) -> None:
        result = search_professional_experience("Vue TypeScript conversational AI")
        self.assertGreater(result["count"], 0)

        for item in result["results"]:
            self.assertTrue(item["source"].startswith("knowledge/"))
            self.assertNotIn("content", item)

    def test_returns_no_results_for_unknown_technology(self) -> None:
        result = search_professional_experience("cobol mainframe")
        self.assertEqual(result["results"], [])
        self.assertEqual(result["count"], 0)

    def test_limits_search_results(self) -> None:
        result = search_professional_experience("Vue", limit=2)
        self.assertLessEqual(len(result["results"]), 2)

    def test_search_results_are_json_serializable(self) -> None:
        result = search_professional_experience("FastAPI LangChain")
        self.assertIsInstance(json.dumps(result, ensure_ascii=False), str)


class LocaleAndPromptTests(unittest.TestCase):
    def test_chat_requests_default_to_english(self) -> None:
        self.assertEqual(ChatRequest(message="Hello").locale, "en")
        self.assertEqual(ChatStreamRequest(message="Hello").locale, "en")

    def test_chat_requests_accept_spanish(self) -> None:
        self.assertEqual(ChatRequest(message="Hola", locale="es").locale, "es")
        self.assertEqual(ChatStreamRequest(message="Hola", locale="es").locale, "es")

    def test_chat_requests_reject_unsupported_locales(self) -> None:
        with self.assertRaises(ValidationError):
            ChatStreamRequest(message="Bonjour", locale="fr")

    def test_english_prompt_requires_verified_knowledge(self) -> None:
        prompt = build_professional_system_prompt("en")
        self.assertIn("Respond entirely in English", prompt)
        self.assertIn("get_profile_section", prompt)
        self.assertIn("Never invent", prompt)

    def test_contact_prompt_is_interest_based_and_read_only(self) -> None:
        prompt = build_professional_system_prompt("en")
        self.assertIn("interest in hiring", prompt)
        self.assertIn("do not repeat an offer", prompt)
        self.assertIn("call get_contact_details", prompt)
        self.assertIn("no external messaging flow", prompt)

    def test_public_contact_details_are_complete_and_authorized(self) -> None:
        self.assertEqual(
            public_contact_details(),
            {
                "phone": "+34 624 179 342",
                "email": "jeyker.salinas13@gmail.com",
                "github": "https://github.com/JeykerSalinas",
                "linkedin": "https://www.linkedin.com/in/jeyker-salinas-608486158/",
            },
        )

    def test_spanish_prompt_translates_english_knowledge(self) -> None:
        prompt = build_professional_system_prompt("es")
        self.assertIn("Respond entirely in Spanish", prompt)
        self.assertIn("source documents are written in English", prompt)
        self.assertIn("private email addresses", prompt)


if __name__ == "__main__":
    unittest.main()
