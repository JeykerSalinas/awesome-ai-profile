import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from pydantic import ValidationError
from main import app
from settings import Settings
from services.profile_service import get_profile, merge_config, profile_settings, PublicProfile, AgentProfile


def modified_profile(**features):
    profile = get_profile("sara")
    public = profile.public.model_copy(update={"features": profile.public.features.model_copy(update=features)})
    return profile.model_copy(update={"public": public})

class ProfileConfigurationTests(unittest.TestCase):
    def test_defaults_merge_without_inheriting_personal_context(self):
        self.assertEqual(merge_config({"features": {"voice": True, "tour": True}, "tools": ["a"]},
            {"features": {"voice": False}, "tools": []}),
            {"features": {"voice": False, "tour": True}, "tools": []})
        self.assertEqual(get_profile("sara").agent.contact, {})
        self.assertNotEqual(get_profile("sara").knowledge_root, get_profile().knowledge_root)

    def test_schema_rejects_unknown_fields_flags_and_tools(self):
        public = get_profile().public.model_dump()
        for extra in [{"secret": "not-public"}, {"features": {"voice": "false"}}]:
            with self.assertRaises(ValidationError):
                PublicProfile.model_validate({**public, **extra})
        with self.assertRaises(ValidationError):
            AgentProfile.model_validate({**get_profile().agent.model_dump(), "allowed_tools": ["shell"]})

    def test_profile_services_select_key_storage_model_and_voice(self):
        profile = get_profile("sara")
        services = profile.agent.services.model_copy(update={"google_api_key_env": "SARA_TEST_KEY", "vector_store_path": "/tmp/sara", "live_model": "voice-model", "live_voice": "Aoede", "embedding_model": "embedding-model"})
        profile = profile.model_copy(update={"agent": profile.agent.model_copy(update={"services": services})})
        base = Settings(google_api_key="shared")
        with patch("services.profile_service.get_profile", return_value=profile):
            with patch.dict(os.environ, {"SARA_TEST_KEY": "sara-only"}):
                resolved = profile_settings("sara", base)
                self.assertEqual(resolved.google_api_key, "sara-only")
                self.assertEqual(resolved.vector_store_path, "/tmp/sara")
                self.assertEqual(resolved.gemini_live_model, "voice-model")
                self.assertEqual(resolved.gemini_live_voice, "Aoede")
                self.assertEqual(resolved.embedding_model, "embedding-model")
                self.assertEqual(base.google_api_key, "shared")
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(ValueError):
                    profile_settings("sara", base)

    def test_disabled_tools_apply_to_both_text_and_voice(self):
        from agents.tools import build_agent_tools
        from services.live_tools_service import build_live_tools
        with patch("agents.tools.get_profile", return_value=modified_profile(tools=False)):
            self.assertEqual(build_agent_tools(profile_id="sara"), [])
            self.assertEqual(build_live_tools(profile_id="sara"), {})
        profile = get_profile("sara")
        profile = profile.model_copy(update={"agent": profile.agent.model_copy(update={"allowed_tools": ["get_profile_section"]})})
        with patch("agents.tools.get_profile", return_value=profile):
            self.assertEqual([tool.name for tool in build_agent_tools(profile_id="sara")], ["get_profile_section"])
            self.assertEqual(list(build_live_tools(profile_id="sara")), ["get_profile_section"])

    def test_documents_disabled_reject_upload_delete_and_chat_attachment(self):
        with patch("services.profile_service.get_profile", return_value=modified_profile(documents=False)):
            with TestClient(app) as client:
                self.assertEqual(client.post("/documents?profile_id=sara", files={"file": ("x.pdf", b"%PDF-fake", "application/pdf")}).status_code, 403)
                self.assertEqual(client.delete("/documents/anything?profile_id=sara").status_code, 403)
                self.assertEqual(client.post("/chat/stream", json={"message": "hi", "profile_id": "sara", "documents": ["id"]}).status_code, 403)

    def test_voice_disabled_or_disabled_attachments_reject_before_provider(self):
        for features, documents in [({"voice": False}, []), ({"documents": False}, ["id"])]:
            with self.subTest(features=features):
                with patch("routes.live.get_profile", return_value=modified_profile(**features)), patch("routes.live.run_live_session") as run:
                    with TestClient(app) as client:
                        with client.websocket_connect("/live/ws") as ws:
                            ws.send_json({"type": "start", "profile_id": "sara", "documents": documents})
                            with self.assertRaises(WebSocketDisconnect) as error:
                                ws.receive_json()
                            self.assertEqual(error.exception.code, 1008)
                    run.assert_not_called()
