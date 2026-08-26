"""Persistent reservations, shared quotas and receipts. No form contents stored."""
import json
from hashlib import sha256
from secrets import token_urlsafe
from time import time

from fastapi import HTTPException
from sqlalchemy import Column, Float, Integer, MetaData, String, Table, delete, insert, select, update

from schemas.contact import ContactReceipt, ContactSessionStatus, ContactSubmission
from services.resend_transport import DeliveryError

metadata = MetaData()
sessions = Table("contact_email_sessions", metadata,
    Column("token_hash", String(64), primary_key=True), Column("expires_at", Float, nullable=False),
    Column("payload_hash", String(64)), Column("request_id", String(64)),
    Column("lease_until", Float, nullable=False, default=0), Column("provider_id", String(200)))
gate = Table("contact_email_gate", metadata,
    Column("id", Integer, primary_key=True), Column("hour", Integer, nullable=False),
    Column("sessions", Integer, nullable=False), Column("day", Integer, nullable=False),
    Column("sends", Integer, nullable=False))


def initialize_contact_schema(engine):
    """Run explicitly once during setup, not while handling public HTTP traffic."""
    metadata.create_all(engine)
    with engine.begin() as connection:
        if connection.execute(select(gate.c.id).where(gate.c.id == 1)).first() is None:
            connection.execute(insert(gate).values(id=1, hour=0, sessions=0, day=0, sends=0))


class PersistentContactService:
    # A 23-hour session cannot retry beyond Resend's 24-hour idempotency window.
    ttl_seconds = 23 * 3600
    lease_seconds = 30

    def __init__(self, engine, transport, daily_limit=20, sessions_per_hour=60, clock=time):
        self.engine, self.transport, self.clock = engine, transport, clock
        self.daily_limit, self.sessions_per_hour = daily_limit, sessions_per_hour

    def _gate(self, connection, now):
        # PostgreSQL row lock; also serializes writes on SQLite in isolated tests.
        result = connection.execute(update(gate).where(gate.c.id == 1).values(id=1))
        if result.rowcount != 1:
            raise HTTPException(503, "contact_unavailable")
        row = connection.execute(select(gate).where(gate.c.id == 1)).mappings().one()
        counters = dict(row)
        if counters["hour"] != int(now // 3600):
            counters.update(hour=int(now // 3600), sessions=0)
        if counters["day"] != int(now // 86400):
            counters.update(day=int(now // 86400), sends=0)
        return counters

    def create_session(self):
        now, token = self.clock(), token_urlsafe(32)
        with self.engine.begin() as connection:
            counters = self._gate(connection, now)
            if counters["sessions"] >= self.sessions_per_hour:
                raise HTTPException(429, "contact_rate_limited")
            counters["sessions"] += 1
            connection.execute(update(gate).where(gate.c.id == 1).values(**counters))
            connection.execute(delete(sessions).where(sessions.c.expires_at <= now))
            connection.execute(insert(sessions).values(token_hash=sha256(token.encode()).hexdigest(),
                expires_at=now + self.ttl_seconds, lease_until=0))
        return token

    def _session(self, connection, token, now):
        row = connection.execute(select(sessions).where(sessions.c.token_hash == sha256(token.encode()).hexdigest())).mappings().first()
        if row is None or row["expires_at"] <= now:
            raise HTTPException(401, "contact_session_expired")
        return row

    @staticmethod
    def _receipt(row):
        return ContactReceipt(request_id=row["request_id"], status="accepted", delivered=None)

    def status(self, token):
        with self.engine.connect() as connection:
            row = self._session(connection, token, self.clock())
            accepted = row["provider_id"] is not None
            return ContactSessionStatus(used=accepted, receipt=self._receipt(row) if accepted else None,
                                        pending=bool(row["payload_hash"]) and not accepted)

    def submit(self, token: str, submission: ContactSubmission):
        if submission.delivery_mode != "resend":
            raise HTTPException(409, "contact_mode_changed")
        payload = self.transport.payload(submission)
        # Includes sender/recipient/config and exact content. Config changes cannot
        # accidentally turn an old reservation into a different Resend request.
        digest = sha256(json.dumps({"request": submission.model_dump(), "payload": payload},
                                    sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        now = self.clock()
        with self.engine.begin() as connection:
            counters = self._gate(connection, now)
            row = self._session(connection, token, now)
            if row["payload_hash"] and row["payload_hash"] != digest:
                raise HTTPException(409, "contact_payload_locked")
            if row["provider_id"]:
                return self._receipt(row)
            if row["lease_until"] > now:
                raise HTTPException(429, "contact_delivery_pending")
            if row["payload_hash"] is None:
                if counters["sends"] >= self.daily_limit:
                    raise HTTPException(429, "contact_rate_limited")
                counters["sends"] += 1  # Reserve budget even if the response is lost.
                connection.execute(update(gate).where(gate.c.id == 1).values(**counters))
            token_hash = row["token_hash"]
            connection.execute(update(sessions).where(sessions.c.token_hash == token_hash).values(
                payload_hash=digest, request_id=submission.request_id, lease_until=now + self.lease_seconds))
        # Reservation is durable BEFORE touching the network. Never hold a DB lock
        # across HTTP. A crash or timeout leaves the same request safely retryable.
        try:
            provider_id = self.transport.send(payload, "portfolio-contact/" + token_hash)
        except DeliveryError:
            raise HTTPException(503, "contact_delivery_pending") from None
        with self.engine.begin() as connection:
            connection.execute(update(sessions).where(sessions.c.token_hash == token_hash).values(provider_id=provider_id))
        return ContactReceipt(request_id=submission.request_id, status="accepted", delivered=None)
