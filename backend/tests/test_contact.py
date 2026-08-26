import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from routes.contact import router
from schemas.contact import AgentContactContext, ContactSubmission
from schemas.chat import ChatStreamRequest
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
        with patch("routes.contact.contact_service", self.service), \
             patch("routes.contact.public_delivery_config", return_value={"mode":"simulation", "available":True}), TestClient(app) as client:
            self.assertEqual(client.get("/contact/profile").status_code, 404)
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


def chat_message(message_id, role, text="", marker=None, data=None):
    parts = [{"type": "text", "text": text}] if text else []
    if marker:
        parts.append({"type": marker, "data": data or {"mode": "demo"}})
    return {"id": message_id, "role": role, "parts": parts}


def choice_message(choice="details", offer_id="offer"):
    return chat_message("choice", "user", "I choose contact", "data-contact-choice",
                        {"choice": choice, "offer_message_id": offer_id})


class ContactRoutingTests(unittest.TestCase):
    def setUp(self):
        self.greeting = chat_message("user", "user", "Hello")
        self.offer = chat_message("offer", "assistant", "Want to get in touch?", "data-contact-offer")

    def test_greeting_or_keywords_never_imply_a_choice(self):
        for text in ["Hello", "Contact interview hiring", "I want to send an email"]:
            request = ChatStreamRequest(messages=[chat_message("u", "user", text)])
            self.assertEqual(request.contact_context(), AgentContactContext())

    def test_explicit_choices_are_routed_without_sending_ui_metadata_to_the_model(self):
        for choice in ["details", "compose"]:
            request = ChatStreamRequest(messages=[self.greeting, self.offer, choice_message(choice)])
            self.assertEqual(request.contact_context(), AgentContactContext(offered=True, choice=choice))
            self.assertEqual(request.to_agent_messages()[-1], {"role": "user", "content": "I choose contact"})
            self.assertNotIn("data-contact", json.dumps(request.to_agent_messages()))

    def test_next_ordinary_turn_does_not_reuse_previous_choice_or_repeat_offer(self):
        request = ChatStreamRequest(messages=[self.greeting, self.offer, choice_message("compose"),
            chat_message("form", "assistant", "Write here", "data-contact-form"),
            chat_message("next", "user", "What about his skills?")])
        self.assertEqual(request.contact_context(), AgentContactContext(offered=True))

    def test_choice_must_reference_an_earlier_assistant_offer(self):
        bad_histories = [
            [self.greeting, choice_message()],
            [self.greeting, choice_message(), self.offer],
            [self.greeting, self.offer, choice_message(offer_id="unknown")],
            [chat_message("offer", "user", "hello", "data-contact-offer"), choice_message()],
            [chat_message("offer", "assistant", "hello"), choice_message()],
            [self.greeting, self.offer, choice_message("send")],
        ]
        for messages in bad_histories:
            with self.subTest(messages=messages), self.assertRaises(ValidationError):
                ChatStreamRequest(messages=messages)

    def test_only_one_choice_per_user_message(self):
        choice = choice_message()
        choice["parts"].append(choice_message("compose")["parts"][1])
        with self.assertRaises(ValidationError):
            ChatStreamRequest(messages=[self.greeting, self.offer, choice])

    def test_tools_are_scoped_to_the_current_human_choice(self):
        from agents.agent import contact_tools
        cases = [(AgentContactContext(), ["offer_contact"]),
                 (AgentContactContext(offered=True), []),
                 (AgentContactContext(offered=True, choice="details"), ["get_contact_details"]),
                 (AgentContactContext(offered=True, choice="compose"), ["open_contact_form"])]
        for context, expected in cases:
            self.assertEqual([tool.name for tool in contact_tools(context)], expected)

    def test_public_details_are_returned_to_the_agent_by_a_read_only_tool(self):
        from agents.tools import get_contact_details
        details = json.loads(get_contact_details.invoke({}))
        self.assertEqual(details["phone"], "+34 624 179 342")
        self.assertEqual(details["email"], "jeyker.salinas13@gmail.com")
        self.assertEqual(details["github"], "https://github.com/JeykerSalinas")
        self.assertEqual(details["linkedin"], "https://www.linkedin.com/in/jeyker-salinas-608486158/")

    def test_prompt_requires_interest_and_human_selection_not_turn_count(self):
        from services.prompt_service import build_professional_system_prompt
        for locale in ["en", "es"]:
            prompt = build_professional_system_prompt(locale)
            self.assertIn("NOT sufficient interest", prompt)
            self.assertIn("No turn-count rule", prompt)
            self.assertIn("WAIT for their choice", prompt)
        for choice, tool in [("details", "get_contact_details"), ("compose", "open_contact_form")]:
            prompt = build_professional_system_prompt("es", AgentContactContext(offered=True, choice=choice))
            self.assertIn(f"Call {tool} now", prompt)
            if choice == "details":
                self.assertIn("GitHub and LinkedIn", prompt)


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

    async def test_contact_sse_embeds_offer_and_form_in_order_and_not_as_sources(self):
        from services.ai_sdk_stream import stream_ui_messages
        async def rest():
            yield {"type": "contact_offer"}
            yield {"type": "message_delta", "text": "Write here."}
            yield {"type": "contact_form"}
            yield {"type": "message_delta", "text": "Simulation only."}
        chunks = [chunk async for chunk in stream_ui_messages({"type": "message_delta", "text": "Want to contact him?"}, rest())]
        events = [json.loads(chunk[6:]) for chunk in chunks[:-1]]
        types = [item["type"] for item in events]
        self.assertEqual(types.count("text-start"), 3)
        self.assertEqual(types.count("text-end"), 3)
        self.assertEqual(types.count("data-contact-offer"), 1)
        self.assertEqual(types.count("data-contact-form"), 1)
        content = [item["type"] for item in events if item["type"] in {"text-delta", "data-contact-offer", "data-contact-form"}]
        self.assertEqual(content, ["text-delta", "data-contact-offer", "text-delta", "data-contact-form", "text-delta"])
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

    async def test_form_tool_is_deduplicated_and_failed_results_never_open_it(self):
        from agents.activity import observe_agent_stream
        from agents.tools import open_contact_form
        from langchain_core.messages import ToolMessage
        from test_agent_activity import EventAgent, event
        for output, expected in [(open_contact_form.invoke({}), 1),
                                 (ToolMessage(content='{"contact_form":true}', status="error", tool_call_id="bad"), 0),
                                 ('{"contact_form":false}', 0), ('not json', 0)]:
            events = []
            for run in ["one", "two"]:
                events += [event("on_tool_start", run, "open_contact_form"),
                           event("on_tool_end", run, "open_contact_form", output=output)]
            result = [item async for item in observe_agent_stream(EventAgent(events), [])]
            self.assertEqual(sum(item["type"] == "contact_form" for item in result), expected)
            self.assertFalse(any(item["type"] == "contact_offer" for item in result))

    async def test_real_agent_details_and_compose_branches_remain_separate(self):
        from agents.agent import contact_tools
        from agents.activity import observe_agent_stream
        from langchain.agents import create_agent
        from langchain_core.messages import AIMessage
        from test_agent_activity import ToolCapableFakeModel
        for choice, tool_name, answer in [
            ("details", "get_contact_details", "Email: [Jeyker](mailto:jeyker.salinas13@gmail.com)"),
            ("compose", "open_contact_form", "Edit the form and confirm the simulation."),
        ]:
            request = ChatStreamRequest(messages=[
                chat_message("offer", "assistant", "Contact him?", "data-contact-offer"), choice_message(choice)])
            model = ToolCapableFakeModel(responses=[
                AIMessage(content="", tool_calls=[{"name": tool_name, "args": {}, "id": "selected", "type": "tool_call"}]),
                AIMessage(content=answer),
            ])
            agent = create_agent(model=model, tools=contact_tools(request.contact_context()))
            result = [item async for item in observe_agent_stream(agent, request.to_agent_messages())]
            self.assertEqual("".join(item["text"] for item in result if item["type"] == "message_delta"), answer)
            self.assertEqual(sum(item["type"] == "contact_form" for item in result), int(choice == "compose"))
            self.assertFalse(any(item["type"] in {"contact_offer", "source"} for item in result))
            # Public details are ordinary model text, never a prebuilt UI data part.
            self.assertFalse(any("email" in json.dumps(item) for item in result if item["type"] != "message_delta"))


if __name__ == "__main__":
    unittest.main()
