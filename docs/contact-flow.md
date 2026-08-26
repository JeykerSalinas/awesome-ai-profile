# Agent-led contact and Resend email

## Conversational flow

The agent offers contact once, after concrete hiring/interview interest or an explicit contact request. Greetings, general questions, photos and thanks do not automatically open a form. The visitor chooses:

- **View details:** the choice returns to chat. `get_contact_details` supplies public phone, email, GitHub and LinkedIn to the model, which writes normal Markdown.
- **Write an email:** the choice returns to chat. `open_contact_form` embeds an editable form in the new assistant response.

Only the selected contact tool is exposed on that turn. Neither tool can send mail. Ordinary later turns do not reuse a previous choice or reopen the form. The latest editor shares a draft and session quota with the rest of the conversation. The draft, name and reply email stay out of LLM history.

The human enters a name, subject and message, optionally a reply email, and explicitly confirms the displayed delivery mode. This is a human-decision/confirmation flow, **not LangGraph interrupt/resume and not MCP**. Resend is called directly from the backend after the form submission gate.

## Delivery modes

| Mode | Confirmation | Result |
| --- | --- | --- |
| `simulation` (default) | Confirm simulated send | `status: simulated`, `delivered: false`. No external call. |
| `resend`, configured and enabled | Confirm and send email | `status: accepted`, `delivered: null`. Resend accepted the request; inbox delivery is unknown. |
| `resend`, disabled/missing configuration | Sending disabled | No fallback to a simulated success. |

The frontend loads `GET /contact/config` before enabling confirmation. The request includes `delivery_mode`; the backend rejects a confirmation for a different mode. The config exposes only mode and configuration availability, never credentials. Availability is not a live database/provider health check.

The recipient is fixed to the owner's authorized address in `services/public_contact.py`. The sender is server-configured, not the visitor. The optional visitor address becomes `reply_to` only. Name and reply address are explicitly identified as unverified in the plain-text email. There are no arbitrary recipients, CC/BCC, HTML, attachments, conversation history or uploaded PDFs.

## Configure Resend (no activation performed by this PR)

1. Create a Resend account. For a controlled first test without a domain, its account email must be **jeyker.salinas13@gmail.com**, our fixed recipient. Resend's `onboarding@resend.dev` sender is for testing and can only send to the account's own address. Use a verified domain before treating this as a production sender. See [testing restrictions](https://resend.com/docs/knowledge-base/403-error-resend-dev-domain).
2. Create a **sending-access** API key, restricted to your domain when applicable. Put it in backend secrets, never in chat, Git, frontend `VITE_*` variables, logs or browser storage. See [API key permissions](https://resend.com/docs/api-reference/api-keys/create-api-key).
3. Configure a shared, durable PostgreSQL database. Locally the existing Compose Postgres can be used; in Azure use a reachable persistent database, not `localhost` or a container-local file. The existing `DATABASE_URL` module is not imported or changed. Contact uses its own explicit connection setting:

```dotenv
CONTACT_DELIVERY_MODE=resend
CONTACT_EMAIL_ENABLED=false
RESEND_API_KEY=<backend-secret>
CONTACT_FROM_EMAIL=Portfolio <onboarding@resend.dev>
CONTACT_DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>:5432/<database>?sslmode=require
CONTACT_DAILY_LIMIT=20
CONTACT_SESSIONS_PER_HOUR=60
```

For local Compose, the example in `backend/.env.example` uses localhost without requiring TLS. For Azure, store the API key and database URL as Container Apps secrets and bind the corresponding environment variables to those secrets. Use TLS and the provider's database networking requirements.

4. From the backend environment, initialize **only the two new contact tables**:

```sh
python -m scripts.init_contact_store
```

This sends no email and does not modify existing application tables. Run it as a setup step once, not concurrently across replicas. Runtime needs read/write access to these tables; schema creation requires separate appropriate permissions. The application does not auto-create tables on public requests.

5. Once configuration and database are ready, set `CONTACT_EMAIL_ENABLED=true` and restart the backend. Configuration is cached per process. Switching off the flag and restarting disables real sends; the UI will not fake a success.
6. Perform an explicitly authorized test from a **new tab/session**: ask to contact Jeyker, choose compose, review the real-send notice, then confirm. Check both the Resend dashboard and the receiving inbox. A 200 response here does not establish inbox delivery. Existing simulation tokens are never silently exchanged for real-email tokens.

No real key, database provisioning, schema mutation on an external database, activation, deployment or test email was performed as part of implementation.

## Persistence, concurrency and retries

Real mode requires PostgreSQL and persists reservations before making the HTTP call. No new Python package is needed: SQLAlchemy/psycopg already exist; the adapter uses standard-library HTTPS.

- A server-generated opaque token represents the tab session. Only its SHA-256 hash is stored in the database.
- A global gate row serializes short reservation/quota transactions across workers and replicas. Network calls happen **outside** the transaction.
- A session reserves one exact normalized form and outbound payload, including sender/recipient, using a digest. Once reserved, a different request ID, edited content or sender configuration cannot reuse that session.
- The same session always supplies the same `Idempotency-Key` to Resend. Resend retains these keys for 24 hours; our session expires **23 hours after creation**, so retries cannot outlive that provider window. See [idempotency behavior](https://resend.com/docs/dashboard/emails/idempotency-keys).
- A 30-second lease throttles simultaneous/repeated attempts; HTTP timeout is 10 seconds. After a timeout, provider rejection, malformed response or interrupted connection, the request remains pending. Retry the **same** text and ID after 30 seconds. There is no background retry job.
- A provider acceptance followed by a failed database receipt write remains a pending reservation. Retrying uses the same provider key and body. No new key is generated to evade a failure.
- Provider errors are deliberately conservative: even a rejection preserves the reservation and consumes the daily attempt budget. Correcting a key may allow an identical retry; changing the sender/body requires another session, subject to shared limits.
- After acceptance, the receipt is persisted and identical retries return it without contacting Resend. Receipt status is recovered after reload/restart.
- The database stores token hash, expiry, payload digest, request ID, lease and provider ID—**not** name, reply email, subject, message or PDFs. Resend and the receiving mailbox necessarily process/store the email; the form explains that disclosure.
- The browser stores token, request ID and receipt status, not the draft. After an ambiguous attempt it freezes the current draft for exact retries. Reloading loses unsent text; a pending session with a lost draft cannot safely resume sending. It never silently starts another email. Contact details remain available.
- Expired rows are pruned when creating sessions. No background cleanup is installed. Database loss, uncoordinated restores, manual resets and incorrect clocks are outside the guarantee: keep one shared store and synchronized clocks. Do not delete reservations to recover an ambiguous send.

Simulation retains its earlier bounded in-memory implementation (24-hour expiry, 10,000 sessions, one process); it never calls Resend. Its tokens cannot be used in real mode.

## Abuse controls and scope

Defaults are **20 new send reservations per UTC day** and **60 new sessions per UTC hour**, shared across replicas. Exact retries do not consume another daily send slot, but remain lease-limited. These are conservative budget caps, not proof of human identity: an attacker can exhaust them and temporarily deny contact. New tabs/cleared storage are new sessions, not verified people.

Before broad public exposure, add infrastructure-level request limits and, if necessary, a challenge/verified identity. Do not trust forwarded IP headers without a configured trusted proxy. The contact API accepts a public form, not authenticated recruiters; a crafted request can assert confirmation. The agent's choice metadata is conversational routing, not a tamper-proof authorization system.

## API and code map

| Endpoint/component | Responsibility |
| --- | --- |
| `GET /contact/config` | Public mode and configured/enabled flag, no secrets. |
| `POST /contact/sessions` | Create a rate-limited server token. No email. |
| `GET /contact/session` | Bearer-authenticated accepted/pending status. |
| `POST /contact/submit` | Validate confirmed mode, exact form, reservation and quota; send through the configured service. |
| `resend_transport.py` | Fixed HTTPS endpoint, plain text, fixed recipient, optional reply-to, idempotency header, sanitized errors and no redirects. |
| `contact_store.py` | Shared PostgreSQL reservations, leases, quotas and receipts. |
| `contact_delivery.py` | Fail-closed server configuration and lazy service construction. |
| `ContactCard` / contact controller | Editable inline form, mode-specific consent, pending/accepted states and explicit retry. |

Confirmation must be boolean true; unknown submission fields are rejected. Status/config responses are `no-store`. Raw provider responses, credentials and form contents are not emitted into activity events. Public Markdown contact data remains agent-written.

## Verification

```sh
cd backend
python -m unittest discover -s tests
cd ../app
npm test
npm run build
```

Automated tests use fake HTTP and file-backed SQLite to exercise the SQLAlchemy store, including multiple service instances, concurrent submissions, quotas, expiry, pending recovery and receipt-write failure. Runtime rejects SQLite configuration for real sends. These tests **do not substitute for a PostgreSQL integration run**, live Resend verification, Gemini evaluation or browser QA; none is claimed here.

Manual acceptance should cover ordinary chat without invitations, both contact choices, mode-specific consent, disabled/missing settings, one accepted email, rejected duplicates, lost-response retry, reload/restart, ES/EN, keyboard/mobile, and a backend mode change between loading and confirming.

Delivery/bounce webhooks and durable background dispatch are future work. MCP remains optional; the narrow delivery service can be reused later without giving the model arbitrary email-sending authority.
