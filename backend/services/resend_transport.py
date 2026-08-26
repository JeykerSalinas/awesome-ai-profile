"""Narrow HTTP adapter. Never log payloads, credentials or provider error bodies."""
import json
import re
from email.utils import parseaddr
from http.client import HTTPException as HTTPClientError
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from schemas.contact import ContactSubmission
from services.public_contact import public_contact_details


class DeliveryError(Exception):
    """Delivery was not acknowledged; never assume the email was not accepted."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Do not forward the authorization header to another host.


def valid_sender(value: str) -> bool:
    if not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        return False
    _, address = parseaddr(value)
    return bool(re.fullmatch(r"[^\s@<>,]+@[^\s@<>,]+\.[^\s@<>,]+", address))


class ResendTransport:
    def __init__(self, api_key: str, sender: str, opener=None):
        if not api_key or not valid_sender(sender):
            raise ValueError("Invalid email configuration")
        self._api_key = api_key
        self.sender = sender
        self.opener = opener or build_opener(NoRedirects())

    def payload(self, submission: ContactSubmission) -> dict:
        # Only the owner is a recipient. The visitor is not the From identity.
        payload = {
            "from": self.sender,
            "to": [public_contact_details()["email"]],
            "subject": submission.subject,
            "text": f"Portfolio contact — visitor identity is not verified.\nName: {submission.sender_name}\nReply email: {submission.reply_email or '(not provided)'}\n\n{submission.message}",
        }
        if submission.reply_email:
            payload["reply_to"] = [submission.reply_email]
        return payload

    def send(self, payload: dict, idempotency_key: str) -> str:
        request = Request("https://api.resend.com/emails", method="POST",
            data=json.dumps(payload, ensure_ascii=False).encode(), headers={
                "Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json",
                "Idempotency-Key": idempotency_key, "User-Agent": "awesome-ai-profile/1.0",
            })
        try:
            with self.opener.open(request, timeout=10) as response:
                if response.status != 200:
                    raise DeliveryError("contact_delivery_pending")
                result = json.loads(response.read(16384))
                email_id = result.get("id") if isinstance(result, dict) else None
                if not isinstance(email_id, str) or not email_id or len(email_id) > 200:
                    raise DeliveryError("contact_delivery_pending")
                return email_id
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, HTTPClientError):
            raise DeliveryError("contact_delivery_pending") from None
