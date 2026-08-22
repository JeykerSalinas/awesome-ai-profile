from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from schemas.chat import ChatRequest, ChatResponse
from schemas.events import DoneEvent, ErrorData, ErrorEvent, MessageDeltaData, MessageDeltaEvent
from services.llm_service import LLMServiceError, generate_response, generate_response_stream


router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        response = await generate_response(request.message)
    except LLMServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return ChatResponse(
        message=response
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
    except LLMServiceError as exc:
        yield ErrorEvent(
            event="error",
            data=ErrorData(message=exc.message),
        ).model_dump_json() + "\n"


@router.post("/stream")
async def stream_chat(request: ChatRequest):
    stream = generate_response_stream(request.message)

    try:
        first_chunk = await anext(stream)
    except StopAsyncIteration:
        first_chunk = None
    except LLMServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return StreamingResponse(
        stream_chat_events(first_chunk, stream),
        media_type="application/x-ndjson",
    )
