from collections.abc import AsyncIterator

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.tools import (
    build_search_documents_tool,
    get_candidate_photo,
    get_contact_details,
    get_profile_section,
    search_experience,
)
from agents.activity import observe_agent_stream
from agents.events import AgentStreamEvent

from services.prompt_service import SupportedLocale, build_professional_system_prompt
from settings import get_settings


def get_agent(locale: SupportedLocale = "en", document_ids: list[str] | None = None):
    settings = get_settings()

    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY is not configured.")

    model = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite",
        google_api_key=settings.google_api_key,
        include_thoughts=False,
    )

    return create_agent(
        model=model,
        tools=[
            get_candidate_photo,
            get_contact_details,
            get_profile_section,
            search_experience,
            build_search_documents_tool(document_ids),
        ],
        system_prompt=build_professional_system_prompt(locale),
    )


async def ask_agent(message: str, locale: SupportedLocale = "en") -> str:
    return await ask_agent_messages(
        [{"role": "user", "content": message}],
        locale,
    )


async def ask_agent_messages(
    messages: list[dict[str, str]],
    locale: SupportedLocale = "en",
) -> str:
    agent = get_agent(locale)

    result = await agent.ainvoke({"messages": messages})

    last_message = result["messages"][-1]

    return last_message.text


async def stream_agent(
    messages: list[dict[str, str]],
    locale: SupportedLocale = "en",
    document_ids: list[str] | None = None,
) -> AsyncIterator[AgentStreamEvent]:
    agent = get_agent(locale, document_ids)
    async for event in observe_agent_stream(agent, messages):
        yield event
