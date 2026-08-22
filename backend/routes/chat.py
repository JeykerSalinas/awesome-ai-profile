from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from schemas.chat import ChatRequest, ChatResponse
from schemas.events import DoneEvent, ErrorData, ErrorEvent, MessageDeltaData, MessageDeltaEvent
from services.llm_service import generate_response, generate_response_stream


router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    response = await generate_response(request.message)

    return ChatResponse(
        message=response
    )


async def stream_chat_events(message: str) -> AsyncIterator[str]:
    try:
        async for chunk in generate_response_stream(message):
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


@router.post("/stream")
async def stream_chat(request: ChatRequest):
    return StreamingResponse(
        stream_chat_events(request.message),
        media_type="application/x-ndjson",
    )
