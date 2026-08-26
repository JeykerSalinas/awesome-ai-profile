import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from routes.contact import router
from schemas.contact import ContactSubmission
from services.contact_service import ContactService


def submission(**changes):
    return ContactSubmission(**{
        "request_id": "contact-request-0001", "sender_name": " Recruiter ",
        "reply_email": "recruiter@example.com", "subject": " Interview ",
        "message": " Let's talk. ", "confirmed": True, **changes,
    })


class ContactTests(unittest.TestCase):
    def setUp(self):
        self.service = ContactService()
        self.token = self.service.create_session()

    def test_required_name_message_subject_and_explicit_confirmation(self):
        for key, value in [("sender_name", " "), ("subject", " "), ("message", " "),
                           ("confirmed", False), ("confirmed", "true"), ("confirmed", 1),
                           ("sender_name", "X" * 101), ("message", "X" * 4001),
                           ("reply_email", "bad-email"), ("subject", "Hello\nBcc: bad@example.com")]:
            with self.subTest(key=key, value=value), self.assertRaises(ValidationError):
                submission(**{key: value})
        self.assertEqual(submission(reply_email="").reply_email, "")
        self.assertEqual(submission().sender_name, "Recruiter")

    def test_client_cannot_choose_recipient_or_attach_chat(self):
        for key in ["to", "cc", "bcc", "attachments", "history"]:
            with self.subTest(key=key), self.assertRaises(ValidationError):
                submission(**{key: "anything"})

    def test_first_submission_is_simulated_and_retry_is_idempotent(self):
        self.assertFalse(self.service.status(self.token).used)
        first = self.service.submit(self.token, submission())
        self.assertEqual(first.status, "simulated")
        self.assertFalse(first.delivered)
        self.assertEqual(first, self.service.submit(self.token, submission()))
        self.assertTrue(self.service.status(self.token).used)
        self.assertEqual(self.service.status(self.token).receipt, first)

    def test_new_request_or_modified_payload_cannot_send_again(self):
        self.service.submit(self.token, submission())
        for changes in [{"message": "changed"}, {"request_id": "contact-request-0002"}]:
            with self.assertRaises(HTTPException) as raised:
                self.service.submit(self.token, submission(**changes))
            self.assertEqual(raised.exception.status_code, 409)

    def test_concurrent_submissions_consume_only_one_slot(self):
        def send(index):
            try:
                self.service.submit(self.token, submission(request_id=f"contact-request-{index:04}"))
                return 200
            except HTTPException as exc:
                return exc.status_code
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(send, range(8)))
        self.assertEqual(results.count(200), 1)
        self.assertEqual(results.count(409), 7)

    def test_unknown_expired_and_other_sessions(self):
        with self.assertRaises(HTTPException):
            self.service.submit("invented", submission())
        other = self.service.create_session()
        self.service.submit(self.token, submission())
        self.assertFalse(self.service.status(other).used)
        self.service.sessions[other].expires_at = 0
        with self.assertRaises(HTTPException) as raised:
            self.service.submit(other, submission())
        self.assertEqual(raised.exception.status_code, 401)

    def test_capacity_is_bounded_and_expired_slots_are_reclaimed(self):
        service = ContactService(max_sessions=1)
        token = service.create_session()
        with self.assertRaises(HTTPException):
            service.create_session()
        service.sessions[token].expires_at = 0
        self.assertNotEqual(token, service.create_session())

    def test_server_does_not_retain_message_or_sender(self):
        self.service.submit(self.token, submission())
        stored = repr(self.service.sessions)
        for private in ["Recruiter", "recruiter@example.com", "Let's talk"]:
            self.assertNotIn(private, stored)

    def test_api_flow_validation_and_reload_status(self):
        app = FastAPI()
        app.include_router(router)
        with patch("routes.contact.contact_service", self.service), TestClient(app) as client:
            profile = client.get("/contact/profile")
            self.assertEqual(profile.status_code, 200)
            self.assertEqual(profile.json()["github"], "https://github.com/JeykerSalinas")
            self.assertEqual(client.post("/contact/submit", json=submission().model_dump()).status_code, 401)
            session = client.post("/contact/sessions")
            self.assertEqual(session.headers["Cache-Control"], "no-store")
            headers = {"Authorization": f"Bearer {session.json()['token']}"}
            invalid = submission().model_dump() | {"sender_name": ""}
            self.assertEqual(client.post("/contact/submit", headers=headers, json=invalid).status_code, 422)
            self.assertFalse(client.get("/contact/session", headers=headers).json()["used"])
            response = client.post("/contact/submit", headers=headers, json=submission().model_dump())
            self.assertEqual(response.json()["status"], "simulated")
            self.assertFalse(response.json()["delivered"])
            status = client.get("/contact/session", headers=headers)
            self.assertTrue(status.json()["used"])
            self.assertEqual(client.post("/contact/submit", headers=headers, json=submission(message="Again").model_dump()).status_code, 409)


class ContactStreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_contact_tool_emits_one_typed_card_not_an_email(self):
        from agents.activity import observe_agent_stream
        from test_agent_activity import EventAgent, event
        from agents.tools import offer_contact
        output = offer_contact.invoke({})
        events = []
        for run in ["one", "two"]:
            events += [event("on_tool_start", run, "offer_contact"),
                       event("on_tool_end", run, "offer_contact", output=output)]
        result = [item async for item in observe_agent_stream(EventAgent(events), [])]
        self.assertEqual(sum(item["type"] == "contact_offer" for item in result), 1)
        self.assertEqual(sum(item["type"] == "activity" for item in result), 4)
        self.assertNotIn("email", json.dumps(result))

    async def test_contact_sse_does_not_break_text_and_is_not_a_source(self):
        from services.ai_sdk_stream import stream_ui_messages
        async def rest():
            yield {"type": "contact_offer"}
            yield {"type": "message_delta", "text": "there**"}
        chunks = [chunk async for chunk in stream_ui_messages({"type": "message_delta", "text": "**Hi "}, rest())]
        events = [json.loads(chunk[6:]) for chunk in chunks[:-1]]
        types = [item["type"] for item in events]
        self.assertEqual(types.count("text-start"), 1)
        self.assertEqual(types.count("data-contact-offer"), 1)
        self.assertNotIn("data-source", types)

    async def test_real_agent_can_offer_contact_but_has_no_send_tool(self):
        from langchain.agents import create_agent
        from langchain_core.messages import AIMessage
        from agents.activity import observe_agent_stream
        from agents.tools import offer_contact
        from test_agent_activity import ToolCapableFakeModel
        model = ToolCapableFakeModel(responses=[
            AIMessage(content="", tool_calls=[{"name": "offer_contact", "args": {}, "id": "contact-call", "type": "tool_call"}]),
            AIMessage(content="Choose contact details or write a demo email."),
        ])
        agent = create_agent(model=model, tools=[offer_contact])
        events = [item async for item in observe_agent_stream(agent, [{"role": "user", "content": "I want to contact Jeyker"}])]
        self.assertIn({"type": "contact_offer"}, events)
        self.assertEqual([item["data"]["status"] for item in events if item["type"] == "activity" and item["data"]["kind"] == "tool"], ["running", "completed"])

    async def test_failed_contact_tool_does_not_emit_an_offer(self):
        from agents.activity import observe_agent_stream
        from langchain_core.messages import ToolMessage
        from test_agent_activity import EventAgent, event
        result = [item async for item in observe_agent_stream(EventAgent([
            event("on_tool_start", "one", "offer_contact"),
            event("on_tool_end", "one", "offer_contact", output=ToolMessage(content='{"contact_offer":true}', status="error", tool_call_id="one")),
        ]), [])]
        self.assertFalse(any(item["type"] == "contact_offer" for item in result))


if __name__ == "__main__":
    unittest.main()
