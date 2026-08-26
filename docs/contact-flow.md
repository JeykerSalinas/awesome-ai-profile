# Contact flow — demo delivery only

## What works

The assistant offers two choices inside a chat message:

- **View contact details:** the explicitly authorized public phone, email and GitHub link.
- **Write an email:** an editable message card with a required sender name, subject and message, plus an optional reply email.

The first assistant answer with text gets one automatic invitation after it stops streaming. When the visitor explicitly asks about contact/interviews, the agent can also call `offer_contact` to show these same choices in its current answer. Repeated invitations share the same draft and submission quota. The invitation does not open either choice automatically, overwrite the chat composer or send anything.

The user types and edits the message themselves. Pressing **Confirm simulated send** is the explicit confirmation of the current form, not a separate model-generated approval. Closing or switching away from the editor preserves the draft while the app remains mounted and does not consume the quota. Name, subject and body cannot be blank. The optional reply email is format-checked, not identity-verified.

After submission the UI says **Simulation completed. No email has been sent.** There is no provider, SMTP connection, MCP client/server or real mail-delivery tool in this milestone. It implements the human-confirmation interaction and a server-enforced demo submission, not a LangGraph interrupt/resume workflow.

## Behavior versus tools

| Component | Responsibility |
| --- | --- |
| Agent prompt | Offer contact naturally; never claim to send or approve on behalf of the visitor. |
| `offer_contact` tool | Returns a harmless contact-offer marker; has no sending capability. |
| Activity/SSE adapters | Expose observed tool execution and a typed `data-contact-offer` part. |
| `ContactCard` | Show the two choices, editable fields, explicit confirmation and demo result. |
| `useContactFlow` / `features/contact/flow.ts` | Share draft and state across message cards; keep them out of LLM history. |
| Contact API/service | Validate the exact submitted input, session token and one-submission limit. |

`MainView` only calls `provideContactFlow(messages, apiBaseUrl)`. Contact styling, strings, state and API calls live in dedicated files. All UI text is English/Spanish and follows the existing theme. Form labels, error/status announcements and explicit button types are included.

## Session definition and limits

- A session is this browser tab's contact session, represented by an opaque server-generated bearer token in `sessionStorage`.
- It survives a page reload and chat-message regeneration. A new independent tab or cleared session storage can create a new session; this is **not one email per verified person** and is not a production anti-spam system.
- Sessions expire after 24 hours from creation. The store is process-local and holds at most 10,000 live sessions. Creation removes expired entries; use of an expired entry removes it immediately. There is no background expiration timer.
- Backend restart loses session state. An existing token is rejected; the frontend does not silently replace it with a fresh session. This demo assumes one backend process/replica. Shared or durable state is required before multi-replica production delivery.
- A lock makes submission atomic: two simultaneous distinct submissions cannot consume the same session twice. An exact retry returns the same receipt; changing the request ID or any submitted field after success returns HTTP 409.
- Only validation-successful, explicitly confirmed submissions consume the quota. Looking at public details, opening/closing the editor and invalid forms do not.
- Browser storage contains the opaque session token, request ID and used flag, **not** the draft, name, email or body. The server retains only expiration, receipt and a payload hash for safe retries; no message content, chat or PDFs are stored by this feature. Reloading loses an unfinished draft.
- API failures are visible. After a lost response, retrying the same form is safe; reloading recovers the used state from the server. The local used flag also keeps the tab locked after an acknowledged success.

## API contract

| Endpoint | Purpose |
| --- | --- |
| `GET /contact/profile` | Public, owner-authorized contact details. |
| `POST /contact/sessions` | Create a bounded, temporary session; return its bearer token. |
| `GET /contact/session` | Read whether the authenticated contact session has already been used. |
| `POST /contact/submit` | Validate and register one demo submission; return `status: simulated`, `delivered: false`. |

Submission fields: `request_id`, `sender_name`, `reply_email`, `subject`, `message`, `confirmed`. `confirmed` must be the boolean `true`, not a string or number. Unknown fields—including recipient overrides, attachments and chat history—are rejected. The sending endpoint is not exposed to the LLM as a tool. Session tokens are sent in the Authorization header, not URLs or prompts. Private responses use `Cache-Control: no-store`.

Public contact data is explicit configuration in `backend/routes/contact.py`, not extracted from uploaded documents or added to the RAG index. It uses the owner's authorized professional phone/email and known GitHub account. The existing knowledge privacy checks remain intact. A `mailto:` link merely opens the visitor's own email application; external/manual contact is outside the demo form's quota.

## Verification

Backend tests cover required/invalid fields, strict confirmation, forbidden recipient overrides, unknown/expired sessions, capacity, independent sessions, concurrency, idempotency, status recovery, absence of retained message text, HTTP routes, tool markers and SSE continuity. Frontend tests exercise the real contact controller with fake HTTP/storage, exact edited payloads, double clicks, reloads, network failures, expiration, blocked storage, localization and the real AI SDK stream reader.

```sh
cd backend
python -m unittest discover -s tests -v
cd ../app
npm test
npm run build
```

Manual acceptance: ask about Jeyker, open the two contact choices, type a name/subject/body, edit the text, confirm the simulation, reload and verify that a second submission is unavailable while contact details remain accessible. Also test explicit contact requests, ES/EN, keyboard, mobile, retry and cancellation. No browser QA or live Gemini call is claimed by the automated suite.

## Next milestone, not implemented here

Connect a narrowly scoped MCP contact tool to a mail provider, preserving fixed recipient, exact-content confirmation and idempotency. Add production anti-abuse limits, safe shared session/receipt storage and delivery-status handling. Provider acceptance must not be described as inbox delivery. Do not expose an arbitrary-recipient email tool or reuse the demo's temporary store as a production delivery guarantee.
