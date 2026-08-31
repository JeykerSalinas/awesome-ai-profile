from typing import Literal

from pydantic import BaseModel


class InboundChannelMessage(BaseModel):
    channel: Literal["whatsapp"]
    message_id: str
    conversation_id: str
    text: str

