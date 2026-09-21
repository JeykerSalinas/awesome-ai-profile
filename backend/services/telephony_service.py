from __future__ import annotations

import base64
import hashlib
import hmac
import re
from urllib.parse import urlsplit
from xml.etree.ElementTree import Element, SubElement, tostring

from services.channel_conversation_service import channel_conversations
from services.prompt_service import SupportedLocale


def verify_twilio_signature(
    url: str,
    form: dict[str, str],
    signature: str | None,
    auth_token: str,
) -> bool:
    if not signature:
        return False
    signed_value = url + "".join(key + form[key] for key in sorted(form))
    digest = hmac.new(
        auth_token.encode("utf-8"), signed_value.encode("utf-8"), hashlib.sha1
    ).digest()
    expected = base64.b64encode(digest).decode("ascii")
    return hmac.compare_digest(expected, signature)


def absolute_channel_url(public_base_url: str | None, request_url: str, path: str) -> str:
    if public_base_url:
        return f"{public_base_url.rstrip('/')}{path}"
    base = request_url.split("?", 1)[0]
    return f"{base.split('/channels/', 1)[0]}{path}"


def signed_request_url(public_base_url: str | None, request_url: str) -> str:
    """Return the exact public URL Twilio used when calculating its signature."""
    if not public_base_url:
        return request_url
    parsed = urlsplit(request_url)
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{public_base_url.rstrip('/')}{parsed.path}{query}"


def build_voice_prompt(
    action_url: str,
    *,
    locale: SupportedLocale,
    message: str,
) -> str:
    language = "es-ES" if locale == "es" else "en-US"
    response = Element("Response")
    gather = SubElement(
        response,
        "Gather",
        {
            "input": "speech",
            "action": action_url,
            "method": "POST",
            "language": language,
            "speechTimeout": "auto",
            "actionOnEmptyResult": "true",
        },
    )
    say = SubElement(gather, "Say", {"language": language})
    say.text = message
    redirect = SubElement(response, "Redirect", {"method": "POST"})
    redirect.text = action_url
    return '<?xml version="1.0" encoding="UTF-8"?>' + tostring(
        response, encoding="unicode"
    )


def to_spoken_text(text: str) -> str:
    text = re.sub(r"\[([^\]]+)]\([^)]+\)", r"\1", text)
    text = re.sub(r"[`*_#>]", "", text)
    return " ".join(text.split())[:3000]


async def answer_phone_turn(
    call_sid: str,
    speech: str,
    locale: SupportedLocale,
) -> str:
    return await channel_conversations.reply("voice", call_sid, speech, locale)
