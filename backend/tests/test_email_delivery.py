import io
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from routes.contact import router
from services.contact_delivery import email_configured
from services.contact_store import MemoryContactStore
from services.contact_email_service import EmailContactService
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


class MemoryContactTests(unittest.TestCase):
    def setUp(self):
        self.transport = FakeTransport()
        self.now = 100000.
        self.store = self.make_store()
        self.service = self.make_service()
        self.token = self.service.create_session()
        self.form = submission(delivery_mode='resend')
    def make_store(self, **kwargs):
        return MemoryContactStore(clock=lambda: self.now, **kwargs)
    def make_service(self):
        return EmailContactService(self.store, self.transport)
    def test_same_store_keeps_receipt_and_same_retry_never_sends_twice(self):
        receipt = self.service.submit(self.token, self.form)
        self.assertEqual(receipt.status, 'accepted')
        self.assertIsNone(receipt.delivered)
        other = self.make_service()
        self.assertEqual(other.submit(self.token, self.form), receipt)
        self.assertTrue(other.status(self.token).used)
        self.assertEqual(len(self.transport.calls), 1)
    def test_restart_loses_state_and_never_recreates_or_resends_old_sessions(self):
        self.service.submit(self.token, self.form)
        restarted = EmailContactService(self.make_store(), self.transport)
        for action in [lambda: restarted.status(self.token), lambda: restarted.submit(self.token, self.form)]:
            with self.assertRaises(HTTPException) as error: action()
            self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(len(self.transport.calls), 1)
        self.assertEqual(restarted.store.sessions, {})
    def test_restart_with_pending_send_rejects_old_token_without_provider_call(self):
        self.transport.fail = True
        with self.assertRaises(HTTPException): self.service.submit(self.token, self.form)
        restarted = EmailContactService(self.make_store(), self.transport)
        self.now += 31
        self.transport.fail = False
        with self.assertRaises(HTTPException) as error: restarted.submit(self.token, self.form)
        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(len(self.transport.calls), 1)
    def test_distinct_content_or_request_id_is_rejected(self):
        self.service.submit(self.token, self.form)
        for changed in [submission(delivery_mode='resend', message='different'),
                        submission(delivery_mode='resend', request_id='different-request-id')]:
            with self.assertRaises(HTTPException) as error:
                self.service.submit(self.token, changed)
            self.assertEqual(error.exception.detail, 'contact_payload_locked')
        self.assertEqual(len(self.transport.calls), 1)
    def test_ambiguous_timeout_retry_uses_identical_key_and_payload_while_store_lives(self):
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
    def test_network_call_does_not_hold_the_store_lock(self):
        def send(payload, key):
            with ThreadPoolExecutor(max_workers=1) as pool:
                self.assertTrue(pool.submit(self.service.status, self.token).result(timeout=1).pending)
            return 'id'
        with patch.object(self.transport, 'send', side_effect=send):
            self.assertEqual(self.service.submit(self.token, self.form).status, 'accepted')
    def test_quota_is_per_store_and_resets_when_a_new_process_starts(self):
        store = self.make_store(daily_limit=1)
        service = EmailContactService(store, self.transport)
        service.submit(service.create_session(), self.form)
        other = EmailContactService(store, self.transport)
        with self.assertRaises(HTTPException) as error: other.submit(other.create_session(), self.form)
        self.assertEqual(error.exception.detail, 'contact_rate_limited')
        restarted = EmailContactService(self.make_store(daily_limit=1), self.transport)
        self.assertEqual(restarted.submit(restarted.create_session(), self.form).status, 'accepted')
        self.assertEqual(len(self.transport.calls), 2)
    def test_creation_quota_and_mode_mismatch_never_send(self):
        store = self.make_store(sessions_per_hour=1)
        store.create_session()
        with self.assertRaises(HTTPException): store.create_session()
        with self.assertRaises(HTTPException) as error: self.service.submit(self.token, submission())
        self.assertEqual(error.exception.detail, 'contact_mode_changed')
        self.assertEqual(self.transport.calls, [])
    def test_memory_retains_no_message_sender_email_or_bearer(self):
        self.service.submit(self.token, self.form)
        stored = repr(self.store.sessions)
        for private in [self.token, self.form.sender_name, self.form.message, self.form.reply_email]:
            self.assertNotIn(private, stored)
    def test_capacity_is_bounded_and_expired_slots_are_reclaimed(self):
        store = self.make_store(max_sessions=1)
        first = store.create_session()
        with self.assertRaises(HTTPException) as error: store.create_session()
        self.assertEqual(error.exception.detail, 'contact_capacity')
        self.now += store.ttl_seconds
        self.assertNotEqual(first, store.create_session())
        self.assertEqual(len(store.sessions), 1)
    def test_hour_and_day_windows_roll_over(self):
        store = self.make_store(daily_limit=1, sessions_per_hour=1)
        service = EmailContactService(store, self.transport)
        service.submit(service.create_session(), self.form)
        self.now += 3600
        token = service.create_session()
        with self.assertRaises(HTTPException): service.submit(token, self.form)
        self.now += 86400
        self.assertEqual(service.submit(service.create_session(), self.form).status, 'accepted')
    def test_receipt_recording_failure_can_retry_while_memory_survives(self):
        with patch.object(self.store, 'accept', side_effect=RuntimeError('receipt unavailable')):
            with self.assertRaises(RuntimeError): self.service.submit(self.token, self.form)
        self.assertTrue(self.service.status(self.token).pending)
        self.now += 31
        self.assertEqual(self.make_service().submit(self.token, self.form).status, 'accepted')
        self.assertEqual(self.transport.calls[0], self.transport.calls[1])


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
    def test_configuration_is_opt_in_without_any_database(self):
        config = dict(_env_file=None, contact_email_enabled=True, resend_api_key='private-key',
                      contact_from_email='onboarding@resend.dev', contact_database_url=None)
        self.assertTrue(email_configured(Settings(**config)))
        self.assertTrue(email_configured(Settings(**(config | {'contact_database_url':'obsolete-and-ignored'}))))
        for key, value in [('contact_email_enabled', False), ('resend_api_key', None),
                           ('contact_from_email', 'bad\nBcc: x@test.com')]:
            self.assertFalse(email_configured(Settings(**(config | {key: value}))))
        self.assertNotIn('private-key', repr(Settings(**config)))
    def test_disabled_endpoint_cannot_fall_back_to_simulation(self):
        app = FastAPI(); app.include_router(router)
        settings = Settings(_env_file=None, contact_delivery_mode='resend', contact_email_enabled=False)
        from services.contact_delivery import _build_real_contact_service
        _build_real_contact_service.cache_clear()
        with patch('services.contact_delivery.get_settings', return_value=settings), TestClient(app) as client:
            self.assertEqual(client.get('/contact/config').json(), {'mode': 'resend', 'available': False})
            response = client.post('/contact/sessions')
            self.assertEqual(response.status_code, 503)
        _build_real_contact_service.cache_clear()
    def test_first_concurrent_requests_use_one_memory_store(self):
        from services.contact_delivery import _build_real_contact_service, real_contact_service
        settings = Settings(_env_file=None, contact_email_enabled=True, resend_api_key='test-key',
                            contact_from_email='onboarding@resend.dev', contact_database_url=None)
        _build_real_contact_service.cache_clear()
        try:
            with patch('services.contact_delivery.get_settings', return_value=settings), \
                 patch('services.contact_delivery.MemoryContactStore', wraps=MemoryContactStore) as factory:
                with ThreadPoolExecutor(max_workers=8) as pool:
                    services = list(pool.map(lambda _: real_contact_service(), range(32)))
                self.assertEqual(len({id(service) for service in services}), 1)
                self.assertEqual(factory.call_count, 1)
        finally:
            _build_real_contact_service.cache_clear()
    def test_real_mode_api_requires_auth_confirmation_and_mode(self):
        transport = FakeTransport()
        service = EmailContactService(MemoryContactStore(), transport)
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
