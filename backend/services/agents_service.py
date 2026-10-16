from collections.abc import AsyncIterator

from agents.agent import AgentStreamEvent, ask_agent, stream_agent
from services.prompt_service import SupportedLocale


async def generate_response(message: str, locale: SupportedLocale = "en", profile_id: str = "jeyker") -> str:
    return await ask_agent(message, locale, profile_id)


async def generate_response_stream(
    messages: list[dict[str, str]],
    locale: SupportedLocale = "en",
    document_ids: list[str] | None = None,
    profile_id: str = "jeyker",
) -> AsyncIterator[AgentStreamEvent]:
    async for chunk in stream_agent(messages, locale, document_ids, profile_id):
        yield chunk
