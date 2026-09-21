from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

import httpx

from schemas.channels import InboundChannelMessage
from services.channel_conversation_service import channel_conversations
from services.prompt_service import SupportedLocale
from settings import get_settings


logger = logging.getLogger(__name__)


def verify_meta_signature(body: bytes, signature: str | None, app_secret: str) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        app_secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def extract_whatsapp_messages(payload: dict[str, Any]) -> list[InboundChannelMessage]:
    messages: list[InboundChannelMessage] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                text = message.get("text", {}).get("body", "").strip()
                sender = str(message.get("from", "")).strip()
                message_id = str(message.get("id", "")).strip()
                if message.get("type") == "text" and text and sender and message_id:
                    messages.append(
                        InboundChannelMessage(
                            channel="whatsapp",
                            message_id=message_id,
                            conversation_id=sender,
                            text=text,
                        )
                    )
    return messages


async def send_whatsapp_text(recipient: str, text: str) -> None:
    settings = get_settings()
    if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
        raise RuntimeError("WhatsApp outbound credentials are not configured.")

    url = (
        f"https://graph.facebook.com/{settings.meta_graph_api_version}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}"}
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"preview_url": False, "body": text[:4096]},
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()


async def process_whatsapp_message(
    message: InboundChannelMessage,
    locale: SupportedLocale,
) -> None:
    try:
        response = await channel_conversations.reply(
            message.channel,
            message.conversation_id,
            message.text,
            locale,
        )
        await send_whatsapp_text(message.conversation_id, response)
        logger.info(
            "whatsapp_message_completed",
            extra={"provider_message_id": message.message_id},
        )
    except Exception:
        logger.exception(
            "whatsapp_message_failed",
            extra={"provider_message_id": message.message_id},
        )
