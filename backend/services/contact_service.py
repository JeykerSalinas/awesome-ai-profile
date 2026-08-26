"""Bounded, process-local demo sessions. No mail provider, chat/PDF storage or MCP."""
from dataclasses import dataclass
from hashlib import sha256
from secrets import token_urlsafe
from threading import Lock
from time import monotonic

from fastapi import HTTPException

from schemas.contact import ContactReceipt, ContactSessionStatus, ContactSubmission


@dataclass
class Session:
    expires_at: float
    receipt: ContactReceipt | None = None
    payload_hash: str | None = None


class ContactService:
    def __init__(self, ttl_seconds: int = 86400, max_sessions: int = 10000):
        self.ttl_seconds = ttl_seconds
        self.max_sessions = max_sessions
        self.sessions: dict[str, Session] = {}
        self.lock = Lock()

    def create_session(self) -> str:
        with self.lock:
            now = monotonic()
            self.sessions = {key: value for key, value in self.sessions.items() if value.expires_at > now}
            if len(self.sessions) >= self.max_sessions:
                raise HTTPException(503, "contact_capacity")
            token = token_urlsafe(32)
            self.sessions[token] = Session(now + self.ttl_seconds)
            return token

    def _session(self, token: str) -> Session:
        session = self.sessions.get(token)
        if session is None or session.expires_at <= monotonic():
            self.sessions.pop(token, None)
            raise HTTPException(401, "contact_session_expired")
        return session

    def status(self, token: str) -> ContactSessionStatus:
        with self.lock:
            session = self._session(token)
            return ContactSessionStatus(used=session.receipt is not None, receipt=session.receipt)

    def submit(self, token: str, submission: ContactSubmission) -> ContactReceipt:
        if submission.delivery_mode != "simulation":
            raise HTTPException(409, "contact_mode_changed")
        digest = sha256(submission.model_dump_json().encode()).hexdigest()
        with self.lock:
            session = self._session(token)
            if session.receipt is not None:
                if session.payload_hash == digest:
                    return session.receipt  # Safe retry after a lost response.
                raise HTTPException(409, "contact_session_used")
            # Deliberately no provider call. A future transport must enforce this gate too.
            receipt = ContactReceipt(request_id=submission.request_id)
            session.receipt = receipt
            session.payload_hash = digest
            return receipt


contact_service = ContactService()
