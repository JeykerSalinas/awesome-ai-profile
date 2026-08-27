from typing import Literal

from pydantic import BaseModel, Field

from services.prompt_service import SupportedLocale


class LiveHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class LiveSessionStart(BaseModel):
    type: Literal["start"]
    locale: SupportedLocale = "en"
    documents: list[str] = Field(default_factory=list, max_length=10)
    history: list[LiveHistoryMessage] = Field(default_factory=list, max_length=20)
