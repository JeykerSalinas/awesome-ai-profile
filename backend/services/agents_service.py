from collections.abc import AsyncIterator

from agents.agent import AgentStreamEvent, ask_agent, stream_agent
from services.prompt_service import SupportedLocale


async def generate_response(message: str, locale: SupportedLocale = "en") -> str:
    return await ask_agent(message, locale)


async def generate_response_stream(
    messages: list[dict[str, str]],
    locale: SupportedLocale = "en",
) -> AsyncIterator[AgentStreamEvent]:
    async for chunk in stream_agent(messages, locale):
        yield chunk
