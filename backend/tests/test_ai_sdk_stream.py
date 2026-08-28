import asyncio
import json
import unittest

from pydantic import ValidationError

from schemas.chat import ChatStreamRequest
from services.ai_sdk_stream import stream_ui_messages
from services.chat_error_service import ERROR_PREFIX


class ChatStreamRequestTests(unittest.TestCase):
    def test_preserves_text_history_and_ignores_custom_parts(self) -> None:
        request = ChatStreamRequest.model_validate(
            {
                "id": "chat-1",
                "messages": [
                    {
                        "id": "user-1",
                        "role": "user",
                        "parts": [{"type": "text", "text": "Who is Jeyker?"}],
                    },
                    {
                        "id": "assistant-1",
                        "role": "assistant",
                        "parts": [
                            {"type": "text", "text": "He is an engineer."},
                            {
                                "type": "data-candidate-photo",
                                "data": {"src": "/jeyker.jpg"},
                            },
                        ],
                    },
                ],
            }
        )

        self.assertEqual(
            request.to_agent_messages(),
            [
                {"role": "user", "content": "Who is Jeyker?"},
                {"role": "assistant", "content": "He is an engineer."},
            ],
        )

    def test_accepts_legacy_message_body(self) -> None:
        request = ChatStreamRequest.model_validate({"message": "  Hello Django  "})
        self.assertEqual(request.to_agent_messages(), [{"role": "user", "content": "Hello Django"}])

    def test_rejects_empty_messages(self) -> None:
        with self.assertRaises(ValidationError):
            ChatStreamRequest.model_validate({"messages": []})


class UIMessageStreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_preserves_text_and_image_order(self) -> None:
        async def remaining_events():
            yield {"type": "image", "src": "/jeyker.jpg", "alt": "Jeyker Salinas"}
            yield {"type": "message_delta", "text": " Here he is."}

        chunks = [
            chunk
            async for chunk in stream_ui_messages(
                {"type": "message_delta", "text": "Meet Jeyker."},
                remaining_events(),
            )
        ]

        self.assertEqual(chunks[-1], "data: [DONE]\n\n")
        events = [json.loads(chunk.removeprefix("data: ")) for chunk in chunks[:-1]]

        self.assertEqual(
            [event["type"] for event in events],
            [
                "start",
                "start-step",
                "text-start",
                "text-delta",
                "text-end",
                "data-candidate-photo",
                "text-start",
                "text-delta",
                "text-end",
                "finish-step",
                "finish",
            ],
        )
        self.assertEqual(events[5]["data"]["src"], "/jeyker.jpg")

    async def test_streams_verified_knowledge_sources(self) -> None:
        async def remaining_events():
            yield {"type": "message_delta", "text": "Jeyker has RAG experience."}

        chunks = [
            chunk
            async for chunk in stream_ui_messages(
                {"type": "source", "path": "knowledge/projects/educational-rag-platform.md"},
                remaining_events(),
            )
        ]
        events = [json.loads(chunk.removeprefix("data: ")) for chunk in chunks[:-1]]
        source = next(event for event in events if event["type"] == "data-source")

        self.assertEqual(source["data"]["path"], "knowledge/projects/educational-rag-platform.md")

    async def test_serializes_provider_errors(self) -> None:
        async def failing_events():
            await asyncio.sleep(0)
            raise RuntimeError("Provider unavailable")
            yield  # Keeps this callable an async generator.

        chunks = [chunk async for chunk in stream_ui_messages(None, failing_events())]
        events = [json.loads(chunk.removeprefix("data: ")) for chunk in chunks[:-1]]

        self.assertEqual(events[-1]["type"], "error")
        self.assertTrue(events[-1]["errorText"].startswith(ERROR_PREFIX))
        payload = json.loads(events[-1]["errorText"].removeprefix(ERROR_PREFIX))
        self.assertEqual(payload["code"], "chat_generation_failed")
        self.assertEqual(len(payload["reference"]), 12)
        self.assertEqual(chunks[-1], "data: [DONE]\n\n")

    async def test_activity_updates_reuse_id_without_splitting_markdown(self) -> None:
        async def remaining_events():
            yield {"type": "activity", "data": {"id": "run-1", "kind": "tool", "tool_name": "search_documents", "status": "running"}}
            yield {"type": "activity", "data": {"id": "run-1", "kind": "tool", "tool_name": "search_documents", "status": "completed", "result_count": 0}}
            yield {"type": "feature", "feature": "streaming"}
            yield {"type": "message_delta", "text": "bold**"}
        chunks = [chunk async for chunk in stream_ui_messages({"type": "message_delta", "text": "**"}, remaining_events())]
        events = [json.loads(chunk.removeprefix("data: ")) for chunk in chunks[:-1]]
        activities = [event for event in events if event["type"] == "data-agent-activity"]
        self.assertEqual([event["id"] for event in activities], ["activity-run-1", "activity-run-1"])
        self.assertEqual(sum(event["type"] == "text-start" for event in events), 1)
        self.assertEqual(sum(event["type"] == "text-end" for event in events), 1)
        self.assertTrue(any(event["type"] == "data-feature-used" for event in events))

    def test_history_does_not_send_activity_or_discovery_back_to_model(self) -> None:
        request = ChatStreamRequest.model_validate({"messages": [{
            "id": "a", "role": "assistant", "parts": [
                {"type": "data-agent-activity", "data": {"id": "x", "status": "completed"}},
                {"type": "data-feature-used", "data": {"feature": "streaming"}},
                {"type": "text", "text": "Public answer"},
            ],
        }]})
        self.assertEqual(request.to_agent_messages(), [{"role": "assistant", "content": "Public answer"}])


if __name__ == "__main__":
    unittest.main()
