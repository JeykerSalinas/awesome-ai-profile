import asyncio
import json
import unittest
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from services.profile_service import get_profile, initial_greeting
from services.prompt_service import build_professional_system_prompt
from services.knowledge_service import get_profile_section_data, search_professional_experience
from services.public_contact import public_contact_details
from schemas.chat import ChatRequest, ChatStreamRequest
from schemas.live import LiveSessionStart

class ProfileTests(unittest.TestCase):
    def test_default_profile_is_backwards_compatible(self):
        self.assertEqual(ChatRequest(message="Hi").profile_id, "jeyker")
        self.assertIn("Django", build_professional_system_prompt())
        self.assertTrue(public_contact_details()["email"])

    def test_rejects_unknown_profiles_in_all_transports(self):
        for schema, payload in [
            (ChatRequest, {"message": "Hi"}),
            (ChatStreamRequest, {"message": "Hi"}),
            (LiveSessionStart, {"type": "start"}),
        ]:
            with self.subTest(schema=schema):
                with self.assertRaises(ValidationError):
                    schema.model_validate({**payload, "profile_id": "../knowledge"})
        with self.assertRaises(ValueError):
            get_profile("../knowledge")

    def test_sara_has_no_jeyker_facts_contact_or_photo(self):
        self.assertEqual(get_profile("sara").photo, None)
        self.assertEqual(public_contact_details("sara"), {})
        self.assertNotIn("Jeyker", json.dumps(get_profile_section_data("profile", "sara")))
        self.assertEqual(search_professional_experience("Vue Python", profile_id="sara")["count"], 0)
        self.assertIn("Sara", build_professional_system_prompt("es", "sara"))
        self.assertNotIn("Jeyker", build_professional_system_prompt("es", "sara"))
        self.assertNotIn("Django", initial_greeting("es", "sara"))

    def test_concurrent_profile_tools_are_bound_independently(self):
        from agents.tools import build_profile_tools
        async def query(profile_id):
            tools = {tool.name: tool for tool in build_profile_tools(profile_id)}
            self.assertEqual("get_candidate_photo" in tools, profile_id == "jeyker")
            result = await tools["get_profile_section"].ainvoke({"section": "profile"})
            return json.loads(result)["data"]
        async def run():
            return await asyncio.gather(query("jeyker"), query("sara"))
        jeyker, sara = asyncio.run(run())
        self.assertIn("Jeyker", json.dumps(jeyker))
        self.assertNotIn("Jeyker", json.dumps(sara))

    def test_voice_prompt_and_tools_use_selected_profile(self):
        from services.live_service import build_live_config
        from services.live_tools_service import build_live_tools
        config = build_live_config("en", profile_id="sara")
        self.assertIn("Sara", config.system_instruction)
        self.assertNotIn("get_candidate_photo", build_live_tools(profile_id="sara"))

    def test_vector_collections_and_upload_capabilities_are_separate(self):
        from services.vector_store_service import VectorStoreService
        with patch("services.vector_store_service.GoogleGenerativeAIEmbeddings"), patch("services.vector_store_service.Chroma") as chroma:
            chroma.return_value.get.return_value = {"ids": []}
            with patch("services.vector_store_service.get_settings") as settings:
                settings.return_value = MagicMock(
                    google_api_key="test", vector_store_path="/tmp/profile-tests",
                    rag_chunk_size=900, rag_chunk_overlap=150, rag_result_limit=5, upload_ttl_minutes=30,
                )
                jeyker = VectorStoreService("jeyker")
                sara = VectorStoreService("sara")
            names = [call.kwargs["collection_name"] for call in chroma.call_args_list]
            self.assertEqual(len(set(names)), 4)
            jeyker.upload_expirations["jeyker-document"] = float("inf")
            self.assertFalse(sara.remove_upload("jeyker-document"))

if __name__ == "__main__":
    unittest.main()
