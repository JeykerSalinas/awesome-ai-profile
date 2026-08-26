import io
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError

from routes.contact import router
from services.contact_delivery import email_configured
from services.contact_store import PersistentContactService, initialize_contact_schema, sessions
from services.resend_transport import DeliveryError, ResendTransport, NoRedirects
from settings import Settings
from test_contact import submission


class ResendTransportTests(unittest.TestCase):
    def test_fixed_recipient_plain_text_reply_to_and_idempotency(self):
        response = io.BytesIO(b'{"id":"provider-id"}')
        response.status = 200
        opener = Mock()
        opener.open.return_value = response
        transport = ResendTransport('private-key', 'Portfolio <onboarding@resend.dev>', opener)
        form = submission(message='<script>text is not HTML</script>', delivery_mode='resend')
        payload = transport.payload(form)
        self.assertEqual(transport.send(payload, 'stable-key'), 'provider-id')
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.resend.com/emails')
        self.assertEqual(request.get_header('Idempotency-key'), 'stable-key')
        self.assertEqual(request.get_header('Authorization'), 'Bearer private-key')
        body = json.loads(request.data)
        self.assertEqual(body['to'], ['jeyker.salinas13@gmail.com'])
        self.assertEqual(body['from'], 'Portfolio <onboarding@resend.dev>')
        self.assertEqual(body['reply_to'], ['recruiter@example.com'])
        self.assertEqual(body['subject'], form.subject)
        self.assertTrue(body['text'].endswith(form.message))
        for key in ['html', 'cc', 'bcc', 'attachments', 'history']:
            self.assertNotIn(key, body)
        self.assertEqual(opener.open.call_args.kwargs['timeout'], 10)
        self.assertNotIn('reply_to', transport.payload(submission(reply_email='')))

    def test_errors_and_unknown_outcomes_are_sanitized(self):
        for error in [TimeoutError('secret'), URLError('secret')]+[
            HTTPError('https://api.resend.com/emails', code, 'secret', {}, None)
            for code in [302, 400, 401, 403, 409, 422, 429, 500]]:
            opener = Mock(); opener.open.side_effect = error
            with self.assertRaises(DeliveryError) as raised:
                ResendTransport('secret', 'onboarding@resend.dev', opener).send({}, 'key')
            self.assertNotIn('secret', str(raised.exception))
        self.assertIsNone(NoRedirects().redirect_request(None, None, 302, '', {}, 'https://other.test'))

    def test_malformed_success_never_claims_acceptance(self):
        for body in [b'{}', b'[]', b'no json', b'{"id":null}', b'{"id":""}']:
            response = io.BytesIO(body); response.status = 200
            opener = Mock(); opener.open.return_value = response
            with self.assertRaises(DeliveryError):
                ResendTransport('secret', 'onboarding@resend.dev', opener).send({}, 'key')


class FakeTransport:
    def __init__(self):
        self.adapter = ResendTransport('test-key', 'onboarding@resend.dev', Mock())
        self.calls = []
        self.fail = False
    def payload(self, form):
        return self.adapter.payload(form)
    def send(self, payload, key):
        self.calls.append((payload, key))
        if self.fail:
            raise DeliveryError('unknown')
        return 'provider-id'


class PersistentContactTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.engine = create_engine('sqlite:///' + self.directory.name + '/contact.sqlite')
        initialize_contact_schema(self.engine)
        self.transport = FakeTransport()
        self.now = 100000.
        self.service = self.make_service()
        self.token = self.service.create_session()
        self.form = submission(delivery_mode='resend')
    def tearDown(self):
        self.engine.dispose()
        self.directory.cleanup()
    def make_service(self, **kwargs):
        return PersistentContactService(self.engine, self.transport, clock=lambda: self.now, **kwargs)
    def test_receipt_survives_restart_and_same_retry_never_sends_twice(self):
        receipt = self.service.submit(self.token, self.form)
        self.assertEqual(receipt.status, 'accepted')
        self.assertIsNone(receipt.delivered)
        other = self.make_service()
        self.assertEqual(other.submit(self.token, self.form), receipt)
        self.assertTrue(other.status(self.token).used)
        self.assertEqual(len(self.transport.calls), 1)
    def test_distinct_content_or_request_id_is_rejected(self):
        self.service.submit(self.token, self.form)
        for changed in [submission(delivery_mode='resend', message='different'),
                        submission(delivery_mode='resend', request_id='different-request-id')]:
            with self.assertRaises(HTTPException) as error:
                self.service.submit(self.token, changed)
            self.assertEqual(error.exception.detail, 'contact_payload_locked')
        self.assertEqual(len(self.transport.calls), 1)
    def test_ambiguous_timeout_retry_uses_identical_key_and_payload_after_restart(self):
        self.transport.fail = True
        with self.assertRaises(HTTPException): self.service.submit(self.token, self.form)
        other = self.make_service()
        self.assertTrue(other.status(self.token).pending)
        self.assertFalse(other.status(self.token).used)
        with self.assertRaises(HTTPException) as error: other.submit(self.token, self.form)
        self.assertEqual(error.exception.status_code, 429)
        self.now += 31
        self.transport.fail = False
        other.submit(self.token, self.form)
        self.assertEqual(self.transport.calls[0], self.transport.calls[1])
    def test_config_change_cannot_change_a_reserved_email(self):
        self.transport.fail = True
        with self.assertRaises(HTTPException): self.service.submit(self.token, self.form)
        self.now += 31
        self.transport.adapter.sender = 'new@example.test'
        with self.assertRaises(HTTPException) as error: self.service.submit(self.token, self.form)
        self.assertEqual(error.exception.detail, 'contact_payload_locked')
        self.assertEqual(len(self.transport.calls), 1)
    def test_expiry_prevents_retries_outside_provider_idempotency_window(self):
        self.transport.fail = True
        with self.assertRaises(HTTPException): self.service.submit(self.token, self.form)
        self.now += 23 * 3600
        with self.assertRaises(HTTPException) as error: self.service.submit(self.token, self.form)
        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(len(self.transport.calls), 1)
    def test_concurrent_services_share_reservation(self):
        def send(_):
            try: return self.make_service().submit(self.token, self.form).status
            except HTTPException as exc: return exc.status_code
        with ThreadPoolExecutor(max_workers=8) as pool: results = list(pool.map(send, range(8)))
        self.assertIn('accepted', results)
        self.assertTrue(all(result in ['accepted', 429] for result in results))
        self.assertEqual(len(self.transport.calls), 1)
    def test_global_quota_applies_across_new_sessions_and_restarts(self):
        service = self.make_service(daily_limit=1)
        service.submit(self.token, self.form)
        other = self.make_service(daily_limit=1)
        token = other.create_session()
        with self.assertRaises(HTTPException) as error: other.submit(token, self.form)
        self.assertEqual(error.exception.detail, 'contact_rate_limited')
        self.assertEqual(len(self.transport.calls), 1)
    def test_creation_quota_and_mode_mismatch_never_send(self):
        with self.assertRaises(HTTPException): self.make_service(sessions_per_hour=1).create_session()
        with self.assertRaises(HTTPException) as error: self.service.submit(self.token, submission())
        self.assertEqual(error.exception.detail, 'contact_mode_changed')
        self.assertEqual(self.transport.calls, [])
    def test_database_retains_no_message_sender_email_or_bearer(self):
        self.service.submit(self.token, self.form)
        with self.engine.connect() as connection:
            stored = repr(connection.execute(select(sessions)).mappings().all())
        for private in [self.token, self.form.sender_name, self.form.message, self.form.reply_email]:
            self.assertNotIn(private, stored)
    def test_receipt_write_failure_keeps_the_durable_reservation_retryable(self):
        begin = self.engine.begin
        calls = 0
        def failing_begin():
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OperationalError('receipt unavailable', {}, Exception())
            return begin()
        with patch.object(self.engine, 'begin', side_effect=failing_begin):
            with self.assertRaises(OperationalError): self.service.submit(self.token, self.form)
        self.assertTrue(self.service.status(self.token).pending)
        self.now += 31
        other_engine = create_engine(str(self.engine.url))
        try:
            other = PersistentContactService(other_engine, self.transport, clock=lambda: self.now)
            self.assertEqual(other.submit(self.token, self.form).status, 'accepted')
            self.assertEqual(self.transport.calls[0], self.transport.calls[1])
        finally:
            other_engine.dispose()


class DeliveryConfigurationTests(unittest.TestCase):
    def test_real_mode_tools_and_prompt_do_not_claim_simulation_or_send(self):
        from agents.tools import offer_contact, open_contact_form
        from services.prompt_service import build_professional_system_prompt
        settings = Settings(_env_file=None, contact_delivery_mode='resend', contact_email_enabled=False)
        with patch('agents.tools.get_settings', return_value=settings), \
             patch('services.prompt_service.get_settings', return_value=settings):
            self.assertEqual(json.loads(offer_contact.invoke({}))['delivery'], 'resend')
            self.assertEqual(json.loads(open_contact_form.invoke({}))['delivery'], 'resend')
            prompt = build_professional_system_prompt('es')
            self.assertNotIn('Contact is currently a DEMO', prompt)
            self.assertIn('Provider acceptance is not confirmed inbox delivery', prompt)
            self.assertIn('Only the visitor', prompt)
    def test_configuration_is_opt_in_and_requires_shared_postgres(self):
        config = dict(_env_file=None, contact_email_enabled=True, resend_api_key='private-key',
                      contact_from_email='onboarding@resend.dev', contact_database_url='postgresql+psycopg://host/db')
        self.assertTrue(email_configured(Settings(**config)))
        for key, value in [('contact_email_enabled', False), ('resend_api_key', None),
                           ('contact_from_email', 'bad\nBcc: x@test.com'), ('contact_database_url', 'sqlite:///:memory:')]:
            self.assertFalse(email_configured(Settings(**(config | {key: value}))))
        self.assertNotIn('private-key', repr(Settings(**config)))
    def test_disabled_endpoint_cannot_fall_back_to_simulation(self):
        app = FastAPI(); app.include_router(router)
        settings = Settings(_env_file=None, contact_delivery_mode='resend', contact_email_enabled=False)
        from services.contact_delivery import real_contact_service
        real_contact_service.cache_clear()
        with patch('services.contact_delivery.get_settings', return_value=settings), TestClient(app) as client:
            self.assertEqual(client.get('/contact/config').json(), {'mode': 'resend', 'available': False})
            response = client.post('/contact/sessions')
            self.assertEqual(response.status_code, 503)
        real_contact_service.cache_clear()
    def test_database_errors_are_safe_public_errors(self):
        app = FastAPI(); app.include_router(router)
        service = Mock(); service.create_session.side_effect = OperationalError('private sql', {}, Exception('private'))
        with patch('routes.contact.public_delivery_config', return_value={'mode':'resend','available':True}), \
             patch('routes.contact.real_contact_service', return_value=service), TestClient(app) as client:
            response = client.post('/contact/sessions')
            self.assertEqual(response.status_code, 503)
            self.assertNotIn('private', response.text)
    def test_real_mode_api_requires_auth_confirmation_and_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = create_engine('sqlite:///' + directory + '/api.sqlite')
            initialize_contact_schema(engine)
            transport = FakeTransport()
            service = PersistentContactService(engine, transport)
            app = FastAPI(); app.include_router(router)
            with patch('routes.contact.public_delivery_config', return_value={'mode':'resend','available':True}), \
                 patch('routes.contact.real_contact_service', return_value=service), TestClient(app) as client:
                data = submission(delivery_mode='resend').model_dump()
                self.assertEqual(client.post('/contact/submit', json=data).status_code, 401)
                token = client.post('/contact/sessions').json()['token']
                headers = {'Authorization': 'Bearer ' + token}
                for change in [{'confirmed':False}, {'to':'other@example.com'}, {'reply_email':'a,b@example.com'}]:
                    self.assertEqual(client.post('/contact/submit', headers=headers, json=data | change).status_code, 422)
                self.assertEqual(client.post('/contact/submit', headers=headers, json=data | {'delivery_mode':'simulation'}).status_code, 409)
                self.assertEqual(transport.calls, [])
                result = client.post('/contact/submit', headers=headers, json=data)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()['status'], 'accepted')
                self.assertIsNone(result.json()['delivered'])
                self.assertTrue(client.get('/contact/session', headers=headers).json()['used'])
                client.post('/contact/submit', headers=headers, json=data)
                self.assertEqual(len(transport.calls), 1)
            engine.dispose()


class RealDeliveryStreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_form_marker_preserves_mode_without_sending(self):
        from agents.activity import observe_agent_stream
        from services.ai_sdk_stream import stream_ui_messages
        from test_agent_activity import EventAgent, event
        agent = EventAgent([event('on_tool_start', 'form', 'open_contact_form'),
            event('on_tool_end', 'form', 'open_contact_form', output='{"contact_form":true,"delivery":"resend"}')])
        events = [item async for item in observe_agent_stream(agent, [])]
        self.assertIn({'type':'contact_form', 'mode':'email'}, events)
        async def rest():
            for item in events: yield item
        chunks = [chunk async for chunk in stream_ui_messages(None, rest())]
        parts = [json.loads(chunk[6:]) for chunk in chunks[:-1]]
        self.assertEqual([item['data'] for item in parts if item['type'] == 'data-contact-form'], [{'mode':'email'}])
