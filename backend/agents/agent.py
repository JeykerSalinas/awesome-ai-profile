from collections.abc import AsyncIterator

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from settings import get_settings


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
        tools=[],
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


async def stream_agent(message: str) -> AsyncIterator[str]:
    agent = get_agent()

    async for token, metadata in agent.astream(
        {
            "messages": [
                {
                    "role": "user",
                    "content": message,
                }
            ]
        },
        stream_mode="messages",
    ):
        if token.text:
            yield token.text
