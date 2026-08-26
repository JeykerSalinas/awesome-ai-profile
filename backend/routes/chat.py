from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from schemas.chat import ChatRequest, ChatResponse, ChatStreamRequest
from services.agents_service import generate_response, generate_response_stream
from services.ai_sdk_stream import stream_ui_messages


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        message = await generate_response(request.message, request.locale)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ChatResponse(message=message)


@router.post("/stream")
async def stream_chat(request: ChatStreamRequest) -> StreamingResponse:
    stream = generate_response_stream(request.to_agent_messages(), request.locale, request.documents, request.contact_context())

    try:
        first_chunk = await anext(stream)
    except StopAsyncIteration:
        first_chunk = None
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return StreamingResponse(
        stream_ui_messages(first_chunk, stream),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "x-vercel-ai-ui-message-stream": "v1",
        },
    )
