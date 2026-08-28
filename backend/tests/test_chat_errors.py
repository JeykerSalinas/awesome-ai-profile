import json
import unittest
from unittest.mock import patch

from observability import JsonFormatter, redact
from services.chat_error_service import ERROR_PREFIX, classify_chat_error


class ChatErrorClassificationTests(unittest.TestCase):
    def test_classifies_depleted_provider_credit(self) -> None:
        error = classify_chat_error(
            RuntimeError("Gemini rejected the request: prepayment credits are depleted")
        )

        self.assertEqual(error.code, "billing_unavailable")
        self.assertEqual(error.status_code, 503)
        self.assertFalse(error.retryable)

        payload = json.loads(
            error.serialize("es", "1234567890abcdef").removeprefix(ERROR_PREFIX)
        )
        self.assertEqual(payload["reference"], "1234567890ab")
        self.assertIn("crédito", payload["message"])

    def test_classifies_invalid_api_key_without_exposing_provider_text(self) -> None:
        error = classify_chat_error(RuntimeError("API key not valid. Please pass a valid API key."))
        payload = error.serialize("en", "request-1")

        self.assertEqual(error.code, "provider_authentication_failed")
        self.assertNotIn("valid API key", payload)

    def test_classifies_quota_as_retryable(self) -> None:
        error = classify_chat_error(RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded"))

        self.assertEqual(error.code, "provider_quota_exceeded")
        self.assertTrue(error.retryable)


class ChatErrorEndpointTests(unittest.TestCase):
    def test_pre_stream_failure_returns_correlated_safe_feedback(self) -> None:
        from fastapi.testclient import TestClient
        from main import app

        async def failing_stream(*_args, **_kwargs):
            raise RuntimeError("prepayment credits are depleted: private provider data")
            yield  # Make this an async generator.

        with patch("routes.chat.generate_response_stream", failing_stream):
            response = TestClient(app).post(
                "/chat/stream",
                json={"message": "Who is Jeyker?", "locale": "es"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertTrue(response.text.startswith(ERROR_PREFIX))
        payload = json.loads(response.text.removeprefix(ERROR_PREFIX))
        self.assertEqual(payload["code"], "billing_unavailable")
        self.assertFalse(payload["retryable"])
        self.assertTrue(response.headers["x-request-id"].startswith(payload["reference"]))
        self.assertNotIn("private provider data", response.text)


class LogRedactionTests(unittest.TestCase):
    def test_redacts_google_keys_and_named_secrets(self) -> None:
        raw = "api_key=top-secret AIza123456789012345678901234567890"
        cleaned = redact(raw)

        self.assertNotIn("top-secret", cleaned)
        self.assertNotIn("AIza123", cleaned)

    def test_formatter_emits_json(self) -> None:
        import logging

        record = logging.LogRecord("test", logging.ERROR, "", 0, "failed", (), None)
        record.request_id = "abc"
        payload = json.loads(JsonFormatter().format(record))

        self.assertEqual(payload["message"], "failed")
        self.assertEqual(payload["request_id"], "abc")


if __name__ == "__main__":
    unittest.main()
