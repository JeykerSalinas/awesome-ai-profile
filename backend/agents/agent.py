import json
from collections.abc import AsyncIterator
from typing import Literal, TypedDict

from langchain.agents import create_agent
from langchain_core.messages import ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.tools import build_search_documents_tool, get_candidate_photo, get_profile_section, search_experience

from services.prompt_service import SupportedLocale, build_professional_system_prompt
from settings import get_settings


class AgentMessageDeltaEvent(TypedDict):
    type: Literal["message_delta"]
    text: str


class AgentImageEvent(TypedDict):
    type: Literal["image"]
    src: str
    alt: str


class AgentSourceEvent(TypedDict):
    type: Literal["source"]
    path: str


AgentStreamEvent = AgentMessageDeltaEvent | AgentImageEvent | AgentSourceEvent


def get_agent(locale: SupportedLocale = "en", document_ids: list[str] | None = None):
    settings = get_settings()

    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY is not configured.")

    model = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite",
        google_api_key=settings.google_api_key,
    )

    return create_agent(
        model=model,
        tools=[get_candidate_photo, get_profile_section, search_experience, build_search_documents_tool(document_ids)],
        system_prompt=build_professional_system_prompt(locale),
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
) -> AsyncIterator[AgentStreamEvent]:
    agent = get_agent(locale, document_ids)
    emitted_sources: set[str] = set()

    async for token, metadata in agent.astream(
        {"messages": messages},
        stream_mode="messages",
    ):
        if isinstance(token, ToolMessage):
            if token.name == "get_candidate_photo":
                src = str(token.text)
                if src:
                    yield {
                        "type": "image",
                        "src": src,
                        "alt": "Jeyker Salinas",
                    }
                continue

            if token.name in {"get_profile_section", "search_experience", "search_documents"}:
                try:
                    payload = json.loads(str(token.text))
                except (TypeError, ValueError):
                    continue

                sources = []
                if isinstance(payload.get("source"), str):
                    sources.append(payload["source"])
                for result in payload.get("results", []):
                    if isinstance(result, dict) and isinstance(result.get("source"), str):
                        sources.append(result["source"])

                for source in sources:
                    if source not in emitted_sources:
                        emitted_sources.add(source)
                        yield {"type": "source", "path": source}
            continue

        text = str(token.text)
        if text:
            yield {
                "type": "message_delta",
                "text": text,
            }
