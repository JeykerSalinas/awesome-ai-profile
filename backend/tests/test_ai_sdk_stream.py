import asyncio
import json
import unittest

from pydantic import ValidationError

from schemas.chat import ChatStreamRequest
from services.ai_sdk_stream import stream_ui_messages


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

    async def test_serializes_provider_errors(self) -> None:
        async def failing_events():
            await asyncio.sleep(0)
            raise RuntimeError("Provider unavailable")
            yield  # Keeps this callable an async generator.

        chunks = [chunk async for chunk in stream_ui_messages(None, failing_events())]
        events = [json.loads(chunk.removeprefix("data: ")) for chunk in chunks[:-1]]

        self.assertEqual(events[-1], {"type": "error", "errorText": "Provider unavailable"})
        self.assertEqual(chunks[-1], "data: [DONE]\n\n")


if __name__ == "__main__":
    unittest.main()
