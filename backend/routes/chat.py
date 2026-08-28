import logging
from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse, StreamingResponse

from schemas.chat import ChatRequest, ChatResponse, ChatStreamRequest
from services.agents_service import generate_response, generate_response_stream
from services.ai_sdk_stream import stream_ui_messages
from services.chat_error_service import classify_chat_error, diagnostic_summary


router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request) -> ChatResponse | PlainTextResponse:
    request_id = http_request.state.request_id
    try:
        message = await generate_response(request.message, request.locale)
    except Exception as exc:
        public_error = classify_chat_error(exc)
        logger.error(
            "chat_request_failed",
            extra={
                "request_id": request_id,
                "error_code": public_error.code,
                "error_type": type(exc).__name__,
                "provider_detail": diagnostic_summary(exc),
            },
            exc_info=True,
        )
        return PlainTextResponse(
            public_error.serialize(request.locale, request_id),
            status_code=public_error.status_code,
            headers={"X-Request-ID": request_id, "X-Error-Code": public_error.code},
        )

    return ChatResponse(message=message)


@router.post("/stream")
async def stream_chat(
    request: ChatStreamRequest,
    http_request: Request,
) -> Response:
    request_id = http_request.state.request_id
    stream = generate_response_stream(request.to_agent_messages(), request.locale, request.documents)

    try:
        first_chunk = await anext(stream)
    except StopAsyncIteration:
        first_chunk = None
    except Exception as exc:
        public_error = classify_chat_error(exc)
        logger.error(
            "chat_stream_failed_before_response",
            extra={
                "request_id": request_id,
                "error_code": public_error.code,
                "error_type": type(exc).__name__,
                "provider_detail": diagnostic_summary(exc),
            },
            exc_info=True,
        )
        return PlainTextResponse(
            public_error.serialize(request.locale, request_id),
            status_code=public_error.status_code,
            headers={"X-Request-ID": request_id, "X-Error-Code": public_error.code},
        )

    logger.info(
        "chat_stream_started",
        extra={
            "request_id": request_id,
            "locale": request.locale,
            "message_count": len(request.to_agent_messages()),
            "document_count": len(request.documents),
        },
    )

    return StreamingResponse(
        stream_ui_messages(first_chunk, stream, request.locale, request_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "x-vercel-ai-ui-message-stream": "v1",
            "X-Request-ID": request_id,
        },
    )
