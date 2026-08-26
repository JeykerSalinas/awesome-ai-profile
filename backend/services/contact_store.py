"""Replaceable contact storage. Current implementation is bounded, process-local RAM."""
from dataclasses import dataclass
from hashlib import sha256
from secrets import token_urlsafe
from threading import Lock
from time import time
from typing import Protocol

from fastapi import HTTPException

from schemas.contact import ContactReceipt, ContactSessionStatus


@dataclass(frozen=True)
class Reservation:
    key: str
    receipt: ContactReceipt | None = None


class ContactStore(Protocol):
    """A future DB adapter must preserve atomic reservation/quota semantics."""
    def create_session(self) -> str: ...
    def status(self, token: str) -> ContactSessionStatus: ...
    def reserve(self, token: str, digest: str, request_id: str) -> Reservation: ...
    def accept(self, key: str, provider_id: str) -> None: ...


@dataclass
class EmailSession:
    expires_at: float
    payload_hash: str | None = None
    request_id: str | None = None
    lease_until: float = 0
    provider_id: str | None = None


class MemoryContactStore:
    # Keep retries within Resend's 24-hour idempotency window.
    ttl_seconds = 23 * 3600
    lease_seconds = 30

    def __init__(self, daily_limit=20, sessions_per_hour=60, max_sessions=10000, clock=time):
        self.clock = clock
        self.daily_limit, self.sessions_per_hour = daily_limit, sessions_per_hour
        self.max_sessions = max_sessions
        self.sessions: dict[str, EmailSession] = {}
        self.lock = Lock()
        self.hour = self.day = -1
        self.created = self.sends = 0

    def _roll_counters(self, now):
        if self.hour != int(now // 3600):
            self.hour, self.created = int(now // 3600), 0
        if self.day != int(now // 86400):
            self.day, self.sends = int(now // 86400), 0

    def _session(self, key, now):
        session = self.sessions.get(key)
        if session is None or session.expires_at <= now:
            self.sessions.pop(key, None)
            # Never recreate a lost token: after a restart, an unknown send
            # outcome must not silently become a new email.
            raise HTTPException(401, "contact_session_expired")
        return session

    @staticmethod
    def _receipt(session):
        return ContactReceipt(request_id=session.request_id, status="accepted", delivered=None)

    def create_session(self) -> str:
        with self.lock:
            now = self.clock()
            self._roll_counters(now)
            self.sessions = {key: session for key, session in self.sessions.items() if session.expires_at > now}
            if len(self.sessions) >= self.max_sessions:
                raise HTTPException(503, "contact_capacity")
            if self.created >= self.sessions_per_hour:
                raise HTTPException(429, "contact_rate_limited")
            token = token_urlsafe(32)
            self.sessions[sha256(token.encode()).hexdigest()] = EmailSession(now + self.ttl_seconds)
            self.created += 1
            return token

    def status(self, token: str) -> ContactSessionStatus:
        with self.lock:
            session = self._session(sha256(token.encode()).hexdigest(), self.clock())
            accepted = session.provider_id is not None
            return ContactSessionStatus(used=accepted,
                receipt=self._receipt(session) if accepted else None,
                pending=session.payload_hash is not None and not accepted)

    def reserve(self, token: str, digest: str, request_id: str) -> Reservation:
        key = sha256(token.encode()).hexdigest()
        with self.lock:
            now = self.clock()
            self._roll_counters(now)
            session = self._session(key, now)
            if session.payload_hash and (session.payload_hash != digest or session.request_id != request_id):
                raise HTTPException(409, "contact_payload_locked")
            if session.provider_id is not None:
                return Reservation(key, self._receipt(session))
            if session.lease_until > now:
                raise HTTPException(429, "contact_delivery_pending")
            if session.payload_hash is None:
                if self.sends >= self.daily_limit:
                    raise HTTPException(429, "contact_rate_limited")
                self.sends += 1  # Keep the budget reserved even on uncertain outcomes.
            session.payload_hash, session.request_id = digest, request_id
            session.lease_until = now + self.lease_seconds
            return Reservation(key)

    def accept(self, key: str, provider_id: str) -> None:
        with self.lock:
            self._session(key, self.clock()).provider_id = provider_id
