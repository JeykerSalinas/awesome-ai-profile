from typing import Literal, TypeAlias
from pydantic import BaseModel


class MessageDeltaData(BaseModel):
    text: str


class MessageDeltaEvent(BaseModel):
    event: Literal["message_delta"]
    data: MessageDeltaData


class ImageData(BaseModel):
    src: str
    alt: str


class ImageEvent(BaseModel):
    event: Literal["image"]
    data: ImageData


class DoneEvent(BaseModel):
    event: Literal["done"]
    data: dict = {}


class ErrorData(BaseModel):
    message: str


class ErrorEvent(BaseModel):
    event: Literal["error"]
    data: ErrorData


StreamEvent: TypeAlias = MessageDeltaEvent | ImageEvent | DoneEvent | ErrorEvent
