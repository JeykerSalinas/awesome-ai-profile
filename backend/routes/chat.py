from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from agents.agent import AgentStreamEvent
from schemas.chat import ChatRequest, ChatResponse
from schemas.events import DoneEvent, ErrorData, ErrorEvent, ImageData, ImageEvent, MessageDeltaData, MessageDeltaEvent
from services.agents_service import generate_response, generate_response_stream


router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)


async def stream_chat_events(
    first_chunk: AgentStreamEvent | None,
    stream: AsyncIterator[AgentStreamEvent],
) -> AsyncIterator[str]:
    try:
        if first_chunk is not None:
            yield serialize_stream_event(first_chunk)

        async for chunk in stream:
            yield serialize_stream_event(chunk)

        yield DoneEvent(event="done", data={}).model_dump_json() + "\n"
    except Exception as exc:
        yield ErrorEvent(
            event="error",
            data=ErrorData(message=str(exc)),
        ).model_dump_json() + "\n"


def serialize_stream_event(event: AgentStreamEvent) -> str:
    if event["type"] == "image":
        return ImageEvent(
            event="image",
            data=ImageData(src=event["src"], alt=event["alt"]),
        ).model_dump_json() + "\n"

    return MessageDeltaEvent(
        event="message_delta",
        data=MessageDeltaData(text=event["text"]),
    ).model_dump_json() + "\n"


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        message = await generate_response(request.message)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ChatResponse(message=message)


@router.post("/stream")
async def stream_chat(request: ChatRequest):
    stream = generate_response_stream(request.message)

    try:
        first_chunk = await anext(stream)
    except StopAsyncIteration:
        first_chunk = None
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return StreamingResponse(
        stream_chat_events(first_chunk, stream),
        media_type="application/x-ndjson",
    )
