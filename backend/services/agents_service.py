from collections.abc import AsyncIterator

from agents.agent import AgentStreamEvent, ask_agent, ask_agent_messages, stream_agent
from services.prompt_service import SupportedLocale


async def generate_response(message: str, locale: SupportedLocale = "en") -> str:
    return await ask_agent(message, locale)


async def generate_response_for_messages(
    messages: list[dict[str, str]],
    locale: SupportedLocale = "en",
) -> str:
    return await ask_agent_messages(messages, locale)


async def generate_response_stream(
    messages: list[dict[str, str]],
    locale: SupportedLocale = "en",
    document_ids: list[str] | None = None,
) -> AsyncIterator[AgentStreamEvent]:
    async for chunk in stream_agent(messages, locale, document_ids):
        yield chunk
