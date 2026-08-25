from collections.abc import AsyncIterator
from typing import Literal, TypedDict

from langchain.agents import create_agent
from langchain_core.messages import ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.tools import get_candidate_photo

from settings import get_settings


class AgentMessageDeltaEvent(TypedDict):
    type: Literal["message_delta"]
    text: str


class AgentImageEvent(TypedDict):
    type: Literal["image"]
    src: str
    alt: str


AgentStreamEvent = AgentMessageDeltaEvent | AgentImageEvent


def get_agent():
    settings = get_settings()

    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY is not configured.")

    model = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite",
        google_api_key=settings.google_api_key,
    )

    return create_agent(
        model=model,
        tools=[ get_candidate_photo ],
        system_prompt="You are Jeyker's professional AI representative. You are very funny. Only answer about jeyker when explictly ask you about him",
    )


async def ask_agent(message: str) -> str:
    agent = get_agent()

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
) -> AsyncIterator[AgentStreamEvent]:
    agent = get_agent()

    async for token, metadata in agent.astream(
        {"messages": messages},
        stream_mode="messages",
    ):
        if isinstance(token, ToolMessage) and token.name == "get_candidate_photo":
            src = str(token.text)
            if src:
                yield {
                    "type": "image",
                    "src": src,
                    "alt": "Jeyker Salinas",
                }
            continue

        text = str(token.text)
        if text:
            yield {
                "type": "message_delta",
                "text": text,
            }
