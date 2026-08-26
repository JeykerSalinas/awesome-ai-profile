"""The contact form is explicit user input, never a model-authored approval."""
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator


class ContactSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    request_id: str = Field(pattern=r"^[a-zA-Z0-9-]{16,64}$")
    sender_name: str = Field(min_length=1, max_length=100)
    reply_email: str = Field(default="", max_length=254)
    subject: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=4000)
    confirmed: StrictBool

    @field_validator("confirmed")
    @classmethod
    def require_confirmation(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Explicit confirmation is required")
        return value

    @field_validator("sender_name", "subject", "reply_email")
    @classmethod
    def single_line(cls, value: str) -> str:
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("Single-line values are required")
        return value

    @field_validator("reply_email")
    @classmethod
    def email_if_present(cls, value: str) -> str:
        if value and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Invalid reply email")
        return value


class ContactReceipt(BaseModel):
    request_id: str
    status: Literal["simulated"] = "simulated"
    delivered: Literal[False] = False


class ContactSessionStatus(BaseModel):
    used: bool
    receipt: ContactReceipt | None = None


class ContactChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    choice: Literal["details", "compose"]
    offer_message_id: str = Field(min_length=1, max_length=200)


class AgentContactContext(BaseModel):
    offered: bool = False
    choice: Literal["details", "compose"] | None = None
