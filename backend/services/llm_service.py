from collections.abc import AsyncIterator

from google import genai

from settings import get_settings

settings = get_settings()


class LLMServiceError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_client() -> genai.Client:
    if not settings.google_api_key:
        raise LLMServiceError(
            "GOOGLE_API_KEY is not configured.",
            status_code=500,
        )

    return genai.Client(api_key=settings.google_api_key)


async def generate_response(message: str) -> str:
    client = get_client()

    try:
        client.interactions.create(
            model="gemini-3.1-flash-lite",
            input="Explain how AI works in a few words",
        )
    except Exception as exc:
        raise LLMServiceError(f"LLM request failed: {exc}") from exc

    return f"AI received: {message}"


async def generate_response_stream(message: str) -> AsyncIterator[str]:
    client = get_client()

    try:
        response = client.interactions.create(
            model="gemini-3.1-flash-lite",
            input=message,
            stream=True,
        )
    except Exception as exc:
        raise LLMServiceError(f"LLM request failed: {exc}") from exc

    try:
        for event in response:
            if event.event_type == "step.delta" and event.delta.type == "text":
                yield event.delta.text
    except Exception as exc:
        raise LLMServiceError(f"LLM stream failed: {exc}") from exc
