from collections.abc import AsyncIterator

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.tools import build_search_documents_tool, get_candidate_photo, get_profile_section, search_experience, offer_contact, get_contact_details, open_contact_form
from agents.activity import observe_agent_stream
from agents.events import AgentStreamEvent

from services.prompt_service import SupportedLocale, build_professional_system_prompt
from settings import get_settings
from schemas.contact import AgentContactContext


def contact_tools(context: AgentContactContext):
    if context.choice == "details":
        return [get_contact_details]
    if context.choice == "compose":
        return [open_contact_form]
    return [] if context.offered else [offer_contact]


def get_agent(locale: SupportedLocale = "en", document_ids: list[str] | None = None, contact: AgentContactContext | None = None):
    settings = get_settings()
    contact = contact or AgentContactContext()

    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY is not configured.")

    model = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite",
        google_api_key=settings.google_api_key,
        include_thoughts=False,
    )

    return create_agent(
        model=model,
        tools=[get_candidate_photo, get_profile_section, search_experience, build_search_documents_tool(document_ids), *contact_tools(contact)],
        system_prompt=build_professional_system_prompt(locale, contact),
    )


async def ask_agent(message: str, locale: SupportedLocale = "en") -> str:
    agent = get_agent(locale)

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
    contact: AgentContactContext | None = None,
) -> AsyncIterator[AgentStreamEvent]:
    agent = get_agent(locale, document_ids, contact)
    async for event in observe_agent_stream(agent, messages):
        yield event
