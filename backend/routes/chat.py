from fastapi import APIRouter

from schemas.chat import ChatRequest, ChatResponse
from services.llm_service import generate_response


router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    response = await generate_response(request.message)

    return ChatResponse(
        message=response
    )