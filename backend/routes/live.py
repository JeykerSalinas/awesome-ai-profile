import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError

from schemas.live import LiveSessionStart
from services.live_service import LiveServiceError, run_live_session
from settings import get_settings


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/live", tags=["live"])


def _origin_is_allowed(websocket: WebSocket) -> bool:
    origin = websocket.headers.get("origin")
    if not origin:
        return True
    return origin in get_settings().cors_allow_origins_list


@router.websocket("/ws")
async def live_conversation(websocket: WebSocket) -> None:
    if not _origin_is_allowed(websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    try:
        start = LiveSessionStart.model_validate_json(await websocket.receive_text())
        await run_live_session(
            websocket,
            start.locale,
            start.documents,
            [message.model_dump() for message in start.history],
        )
    except ValidationError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    except WebSocketDisconnect:
        return
    except LiveServiceError as exc:
        logger.warning(
            "Live conversation closed: code=%s stage=%s detail=%s",
            exc.code,
            exc.stage,
            exc.detail,
        )
        try:
            await websocket.send_json(exc.to_event())
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except RuntimeError:
            pass
