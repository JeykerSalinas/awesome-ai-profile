# Contact flow — demo delivery only

## What works

The assistant offers two choices inside a chat message:

- **View contact details:** a new user turn asks the agent for the explicitly authorized public phone, email and GitHub link. The agent reads them with `get_contact_details` and writes them in its normal Markdown answer, not a prebuilt contact panel.
- **Write an email:** a new user turn asks the agent to compose. Its `open_contact_form` tool embeds an editable message card in that assistant response, with a required sender name, subject and message, plus an optional reply email.

There is no first-answer or turn-count invitation. The agent decides whether the conversation shows concrete interest in hiring/interviewing Jeyker or an explicit request to contact him. Greetings, general experience questions, photo requests and polite thanks are not enough. When appropriate, it asks about contact and calls `offer_contact`. Only that tool's marker displays the two buttons, once per conversation, after streaming stops. An ordinary response displays neither the choices nor the form.

The human's click sends visible choice text plus `data-contact-choice` referencing the assistant offer. The backend validates this reference and scopes the next turn's tools: only `get_contact_details` for details, only `open_contact_form` for compose. Neither tool is available during the initial invitation. An ordinary later user turn clears the current choice and cannot automatically reopen a form. The existing offer buttons remain available for switching from details to compose, but a used session disables compose. Only the most recent form marker displays an editor; drafts and submission quota are shared across the conversation.

The user types and edits the message themselves. Pressing **Confirm simulated send** is the explicit confirmation of the current form, not a separate model-generated approval. Closing and reopening the editor preserves the draft while the app remains mounted and does not consume the quota. Name, subject and body cannot be blank. The optional reply email is format-checked, not identity-verified.

After submission the UI says **Simulation completed. No email has been sent.** There is no provider, SMTP connection, MCP client/server or real mail-delivery tool in this milestone. It implements the human-confirmation interaction and a server-enforced demo submission, not a LangGraph interrupt/resume workflow.

## Behavior versus tools

| Component | Responsibility |
| --- | --- |
| Agent prompt | Detect genuine interest, ask once, wait for the human choice; never claim to send or approve. |
| `offer_contact` tool | Returns a harmless invitation marker, not a form or contact data. |
| `get_contact_details` tool | Returns authorized public facts to the model for a normal conversational answer. |
| `open_contact_form` tool | Returns a form marker only on the compose-choice turn; cannot send. |
| Chat request / agent setup | Validate the choice reference and expose only the appropriate contact tool for this turn. |
| Activity/SSE adapters | Expose observed tool execution and typed `data-contact-offer` / `data-contact-form` parts, preserving their position among text parts. |
| `ContactChoices` / `ContactCard` | Render the two choice buttons / the inline editable fields, explicit confirmation and demo result. |
| `useContactFlow` / `features/contact/flow.ts` | Send the choice back into chat; share draft and session state, keeping form fields out of LLM history. |
| Contact API/service | Validate the exact submitted input, session token and one-submission limit. |

`MainView` only wires `provideContactFlow` to messages, API URL, chat status and `sendMessage`. Contact styling, strings, state and API calls live in dedicated files. All UI text is English/Spanish and follows the existing theme. Form labels, error/status announcements and explicit button types are included.

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
| `POST /contact/sessions` | Create a bounded, temporary session; return its bearer token. |
| `GET /contact/session` | Read whether the authenticated contact session has already been used. |
| `POST /contact/submit` | Validate and register one demo submission; return `status: simulated`, `delivered: false`. |

Submission fields: `request_id`, `sender_name`, `reply_email`, `subject`, `message`, `confirmed`. `confirmed` must be the boolean `true`, not a string or number. Unknown fields—including recipient overrides, attachments and chat history—are rejected. The sending endpoint is not exposed to the LLM as a tool. Session tokens are sent in the Authorization header, not URLs or prompts. Private responses use `Cache-Control: no-store`.

Public contact data is explicit configuration in `backend/services/public_contact.py`, exposed to the model through `get_contact_details`, not a frontend profile endpoint. It is not extracted from uploaded documents or added to the RAG index. It uses the owner's authorized professional phone/email and known GitHub account. The existing knowledge privacy checks remain intact. Markdown supports `tel:`, `mailto:` and HTTPS links; external/manual contact is outside the demo form's quota.

The human choice metadata is conversational routing, not authenticated consent or a tamper-proof authorization boundary: the client submits the conversation history. It does not authorize email delivery. The separate submit endpoint still validates the exact form, confirmation and session quota. The model decides when to invite and writes the contact answer, so semantic quality still requires live-model evaluation; the UI never infers interest from keywords.

## Verification

Backend tests cover required/invalid fields, strict confirmation, forbidden recipient overrides, unknown/expired sessions, capacity, independent sessions, concurrency, idempotency, status recovery, absence of retained message text, HTTP routes, scoped tools, invalid choice references, stale-choice clearing, failed/deduplicated tool markers and inline SSE ordering. Real LangChain agents with deterministic fake models exercise both branches without network access. Frontend tests exercise marker-only rendering, conversational choice dispatch, duplicate-click/busy guards, the contact controller with fake HTTP/storage, exact edited payloads, reloads, retries, expiration, blocked storage, localization, public Markdown links and the real AI SDK stream reader.

```sh
cd backend
python -m unittest discover -s tests -v
cd ../app
npm test
npm run build
```

Manual acceptance: greet the assistant and ask about general experience (no invitation/form); express interest in an interview (one invitation); choose details (agent-written phone/email/GitHub, no form); choose compose in the original invitation (new assistant response with inline editor); ask an unrelated question (no repeated invitation/form). Type a name/subject/body, edit the text, confirm the simulation, reload and verify that a second submission is unavailable while contact details remain accessible. Also test ES/EN, keyboard, mobile, retry and cancellation. No browser QA or live Gemini call is claimed by the automated suite.

## Next milestone, not implemented here

Connect a narrowly scoped MCP contact tool to a mail provider, preserving fixed recipient, exact-content confirmation and idempotency. Add production anti-abuse limits, safe shared session/receipt storage and delivery-status handling. Provider acceptance must not be described as inbox delivery. Do not expose an arbitrary-recipient email tool or reuse the demo's temporary store as a production delivery guarantee.
