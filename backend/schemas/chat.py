from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    message: str


class UIMessagePart(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    text: str | None = None


class UIChatMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    role: Literal["system", "user", "assistant"]
    parts: list[UIMessagePart] = Field(default_factory=list)

    def to_agent_message(self) -> dict[str, str] | None:
        text = "".join(
            part.text for part in self.parts if part.type == "text" and part.text
        ).strip()

        if not text:
            return None

        return {"role": self.role, "content": text}


class ChatStreamRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    messages: list[UIChatMessage] = Field(default_factory=list)
    message: str | None = None

    @model_validator(mode="after")
    def validate_messages(self) -> "ChatStreamRequest":
        if not self.to_agent_messages():
            raise ValueError("A non-empty message is required.")

        return self

    def to_agent_messages(self) -> list[dict[str, str]]:
        if self.messages:
            return [
                agent_message
                for message in self.messages
                if (agent_message := message.to_agent_message()) is not None
            ]

        if self.message and self.message.strip():
            return [{"role": "user", "content": self.message.strip()}]

        return []
