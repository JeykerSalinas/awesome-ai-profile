from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from schemas.contact import AgentContactContext, ContactChoice


class ChatRequest(BaseModel):
    message: str
    locale: Literal["en", "es"] = "en"


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
    locale: Literal["en", "es"] = "en"
    messages: list[UIChatMessage] = Field(default_factory=list)
    message: str | None = None
    documents: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_messages(self) -> "ChatStreamRequest":
        if not self.to_agent_messages():
            raise ValueError("A non-empty message is required.")
        self.contact_context()
        return self

    def contact_context(self) -> AgentContactContext:
        """UI choice belongs to an earlier assistant offer and only authorizes this turn.

        This is conversation routing, not authentication or approval to send mail.
        """
        offers: set[str] = set()
        latest_choice = None
        for message in self.messages:
            if message.role == "assistant" and any(part.type == "data-contact-offer" for part in message.parts):
                offers.add(message.id)
            if message.role != "user":
                continue
            latest_choice = None  # A new ordinary user turn must not inherit consent.
            choices = [part for part in message.parts if part.type == "data-contact-choice"]
            if len(choices) > 1:
                raise ValueError("Only one contact choice is allowed per message")
            if choices:
                selection = ContactChoice.model_validate(getattr(choices[0], "data", None))
                if selection.offer_message_id not in offers:
                    raise ValueError("Contact choice must refer to an earlier assistant offer")
                latest_choice = selection.choice
        return AgentContactContext(offered=bool(offers), choice=latest_choice)

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
