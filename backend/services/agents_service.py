from collections.abc import AsyncIterator

from agents.agent import AgentStreamEvent, ask_agent, stream_agent


async def generate_response(message: str) -> str:
    return await ask_agent(message)


async def generate_response_stream(message: str) -> AsyncIterator[AgentStreamEvent]:
    async for chunk in stream_agent(message):
        yield chunk
