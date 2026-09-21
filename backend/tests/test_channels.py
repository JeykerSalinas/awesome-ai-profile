import hashlib
import hmac
import json
import unittest
from base64 import b64encode
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from services.channel_conversation_service import ChannelConversationService
from services.telephony_service import (
    build_voice_prompt,
    signed_request_url,
    to_spoken_text,
    verify_twilio_signature,
)
from services.whatsapp_service import extract_whatsapp_messages, verify_meta_signature


def channel_settings(**overrides):
    defaults = {
        "whatsapp_verify_token": "verify-me",
        "whatsapp_app_secret": "meta-secret",
        "whatsapp_access_token": "access-token",
        "whatsapp_phone_number_id": "phone-id",
        "meta_graph_api_version": "v26.0",
        "twilio_auth_token": "twilio-secret",
        "channel_public_base_url": None,
        "channel_default_locale": "es",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class WhatsAppServiceTests(unittest.TestCase):
    def test_verifies_meta_hmac_signature(self) -> None:
        body = b'{"object":"whatsapp_business_account"}'
        signature = "sha256=" + hmac.new(
            b"meta-secret", body, hashlib.sha256
        ).hexdigest()
        self.assertTrue(verify_meta_signature(body, signature, "meta-secret"))
        self.assertFalse(verify_meta_signature(body + b"!", signature, "meta-secret"))

    def test_extracts_only_text_messages(self) -> None:
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [
                            {"id": "wamid.1", "from": "34600", "type": "text", "text": {"body": "¿Qué experiencia tiene?"}},
                            {"id": "wamid.2", "from": "34600", "type": "image"},
                        ]
                    }
                }]
            }]
        }
        messages = extract_whatsapp_messages(payload)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].conversation_id, "34600")
        self.assertEqual(messages[0].text, "¿Qué experiencia tiene?")


class ConversationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_preserves_short_channel_history(self) -> None:
        service = ChannelConversationService(max_messages=6)
        responses = ["Respuesta uno", "Respuesta dos"]
        with patch(
            "services.channel_conversation_service.generate_response_for_messages",
            new=AsyncMock(side_effect=responses),
        ) as generate:
            await service.reply("whatsapp", "34600", "Hola", "es")
            await service.reply("whatsapp", "34600", "¿Y su experiencia?", "es")

        second_messages = generate.await_args_list[1].args[0]
        self.assertEqual(
            second_messages,
            [
                {"role": "user", "content": "Hola"},
                {"role": "assistant", "content": "Respuesta uno"},
                {"role": "user", "content": "¿Y su experiencia?"},
            ],
        )


class TelephonyServiceTests(unittest.TestCase):
    def test_verifies_twilio_signature(self) -> None:
        url = "https://api.example.com/channels/voice/turn"
        form = {"CallSid": "CA123", "SpeechResult": "Hola"}
        signed = url + "CallSidCA123SpeechResultHola"
        signature = b64encode(
            hmac.new(b"twilio-secret", signed.encode(), hashlib.sha1).digest()
        ).decode()
        self.assertTrue(
            verify_twilio_signature(url, form, signature, "twilio-secret")
        )

    def test_builds_safe_twiml_and_plain_spoken_text(self) -> None:
        xml = build_voice_prompt(
            "https://api.example.com/channels/voice/turn?x=1&y=2",
            locale="es",
            message="Jeyker usa RAG & agentes.",
        )
        self.assertIn("&amp;", xml)
        self.assertIn("<Gather", xml)
        self.assertEqual(
            to_spoken_text("**Perfil:** [Jeyker](https://example.com) usa `RAG`."),
            "Perfil: Jeyker usa RAG.",
        )
        self.assertEqual(
            signed_request_url(
                "https://api.example.com",
                "http://container:8000/channels/voice/turn?region=eu",
            ),
            "https://api.example.com/channels/voice/turn?region=eu",
        )


class ChannelEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        from main import app

        self.client = TestClient(app)

    def test_verifies_whatsapp_subscription(self) -> None:
        with patch("routes.channels.get_settings", return_value=channel_settings()):
            response = self.client.get(
                "/channels/whatsapp/webhook",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "verify-me",
                    "hub.challenge": "challenge-123",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "challenge-123")

    def test_accepts_signed_whatsapp_message(self) -> None:
        payload = {
            "entry": [{"changes": [{"value": {"messages": [{
                "id": "wamid.1",
                "from": "34600",
                "type": "text",
                "text": {"body": "Háblame de su RAG"},
            }]}}]}]
        }
        body = json.dumps(payload, separators=(",", ":")).encode()
        signature = "sha256=" + hmac.new(
            b"meta-secret", body, hashlib.sha256
        ).hexdigest()
        with (
            patch("routes.channels.get_settings", return_value=channel_settings()),
            patch(
                "routes.channels.process_whatsapp_message", new=AsyncMock()
            ) as process,
        ):
            response = self.client.post(
                "/channels/whatsapp/webhook",
                content=body,
                headers={
                    "content-type": "application/json",
                    "x-hub-signature-256": signature,
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["messages"], 1)
        process.assert_awaited_once()

    def test_returns_conversational_twiml_for_phone_turn(self) -> None:
        form = {"CallSid": "CA123", "SpeechResult": "¿Qué experiencia tiene con IA?"}
        url = "http://testserver/channels/voice/turn"
        signed = url + "".join(key + form[key] for key in sorted(form))
        signature = b64encode(
            hmac.new(b"twilio-secret", signed.encode(), hashlib.sha1).digest()
        ).decode()
        with (
            patch("routes.channels.get_settings", return_value=channel_settings()),
            patch(
                "routes.channels.answer_phone_turn",
                new=AsyncMock(return_value="Jeyker ha construido sistemas con **RAG**."),
            ),
        ):
            response = self.client.post(
                "/channels/voice/turn",
                data=form,
                headers={"x-twilio-signature": signature},
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Jeyker ha construido sistemas con RAG.", response.text)
        self.assertIn("<Gather", response.text)


if __name__ == "__main__":
    unittest.main()
