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
| `resend`, configured and enabled | Confirm and send email | `status: accepted`, `delivered: null`. Provider acceptance, not confirmed inbox delivery. |
| `resend`, disabled/missing configuration | Sending disabled | No fallback to a simulated success. |

The frontend loads `GET /contact/config` before enabling confirmation. It exposes only mode and configuration availability, never secrets, and does not check live provider health. The POST includes `delivery_mode`; a confirmation for a different mode is rejected.

Recipient is fixed to the owner's authorized address in `services/public_contact.py`. Sender is server-configured, never the visitor. The optional visitor address becomes `reply_to` only. Visitor identity is explicitly unverified in the plain-text email. No arbitrary recipients, CC/BCC, HTML, attachments, conversation history or uploaded PDFs.

## Activate without a database

**No PostgreSQL, Redis, SQLite, volume or schema setup is required for contact.** The existing project-wide `DATABASE_URL`, SQLAlchemy dependencies and local Docker Compose groundwork are unrelated and left unchanged. The old contact-table initialization script was removed; prior code remains in Git history. A legacy `CONTACT_DATABASE_URL` is accepted but ignored for compatibility with earlier .env files; it can be removed.

1. Create a Resend account. For a controlled test without a domain, its account email must be **jeyker.salinas13@gmail.com**, our fixed recipient. The `onboarding@resend.dev` sender is for testing and can send only to the account's own address. Use a verified domain before treating this as a production sender. See [testing restrictions](https://resend.com/docs/knowledge-base/403-error-resend-dev-domain).
2. Create a **sending-access** API key, restricted to your domain when applicable. Put it in backend secrets, never chat, Git, frontend `VITE_*` variables, logs or browser storage. See [key permissions](https://resend.com/docs/api-reference/api-keys/create-api-key).
3. Configure the existing backend:

```dotenv
CONTACT_DELIVERY_MODE=resend
CONTACT_EMAIL_ENABLED=false
RESEND_API_KEY=<backend-secret>
CONTACT_FROM_EMAIL=Portfolio <onboarding@resend.dev>
CONTACT_DAILY_LIMIT=20
CONTACT_SESSIONS_PER_HOUR=60
CONTACT_MAX_SESSIONS=10000
```

In Azure, store the API key as a Container Apps secret and bind `RESEND_API_KEY` to it. Other settings can be ordinary backend environment variables. No additional database service is needed.

4. Use **one backend process/worker and one active replica** for this demo. Each process has its own store. Multiple workers/replicas or overlapping deployment revisions cannot share sessions or limits. Scale-to-zero also loses RAM. Keeping a replica running does not make memory durable.
5. Set `CONTACT_EMAIL_ENABLED=true` only when ready to permit real sends and restart the backend. Configuration is cached per process. To disable sending, set the flag false and restart. Repository defaults remain simulation/disabled.
6. Test only with explicit permission, in a new tab/session: ask to contact Jeyker, choose compose, review the real-send notice, confirm and check both the Resend dashboard and inbox. A 200 response does not establish delivery. Existing simulation tokens are not exchanged for real-email tokens.

No account, key, cloud resource, deployment, activation or test email was created/performed during this code change.

## Memory lifecycle, concurrency and retries

The session state lives only in the backend process. Reloading a browser can recover it **while that same process and store remain alive**.

- An opaque server-generated token identifies the tab session; RAM stores only its SHA-256 hash.
- A lock makes session creation, reservation, quotas and receipt updates atomic within the process. HTTP runs **outside** the lock.
- The service reserves one exact normalized form and outbound payload, including sender/recipient, using a digest. Different text, request ID or sender settings cannot reuse a reserved session.
- The same session supplies a stable `Idempotency-Key` to Resend. Its 24-hour retention window is longer than our **23-hour session lifetime**. This protects identical retries; it is not durable session storage. See [idempotency](https://resend.com/docs/dashboard/emails/idempotency-keys).
- A 30-second lease throttles attempts; the HTTP timeout is 10 seconds. A timeout, provider rejection, malformed response or interrupted connection leaves the request pending. Retry the same text and ID after 30 seconds, only while the session exists. There are no background retries.
- Even a rejection conservatively reserves the session and consumes the process's daily attempt budget. Correcting a key may permit an identical retry; changing sender/body cannot mutate a pending reservation.
- After acceptance, identical retries return the in-memory receipt without another provider call. If recording the receipt fails but the process survives, retry uses the same key/body.
- RAM retains token hash, expiry, digest, request ID, lease and provider ID—not name, reply email, subject, message or PDFs. Resend and the recipient mailbox necessarily process/store the email; the form explains that disclosure.
- Browser sessionStorage contains token, request ID and result, not draft text. After an ambiguous attempt the draft is frozen for exact retries. Reloading loses that draft; a pending session without the original text cannot safely resume sending.
- The store is capped at `CONTACT_MAX_SESSIONS` (10,000 by default). Creation prunes expired entries; access removes expired tokens. No background cleanup or disk writes occur.

### Restart, deployment or another replica

**Sessions, receipts and counters are lost on restart.** Old tokens are rejected with HTTP 401 before contacting Resend. The frontend displays expiry/restart and does not silently allocate another session or resubmit.

An email may already have been accepted before the restart, even if its receipt was lost. Resend's idempotency alone cannot reconstruct our lost session; do not open another session to retry an uncertain send without first checking its status outside this flow. Known browser success flags remain visible across reloads, but do not recover server state.

New explicit sessions after a restart have a fresh process budget. Another replica has independent counters and rejects tokens created elsewhere. **The one-email rule and aggregate caps are not durable or shared across processes.** This is an intentional demo tradeoff, not a production guarantee.

Simulation keeps its separate bounded in-memory store (24-hour expiry, 10,000 sessions) and never contacts Resend.

## Limits and future storage

Defaults are **20 new send reservations per UTC day**, **60 new sessions per UTC hour**, and **10,000 live sessions**, all **per process**. Exact retries do not consume another daily reservation but respect the lease. Restarts reset counters. These caps do not verify identity: an attacker could exhaust them and deny contact temporarily. New tabs/cleared storage represent new sessions, not verified people.

Before wider public exposure, consider infrastructure-level request limits and a challenge/verified identity. The public form can be submitted by a crafted client asserting confirmation; agent choice metadata is routing, not authentication.

Storage is an explicit `ContactStore` protocol with four operations: `create_session`, `status`, `reserve` and `accept`. `EmailContactService` handles validation, digesting and Resend independently. Later we can implement a database-backed store and change the factory without rewriting the form or delivery adapter. That adapter must preserve atomic reservations/quotas, stable keys, expiry and pending semantics across processes; no unused database implementation is kept active now.

## API and code map

| Endpoint/component | Responsibility |
| --- | --- |
| `GET /contact/config` | Public delivery mode and configured/enabled flag, no secrets. |
| `POST /contact/sessions` | Allocate a bounded, rate-limited process-local session. No email. |
| `GET /contact/session` | Bearer-authenticated accepted/pending status; unknown tokens rejected. |
| `POST /contact/submit` | Validate confirmed mode, exact form, reservation and quota; then send. |
| `resend_transport.py` | Fixed HTTPS endpoint and recipient, plain text, optional reply-to, stable key, sanitized provider errors, no redirects. |
| `contact_store.py` | Storage contract and bounded lock-protected memory implementation. |
| `contact_email_service.py` | Confirmed delivery orchestration, independent of storage. |
| `contact_delivery.py` | Opt-in configuration and thread-safe lazy singleton construction. |
| `ContactCard` / contact controller | Inline editing, mode-specific consent, pending/accepted/expired states and explicit retry. |

Confirmation must be boolean true; unknown fields are rejected. Status/config responses are `no-store`. No raw provider payloads, credentials or form content enter activity events. Public contact data remains agent-written.

## Verification

```sh
cd backend
python -m unittest discover -s tests
cd ../app
npm test
npm run build
```

Automated tests use fake HTTP and the real memory store. They cover shared-store concurrency, cold singleton construction, lock-free network calls, capacity, quotas, expiry, retries, receipt failure, deliberate counter reset and rejection of old tokens after a restart. No database is created or required for contact tests.

Manual acceptance: ordinary chat without invitations; both contact choices; real/demo consent; disabled settings; one accepted email; duplicate rejection; lost-response retry while the process lives; reload; backend restart with an old token (no resend/new session); ES/EN and keyboard/mobile. No live Resend, inbox, Gemini or browser QA is claimed by the automated suite.

Delivery webhooks, durable storage and background dispatch remain future work. MCP is optional and not implemented here.
