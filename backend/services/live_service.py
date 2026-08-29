from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types

from services.live_tools_service import (
    build_live_tool_config,
    build_live_tools,
    execute_live_tool,
)
from services.prompt_service import SupportedLocale, build_professional_system_prompt
from settings import get_settings


logger = logging.getLogger(__name__)
INPUT_AUDIO_MIME_TYPE = "audio/pcm;rate=16000"
INITIAL_GREETINGS: dict[SupportedLocale, str] = {
    "es": "Hola, soy Django, asistente profesional de Jeyker.",
    "en": "Hi, I'm Django, Jeyker's professional assistant.",
}


class LiveServiceError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "live_service_error",
        detail: str | None = None,
        retryable: bool = False,
        stage: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.detail = detail
        self.retryable = retryable
        self.stage = stage

    def to_event(self) -> dict[str, Any]:
        event: dict[str, Any] = {
            "type": "error",
            "code": self.code,
            "message": str(self),
            "retryable": self.retryable,
        }
        if self.detail:
            event["detail"] = self.detail
        if self.stage:
            event["stage"] = self.stage
        return event


def describe_live_error(exc: Exception, stage: str) -> LiveServiceError:
    provider_message = " ".join(str(exc).split())
    normalized = provider_message.lower()

    if "prepayment credits are depleted" in normalized:
        return LiveServiceError(
            "The Google AI project has no available prepaid credit.",
            code="billing_credits_depleted",
            detail="Gemini Live: prepayment credits are depleted.",
            retryable=False,
            stage=stage,
        )
    if "quota" in normalized or "rate limit" in normalized or "resource exhausted" in normalized:
        return LiveServiceError(
            "Gemini Live temporarily rejected the session because its quota was exceeded.",
            code="quota_exceeded",
            detail=provider_message[:500],
            retryable=True,
            stage=stage,
        )
    if "1011" in normalized or "internal error occurred" in normalized:
        return LiveServiceError(
            "Gemini Live closed the session because of an internal provider error.",
            code="provider_internal_error",
            detail=provider_message[:500] or "Gemini Live WebSocket closed with code 1011.",
            retryable=True,
            stage=stage,
        )

    return LiveServiceError(
        "The live conversation could not be completed.",
        code="live_session_failed",
        detail=provider_message[:500] or type(exc).__name__,
        retryable=True,
        stage=stage,
    )


def build_live_config(
    locale: SupportedLocale,
    document_ids: list[str] | None = None,
    *,
    include_tools: bool = True,
) -> types.LiveConnectConfig:
    settings = get_settings()
    live_tools = build_live_tools(document_ids)
    return types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO],
        system_instruction=build_professional_system_prompt(locale),
        tools=[build_live_tool_config(live_tools)] if include_tools else None,
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=settings.gemini_live_voice,
                )
            )
        ),
    )


async def _receive_browser_audio(websocket: WebSocket, session: Any) -> None:
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            raise WebSocketDisconnect(message.get("code", 1000))

        audio = message.get("bytes")
        if audio:
            await session.send_realtime_input(
                audio=types.Blob(data=audio, mime_type=INPUT_AUDIO_MIME_TYPE)
            )
            continue

        text = message.get("text")
        if text == '{"type":"stop"}':
            return


async def _send_transcription(websocket: WebSocket, role: str, transcription: Any) -> None:
    if transcription and (transcription.text or transcription.finished):
        await websocket.send_json(
            {
                "type": "transcript",
                "role": role,
                "text": transcription.text or "",
                "finished": bool(transcription.finished),
            }
        )


async def _handle_tool_calls(
    websocket: WebSocket,
    session: Any,
    tool_call: types.LiveServerToolCall,
    live_tools: dict[str, Any],
) -> None:
    responses: list[types.FunctionResponse] = []
    for call in tool_call.function_calls or []:
        name = call.name or "unknown"
        await websocket.send_json({"type": "tool", "name": name, "status": "running"})
        tool = live_tools.get(name)
        if tool is None:
            result: Any = {"error": f"Unknown tool: {name}"}
        else:
            result = await execute_live_tool(tool, call.args)
        responses.append(
            types.FunctionResponse(
                id=call.id,
                name=name,
                response={"result": result},
            )
        )
        completed_event: dict[str, Any] = {
            "type": "tool",
            "name": name,
            "status": "completed",
        }
        if name == "get_candidate_photo" and isinstance(result, str):
            completed_event["result"] = result
        await websocket.send_json(completed_event)

    if responses:
        await session.send_tool_response(function_responses=responses)


async def _relay_gemini_output(
    websocket: WebSocket,
    session: Any,
    live_tools: dict[str, Any],
    max_turns: int,
    uncounted_turns: int = 0,
) -> None:
    turns_used = 0
    while True:
        async for message in session.receive():
            if message.data:
                await websocket.send_bytes(message.data)

            if message.tool_call:
                await _handle_tool_calls(websocket, session, message.tool_call, live_tools)

            content = message.server_content
            if content:
                if content.interrupted:
                    await websocket.send_json({"type": "interrupted"})
                await _send_transcription(websocket, "user", content.input_transcription)
                await _send_transcription(websocket, "assistant", content.output_transcription)
                if content.turn_complete:
                    if uncounted_turns > 0:
                        uncounted_turns -= 1
                        await websocket.send_json(
                            {
                                "type": "turn_complete",
                                "turns_used": turns_used,
                                "turns_remaining": max_turns,
                                "counted": False,
                            }
                        )
                        continue
                    turns_used += 1
                    await websocket.send_json(
                        {
                            "type": "turn_complete",
                            "turns_used": turns_used,
                            "turns_remaining": max(0, max_turns - turns_used),
                        }
                    )
                    if turns_used >= max_turns:
                        await websocket.send_json(
                            {
                                "type": "limit_reached",
                                "max_turns": max_turns,
                            }
                        )
                        return

            if message.go_away:
                await websocket.send_json({"type": "ending"})


async def run_live_session(
    websocket: WebSocket,
    locale: SupportedLocale,
    document_ids: list[str] | None = None,
    history: list[dict[str, str]] | None = None,
) -> None:
    settings = get_settings()
    if not settings.google_api_key:
        raise LiveServiceError(
            "GOOGLE_API_KEY is not configured.",
            code="configuration_error",
            stage="configuration",
        )

    live_tools = build_live_tools(document_ids)
    client: genai.Client | None = None

    stage = "connecting"
    try:
        client = genai.Client(api_key=settings.google_api_key)
        async with client.aio.live.connect(
            model=settings.gemini_live_model,
            config=build_live_config(locale, document_ids),
        ) as session:
            stage = "seeding_history"
            if history:
                await session.send_client_content(
                    turns=[
                        {
                            "role": "model" if item["role"] == "assistant" else "user",
                            "parts": [{"text": item["content"]}],
                        }
                        for item in history
                    ],
                    turn_complete=False,
                )
            stage = "greeting"
            greeting = INITIAL_GREETINGS[locale]
            await session.send_client_content(
                turns=[
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": (
                                    "Start the voice conversation now. Your complete "
                                    "response must be exactly this sentence, without "
                                    f"quotation marks: {greeting}"
                                )
                            }
                        ],
                    }
                ],
                turn_complete=True,
            )
            stage = "streaming"
            await websocket.send_json(
                {"type": "ready", "max_turns": settings.gemini_live_max_turns}
            )
            browser_task = asyncio.create_task(_receive_browser_audio(websocket, session))
            gemini_task = asyncio.create_task(
                _relay_gemini_output(
                    websocket,
                    session,
                    live_tools,
                    settings.gemini_live_max_turns,
                    uncounted_turns=1,
                )
            )
            done, pending = await asyncio.wait(
                {browser_task, gemini_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            for task in pending:
                with suppress(asyncio.CancelledError):
                    await task
            for task in done:
                task.result()
    except WebSocketDisconnect:
        return
    except Exception as exc:
        logger.exception("Gemini Live session failed during %s", stage)
        raise describe_live_error(exc, stage) from exc
    finally:
        if client:
            with suppress(Exception):
                await client.aio.aclose()
            with suppress(Exception):
                client.close()
