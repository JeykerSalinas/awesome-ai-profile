"""Confirmed email workflow, independent of the storage implementation."""
import json
from hashlib import sha256

from fastapi import HTTPException

from schemas.contact import ContactReceipt, ContactSubmission
from services.contact_store import ContactStore
from services.resend_transport import DeliveryError


class EmailContactService:
    def __init__(self, store: ContactStore, transport):
        self.store, self.transport = store, transport

    def create_session(self):
        return self.store.create_session()

    def status(self, token):
        return self.store.status(token)

    def submit(self, token: str, submission: ContactSubmission):
        if submission.delivery_mode != "resend":
            raise HTTPException(409, "contact_mode_changed")
        payload = self.transport.payload(submission)
        digest = sha256(json.dumps({"request": submission.model_dump(), "payload": payload},
                                    sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        reservation = self.store.reserve(token, digest, submission.request_id)
        if reservation.receipt is not None:
            return reservation.receipt
        # Reserve before HTTP; the store's lock is not held across the network.
        # This key is stable for retries, but lost sessions are never recreated.
        try:
            provider_id = self.transport.send(payload, "portfolio-contact/" + reservation.key)
        except DeliveryError:
            raise HTTPException(503, "contact_delivery_pending") from None
        self.store.accept(reservation.key, provider_id)
        return ContactReceipt(request_id=submission.request_id, status="accepted", delivered=None)
