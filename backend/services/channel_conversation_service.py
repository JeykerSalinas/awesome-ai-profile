from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from time import monotonic

from services.agents_service import generate_response_for_messages
from services.prompt_service import SupportedLocale


@dataclass
class Conversation:
    messages: list[dict[str, str]] = field(default_factory=list)
    touched_at: float = field(default_factory=monotonic)


class ChannelConversationService:
    """Small in-memory conversation store for the channel proof of concept.

    Production deployments should replace this with Redis so replicas share state
    and conversations survive process restarts.
    """

    def __init__(self, *, ttl_seconds: int = 1800, max_messages: int = 12) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_messages = max_messages
        self._conversations: dict[str, Conversation] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _remove_expired(self) -> None:
        cutoff = monotonic() - self.ttl_seconds
        expired = [
            key
            for key, conversation in self._conversations.items()
            if conversation.touched_at < cutoff
        ]
        for key in expired:
            self._conversations.pop(key, None)
            self._locks.pop(key, None)

    async def reply(
        self,
        channel: str,
        conversation_id: str,
        message: str,
        locale: SupportedLocale,
    ) -> str:
        self._remove_expired()
        key = f"{channel}:{conversation_id}"
        lock = self._locks.setdefault(key, asyncio.Lock())

        async with lock:
            conversation = self._conversations.setdefault(key, Conversation())
            agent_messages = [
                *conversation.messages,
                {"role": "user", "content": message},
            ][-self.max_messages :]
            response = await generate_response_for_messages(agent_messages, locale)
            conversation.messages = [
                *agent_messages,
                {"role": "assistant", "content": response},
            ][-self.max_messages :]
            conversation.touched_at = monotonic()
            return response


channel_conversations = ChannelConversationService()
