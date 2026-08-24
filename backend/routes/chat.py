from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from schemas.chat import ChatRequest, ChatResponse
from schemas.events import DoneEvent, ErrorData, ErrorEvent, MessageDeltaData, MessageDeltaEvent
from services.agents_service import generate_response, generate_response_stream


router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)


async def stream_chat_events(first_chunk: str | None, stream: AsyncIterator[str]) -> AsyncIterator[str]:
    try:
        if first_chunk is not None:
            yield MessageDeltaEvent(
                event="message_delta",
                data=MessageDeltaData(text=first_chunk),
            ).model_dump_json() + "\n"

        async for chunk in stream:
            yield MessageDeltaEvent(
                event="message_delta",
                data=MessageDeltaData(text=chunk),
            ).model_dump_json() + "\n"

        yield DoneEvent(event="done", data={}).model_dump_json() + "\n"
    except Exception as exc:
        yield ErrorEvent(
            event="error",
            data=ErrorData(message=str(exc)),
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
