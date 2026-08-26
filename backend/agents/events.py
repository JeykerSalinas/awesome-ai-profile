"""Public, provider-independent events. Never include prompts or raw tool data."""
from typing import Literal, NotRequired, TypedDict

ActivityStatus = Literal["running", "completed", "error", "interrupted"]

class AgentMessageDeltaEvent(TypedDict):
    type: Literal["message_delta"]
    text: str


class AgentImageEvent(TypedDict):
    type: Literal["image"]
    src: str
    alt: str


class AgentSourceEvent(TypedDict):
    type: Literal["source"]
    path: str


class AgentActivityData(TypedDict):
    id: str
    kind: Literal["model", "tool"]
    status: ActivityStatus
    tool_name: NotRequired[str]
    duration_ms: NotRequired[int]
    result_count: NotRequired[int]


class AgentActivityEvent(TypedDict):
    type: Literal["activity"]
    data: AgentActivityData


class AgentFeatureEvent(TypedDict):
    type: Literal["feature"]
    feature: Literal["streaming"]


class AgentContactOfferEvent(TypedDict):
    type: Literal["contact_offer"]
    mode: NotRequired[Literal["demo", "email"]]


class AgentContactFormEvent(TypedDict):
    type: Literal["contact_form"]
    mode: NotRequired[Literal["demo", "email"]]


AgentStreamEvent = AgentMessageDeltaEvent | AgentImageEvent | AgentSourceEvent | AgentActivityEvent | AgentFeatureEvent | AgentContactOfferEvent | AgentContactFormEvent
