from google import genai
from settings import get_settings

settings = get_settings()
client = genai.Client(api_key=settings.google_api_key)



async def generate_response(message: str) -> str:
    stream = client.interactions.create(
        model="gemini-3.1-flash-lite",
        input="Explain how AI works in a few words",
        # stream=True
    )
    # for event in stream:
    #     if event.event_type == "step.delta":
    #         if event.delta.type == "text":
    #             print(event.delta.text, end="", flush=True)
    return f"AI received: {message}"

async def generate_response_stream(message: str):
    response = client.interactions.create(
         model="gemini-3.1-flash-lite",
        input=message,
        stream=True
    )
    for event in response:
        if event.event_type == "step.delta":
            if event.delta.type == "text":
                yield event.delta.text