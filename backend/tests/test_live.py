import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from services.live_service import build_live_config
from services.live_tools_service import build_live_tool_config, build_live_tools, execute_live_tool


class LiveConfigurationTests(unittest.TestCase):
    def test_live_session_uses_native_audio_transcription_prompt_and_all_tools(self) -> None:
        settings = SimpleNamespace(gemini_live_voice="Kore")
        with patch("services.live_service.get_settings", return_value=settings):
            config = build_live_config("es", ["document-123"])

        self.assertEqual(config.response_modalities, ["AUDIO"])
        self.assertIn("Respond entirely in Spanish", str(config.system_instruction))
        declarations = config.tools[0].function_declarations
        self.assertEqual(
            {declaration.name for declaration in declarations},
            {"get_candidate_photo", "get_profile_section", "search_experience", "search_documents"},
        )
        search_schema = next(item for item in declarations if item.name == "search_documents")
        self.assertIn("query", search_schema.parameters_json_schema["required"])

    def test_live_tool_declarations_reuse_langchain_schemas(self) -> None:
        config = build_live_tool_config(build_live_tools())
        profile = next(item for item in config.function_declarations if item.name == "get_profile_section")
        self.assertEqual(
            profile.parameters_json_schema["properties"]["section"]["enum"],
            ["profile", "experience", "education", "skills", "projects"],
        )

    def test_live_tool_execution_returns_safe_error(self) -> None:
        tool = MagicMock()
        tool.name = "broken_tool"
        tool.invoke.side_effect = RuntimeError("secret provider detail")
        with self.assertLogs("services.live_tools_service", level="ERROR"):
            result = __import__("asyncio").run(execute_live_tool(tool, {}))
        self.assertEqual(result, {"error": "The requested tool could not be completed."})


class LiveWebSocketEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        from main import app

        self.client = TestClient(app)

    def test_rejects_untrusted_websocket_origin(self) -> None:
        with self.assertRaises(Exception):
            with self.client.websocket_connect(
                "/live/ws", headers={"origin": "https://untrusted.example"}
            ):
                pass

    def test_accepts_start_message_and_passes_locale_and_documents(self) -> None:
        run_session = AsyncMock()
        with patch("routes.live.run_live_session", run_session):
            with self.client.websocket_connect(
                "/live/ws", headers={"origin": "http://localhost:5173"}
            ) as websocket:
                websocket.send_text(
                    json.dumps(
                        {
                            "type": "start",
                            "locale": "es",
                            "documents": ["document-123"],
                            "history": [{"role": "user", "content": "Tell me about RAG"}],
                        }
                    )
                )

        args = run_session.await_args.args
        self.assertEqual(
            args[1:],
            (
                "es",
                ["document-123"],
                [{"role": "user", "content": "Tell me about RAG"}],
            ),
        )


if __name__ == "__main__":
    unittest.main()
