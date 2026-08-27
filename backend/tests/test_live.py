import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from services.live_service import (
    LiveServiceError,
    _relay_gemini_output,
    _send_transcription,
    build_live_config,
    describe_live_error,
)
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

    def test_live_turn_limit_defaults_to_two(self) -> None:
        from settings import Settings

        settings = Settings(_env_file=None)
        self.assertEqual(settings.gemini_live_max_turns, 2)

    def test_live_tool_declarations_reuse_langchain_schemas(self) -> None:
        config = build_live_tool_config(build_live_tools())
        profile = next(item for item in config.function_declarations if item.name == "get_profile_section")
        self.assertEqual(
            profile.parameters_json_schema["properties"]["section"]["enum"],
            ["profile", "experience", "education", "skills", "projects"],
        )

    def test_minimal_diagnostic_config_excludes_tools(self) -> None:
        settings = SimpleNamespace(gemini_live_voice="Kore")
        with patch("services.live_service.get_settings", return_value=settings):
            config = build_live_config("en", include_tools=False)
        self.assertIsNone(config.tools)

    def test_provider_internal_error_preserves_safe_diagnostics(self) -> None:
        error = describe_live_error(
            RuntimeError("1011 None. Internal error occurred."),
            "streaming",
        )
        self.assertEqual(error.code, "provider_internal_error")
        self.assertEqual(error.stage, "streaming")
        self.assertTrue(error.retryable)
        self.assertIn("1011", error.detail)

    def test_live_tool_execution_returns_safe_error(self) -> None:
        tool = MagicMock()
        tool.name = "broken_tool"
        tool.invoke.side_effect = RuntimeError("secret provider detail")
        with self.assertLogs("services.live_tools_service", level="ERROR"):
            result = __import__("asyncio").run(execute_live_tool(tool, {}))
        self.assertEqual(result, {"error": "The requested tool could not be completed."})


class LiveTranscriptionTests(unittest.IsolatedAsyncioTestCase):
    async def test_forwards_finished_marker_without_text(self) -> None:
        websocket = SimpleNamespace(send_json=AsyncMock())
        transcription = SimpleNamespace(text=None, finished=True)

        await _send_transcription(websocket, "user", transcription)

        websocket.send_json.assert_awaited_once_with(
            {
                "type": "transcript",
                "role": "user",
                "text": "",
                "finished": True,
            }
        )

    async def test_closes_live_relay_after_two_completed_turns(self) -> None:
        websocket = SimpleNamespace(send_json=AsyncMock(), send_bytes=AsyncMock())

        async def receive():
            for _ in range(2):
                yield SimpleNamespace(
                    data=None,
                    tool_call=None,
                    go_away=None,
                    server_content=SimpleNamespace(
                        interrupted=False,
                        input_transcription=None,
                        output_transcription=None,
                        turn_complete=True,
                    ),
                )

        session = SimpleNamespace(receive=receive)
        await _relay_gemini_output(websocket, session, {}, 2)

        self.assertEqual(
            [call.args[0] for call in websocket.send_json.await_args_list],
            [
                {"type": "turn_complete", "turns_used": 1, "turns_remaining": 1},
                {"type": "turn_complete", "turns_used": 2, "turns_remaining": 0},
                {"type": "limit_reached", "max_turns": 2},
            ],
        )


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

    def test_returns_structured_live_service_error(self) -> None:
        run_session = AsyncMock(
            side_effect=LiveServiceError(
                "Gemini failed.",
                code="provider_internal_error",
                detail="1011 Internal error occurred.",
                retryable=True,
                stage="streaming",
            )
        )
        with patch("routes.live.run_live_session", run_session):
            with self.client.websocket_connect(
                "/live/ws", headers={"origin": "http://localhost:5173"}
            ) as websocket:
                websocket.send_text(json.dumps({"type": "start", "locale": "en"}))
                event = websocket.receive_json()

        self.assertEqual(
            event,
            {
                "type": "error",
                "code": "provider_internal_error",
                "message": "Gemini failed.",
                "detail": "1011 Internal error occurred.",
                "retryable": True,
                "stage": "streaming",
            },
        )


if __name__ == "__main__":
    unittest.main()
