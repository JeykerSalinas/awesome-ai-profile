from __future__ import annotations

import argparse
import asyncio
from contextlib import suppress
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from google import genai
from google.genai import types

from services.live_service import build_live_config, describe_live_error
from services.live_tools_service import build_live_tools, execute_live_tool
from settings import get_settings


async def run_diagnostic(mode: str, locale: str) -> None:
    settings = get_settings()
    if not settings.google_api_key:
        raise SystemExit("GOOGLE_API_KEY is not configured in backend/.env")

    include_tools = mode == "tools"
    live_tools = build_live_tools()
    client = genai.Client(api_key=settings.google_api_key)
    stage = "connecting"
    audio_bytes = 0
    tool_calls = 0

    print(f"[{mode}] connecting to {settings.gemini_live_model}")
    try:
        async with client.aio.live.connect(
            model=settings.gemini_live_model,
            config=build_live_config(locale, include_tools=include_tools),
        ) as session:
            stage = "streaming"
            prompt = (
                "Use the profile tools to tell me one professional skill Jeyker has. "
                "Answer in one short sentence."
                if include_tools
                else "Say hello in one short sentence."
            )
            await session.send_client_content(
                turns=[{"role": "user", "parts": [{"text": prompt}]}],
                turn_complete=True,
            )

            while True:
                async for message in session.receive():
                    if message.data:
                        audio_bytes += len(message.data)

                    if message.tool_call:
                        responses: list[types.FunctionResponse] = []
                        for call in message.tool_call.function_calls or []:
                            tool_calls += 1
                            tool = live_tools.get(call.name or "")
                            result = (
                                await execute_live_tool(tool, call.args)
                                if tool
                                else {"error": f"Unknown tool: {call.name}"}
                            )
                            responses.append(
                                types.FunctionResponse(
                                    id=call.id,
                                    name=call.name,
                                    response={"result": result},
                                )
                            )
                        if responses:
                            await session.send_tool_response(function_responses=responses)

                    content = message.server_content
                    if content and content.output_transcription and content.output_transcription.text:
                        print(f"[{mode}] transcript: {content.output_transcription.text}")
                    if content and content.turn_complete:
                        print(
                            f"[{mode}] OK: received {audio_bytes} audio bytes "
                            f"and {tool_calls} tool call(s)"
                        )
                        return
    except Exception as exc:
        error = describe_live_error(exc, stage)
        print(
            f"[{mode}] FAILED: code={error.code} stage={error.stage} "
            f"detail={error.detail}"
        )
        raise SystemExit(1) from exc
    finally:
        with suppress(Exception):
            await client.aio.aclose()
        with suppress(Exception):
            client.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnose Gemini Live independently of the browser."
    )
    parser.add_argument("--mode", choices=("minimal", "tools"), default="minimal")
    parser.add_argument("--locale", choices=("en", "es"), default="es")
    args = parser.parse_args()
    asyncio.run(run_diagnostic(args.mode, args.locale))


if __name__ == "__main__":
    main()
