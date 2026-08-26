from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from agents.events import AgentStreamEvent


def encode_sse_event(event: dict[str, object]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


async def stream_ui_messages(
    first_chunk: AgentStreamEvent | None,
    stream: AsyncIterator[AgentStreamEvent],
) -> AsyncIterator[str]:
    message_id = f"assistant-{uuid4().hex}"
    text_id: str | None = None

    yield encode_sse_event({"type": "start", "messageId": message_id})
    yield encode_sse_event({"type": "start-step"})

    try:
        async def agent_events() -> AsyncIterator[AgentStreamEvent]:
            if first_chunk is not None:
                yield first_chunk

            async for event in stream:
                yield event

        async for event in agent_events():
            if event["type"] in {"contact_offer", "contact_form"}:
                if text_id is not None:
                    yield encode_sse_event({"type": "text-end", "id": text_id})
                    text_id = None
                part_name = event["type"].replace("_", "-")
                yield encode_sse_event({"type": f"data-{part_name}", "id": part_name, "data": {"mode": event.get("mode", "demo")}})
                continue

            if event["type"] == "feature":
                yield encode_sse_event({
                    "type": "data-feature-used", "id": f"feature-{event['feature']}",
                    "data": {"feature": event["feature"]},
                })
                continue

            if event["type"] == "activity":
                # Reuse the same ID: AI SDK updates one row instead of appending duplicates.
                # Activity does not split a text block (which could break streamed Markdown).
                yield encode_sse_event({
                    "type": "data-agent-activity",
                    "id": f"activity-{event['data']['id']}",
                    "data": event["data"],
                })
                continue

            if event["type"] == "message_delta":
                if text_id is None:
                    text_id = f"text-{uuid4().hex}"
                    yield encode_sse_event({"type": "text-start", "id": text_id})

                yield encode_sse_event(
                    {"type": "text-delta", "id": text_id, "delta": event["text"]}
                )
                continue

            if text_id is not None:
                yield encode_sse_event({"type": "text-end", "id": text_id})
                text_id = None

            if event["type"] == "image":
                yield encode_sse_event(
                    {
                        "type": "data-candidate-photo",
                        "id": f"photo-{uuid4().hex}",
                        "data": {"src": event["src"], "alt": event["alt"]},
                    }
                )
                continue

            yield encode_sse_event(
                {
                    "type": "data-source",
                    "id": f"source-{uuid4().hex}",
                    "data": {"path": event["path"]},
                }
            )

        if text_id is not None:
            yield encode_sse_event({"type": "text-end", "id": text_id})

        yield encode_sse_event({"type": "finish-step"})
        yield encode_sse_event({"type": "finish", "finishReason": "stop"})
    except Exception:
        yield encode_sse_event({"type": "error", "errorText": "The response could not be completed. Please try again."})

    yield "data: [DONE]\n\n"
