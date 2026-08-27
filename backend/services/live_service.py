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


class LiveServiceError(Exception):
    pass


def build_live_config(
    locale: SupportedLocale,
    document_ids: list[str] | None = None,
) -> types.LiveConnectConfig:
    settings = get_settings()
    live_tools = build_live_tools(document_ids)
    return types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO],
        system_instruction=build_professional_system_prompt(locale),
        tools=[build_live_tool_config(live_tools)],
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
    if transcription and transcription.text:
        await websocket.send_json(
            {
                "type": "transcript",
                "role": role,
                "text": transcription.text,
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
) -> None:
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
                    await websocket.send_json({"type": "turn_complete"})

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
        raise LiveServiceError("GOOGLE_API_KEY is not configured.")

    live_tools = build_live_tools(document_ids)
    client: genai.Client | None = None

    try:
        client = genai.Client(api_key=settings.google_api_key)
        async with client.aio.live.connect(
            model=settings.gemini_live_model,
            config=build_live_config(locale, document_ids),
        ) as session:
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
            await websocket.send_json({"type": "ready"})
            browser_task = asyncio.create_task(_receive_browser_audio(websocket, session))
            gemini_task = asyncio.create_task(
                _relay_gemini_output(websocket, session, live_tools)
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
        logger.exception("Gemini Live session failed")
        raise LiveServiceError("The live conversation could not be completed.") from exc
    finally:
        if client:
            with suppress(Exception):
                await client.aio.aclose()
            with suppress(Exception):
                client.close()
