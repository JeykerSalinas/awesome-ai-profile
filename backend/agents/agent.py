from collections.abc import AsyncIterator

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.tools import (
    build_search_documents_tool,
    build_profile_tools,
    build_agent_tools,
)
from agents.activity import observe_agent_stream
from agents.events import AgentStreamEvent

from services.prompt_service import SupportedLocale, build_professional_system_prompt
from settings import get_settings
from services.profile_service import get_profile, profile_settings


def get_agent(locale: SupportedLocale = "en", document_ids: list[str] | None = None, profile_id: str = "jeyker"):
    settings = profile_settings(profile_id, get_settings())

    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY is not configured.")

    model = ChatGoogleGenerativeAI(
        model=get_profile(profile_id).agent.services.chat_model,
        google_api_key=settings.google_api_key,
        include_thoughts=False,
    )

    return create_agent(
        model=model,
        tools=build_agent_tools(document_ids, profile_id),
        system_prompt=build_professional_system_prompt(locale, profile_id),
    )


async def ask_agent(message: str, locale: SupportedLocale = "en", profile_id: str = "jeyker") -> str:
    agent = get_agent(locale, profile_id=profile_id)

    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": message,
                }
            ]
        }
    )

    last_message = result["messages"][-1]

    return last_message.text


async def stream_agent(
    messages: list[dict[str, str]],
    locale: SupportedLocale = "en",
    document_ids: list[str] | None = None,
    profile_id: str = "jeyker",
) -> AsyncIterator[AgentStreamEvent]:
    agent = get_agent(locale, document_ids, profile_id)
    async for event in observe_agent_stream(agent, messages):
        yield event
