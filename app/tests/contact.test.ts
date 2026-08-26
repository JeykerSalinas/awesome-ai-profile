import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { readUIMessageStream, type UIMessageChunk } from 'ai'
import { contactChoiceParts, createContactChoiceHandler, createContactController, initialContactState, offersContact, showsContactForm, requestKey, sessionKey, usedKey, validDraft } from '../src/features/contact/flow.ts'
import { contactCopy } from '../src/features/contact/copy.ts'
import type { ProfileMessage } from '../src/types/chat.ts'

const draft = { sender_name: 'Ada', reply_email: 'ada@example.com', subject: 'Interview', message: 'Would you like to talk?' }
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status })
function setup(fetcher: typeof fetch, initial: Record<string, string> = {}) {
  const values = new Map(Object.entries(initial))
  const storage = { getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => { values.set(key, value) } }
  const state = initialContactState()
  state.draft = { ...draft }
  return { ...createContactController(state, storage, fetcher, 'https://api.test'), values, storage }
}
const offer: ProfileMessage = { id: 'offer', role: 'assistant', parts: [{ type: 'data-contact-offer', data: { mode: 'demo' } }] }

test('name, subject and body are mandatory; email is optional and validated when provided', () => {
  assert.ok(validDraft(draft))
  assert.ok(validDraft({ ...draft, reply_email: '' }))
  for (const key of ['sender_name', 'subject', 'message']) assert.equal(validDraft({ ...draft, [key]: ' ' }), false)
  assert.equal(validDraft({ ...draft, reply_email: 'bad' }), false)
  assert.equal(validDraft({ ...draft, subject: 'Hi\nBcc: someone' }), false)
  assert.equal(validDraft({ ...draft, message: 'x'.repeat(4001) }), false)
})

test('ordinary answers never invite contact; only the first agent offer renders choices', () => {
  const user: ProfileMessage = { id: 'u', role: 'user', parts: [{ type: 'text', text: 'Hello' }] }
  const first: ProfileMessage = { id: 'a', role: 'assistant', parts: [{ type: 'text', text: 'Hi' }] }
  const next: ProfileMessage = { ...first, id: 'b' }
  assert.equal(offersContact(user, [user, first], false), false)
  assert.equal(offersContact(first, [user, first], true), false)
  assert.equal(offersContact(first, [user, first], false), false)
  assert.equal(offersContact(next, [user, first, next], false), false)
  const explicit: ProfileMessage = { ...next, parts: [{ type: 'data-contact-offer', data: { mode: 'demo' } }] }
  assert.equal(offersContact(explicit, [first, explicit], false), true)
  assert.equal(offersContact(explicit, [offer, explicit], false), false)
  assert.equal(offersContact({ ...offer, role: 'user' }, [offer], false), false)
  assert.equal(offersContact(offer, [offer], true), false)
  const keywords: ProfileMessage = { ...first, parts: [{ type: 'text', text: 'Contact email interview hiring' }] }
  assert.equal(offersContact(keywords, [keywords], false), false)
  assert.equal(offersContact({ ...first, parts: [] }, [], false), false)
})

test('an offer never renders the form; only the latest agent form marker does', () => {
  const form: ProfileMessage = { id: 'form', role: 'assistant', parts: [{ type: 'data-contact-form', data: { mode: 'demo' } }] }
  const later = { ...form, id: 'later' }
  assert.equal(showsContactForm(offer, [offer], false), false)
  assert.equal(showsContactForm(form, [offer, form], false), true)
  assert.equal(showsContactForm(form, [offer, form], true), false)
  assert.equal(showsContactForm(form, [offer, form, later], false), false)
  assert.equal(showsContactForm(later, [offer, form, later], false), true)
  assert.equal(showsContactForm({ ...form, role: 'user' }, [form], false), false)
})

test('each human choice sends a normal chat turn plus a typed reference to the offer', async () => {
  for (const choice of ['details', 'compose'] as const) {
    for (const locale of ['es', 'en'] as const) {
      const state = initialContactState()
      const sent: ProfileMessage['parts'][] = []
      const choose = createContactChoiceHandler(state, () => [offer], () => false,
        async parts => { sent.push(parts) }, () => locale)
      await Promise.all([choose(offer.id, choice), choose(offer.id, choice)])
      assert.deepEqual(sent, [contactChoiceParts(offer.id, choice, locale)])
      assert.deepEqual(sent[0]?.[1], { type: 'data-contact-choice', data: { choice, offer_message_id: offer.id } })
      assert.ok(!JSON.stringify(sent).includes('sender_name'))
      assert.equal(state.choosing, false)
      assert.deepEqual(state.draft, initialContactState().draft)
    }
  }
})

test('choice guard rejects missing offers, active streams and used compose, but allows viewing details', async () => {
  const state = initialContactState()
  let busy = false, calls = 0
  const choose = createContactChoiceHandler(state, () => [offer], () => busy, async () => { calls++ }, () => 'es')
  await choose('missing', 'compose')
  busy = true
  await choose(offer.id, 'details')
  busy = false; state.used = true
  await choose(offer.id, 'compose')
  assert.equal(calls, 0)
  await choose(offer.id, 'details')
  assert.equal(calls, 1)
})

test('failed choice can be retried without leaving the UI busy', async () => {
  const state = initialContactState()
  let calls = 0
  const choose = createContactChoiceHandler(state, () => [offer], () => false,
    async () => { if (++calls === 1) throw Error('network') }, () => 'en')
  await choose(offer.id, 'compose')
  assert.equal(state.choiceError, true)
  assert.equal(state.choosing, false)
  await choose(offer.id, 'compose')
  assert.equal(state.choiceError, false)
})

test('loading/viewing contact never allocates a session or submits anything', async () => {
  const paths: string[] = []
  const flow = setup(async url => { paths.push(String(url)); return json({}) })
  await Promise.all([flow.load(), flow.load()])
  assert.deepEqual(paths, [])
  assert.equal(flow.state.used, false)
  assert.equal(flow.values.size, 0)
})

test('double click submits the exact edited payload once, and locks the session', async () => {
  const posts: Record<string, unknown>[] = []
  const flow = setup(async (url, init) => {
    if (String(url).endsWith('/sessions')) return json({ token: 'server-token' })
    posts.push(JSON.parse(String(init?.body)))
    assert.equal((init?.headers as Record<string, string>).Authorization, 'Bearer server-token')
    return json({ request_id: posts[0]?.request_id, status: 'simulated', delivered: false })
  })
  flow.state.draft.message = 'My edited message'
  await Promise.all([flow.submit(), flow.submit()])
  await flow.submit()
  assert.equal(posts.length, 1)
  assert.equal(posts[0]?.message, 'My edited message')
  assert.equal(posts[0]?.confirmed, true)
  assert.equal(posts[0]?.sender_name, 'Ada')
  for (const forbidden of ['to', 'history', 'documents']) assert.equal(forbidden in posts[0]!, false)
  assert.equal(flow.state.used, true)
  assert.equal(flow.values.get(usedKey), 'true')
  assert.equal(flow.values.get(sessionKey), 'server-token')
  assert.ok(flow.values.get(requestKey))
})

test('a local used flag survives reload without sending or resetting the session', async () => {
  const flow = setup(async () => { assert.fail('used sessions need no request') }, { [usedKey]: 'true', [sessionKey]: 'token' })
  await flow.load()
  await flow.submit()
  assert.equal(flow.state.used, true)
})

test('server receipt recovers a lost submit response after reload', async () => {
  const flow = setup(async url => { assert.ok(String(url).endsWith('/session')); return json({ used: true }) }, { [sessionKey]: 'token' })
  await flow.load()
  assert.equal(flow.state.used, true)
  assert.equal(flow.values.get(usedKey), 'true')
})

test('network failure preserves draft and request id for safe retry', async () => {
  const ids: string[] = []
  const flow = setup(async (url, init) => {
    if (String(url).endsWith('/sessions')) return json({ token: 'token' })
    ids.push(JSON.parse(String(init?.body)).request_id)
    if (ids.length === 1) throw new Error('network')
    return json({ status: 'simulated', delivered: false })
  })
  await flow.submit()
  assert.equal(flow.state.error, 'unavailable')
  assert.equal(flow.state.used, false)
  assert.deepEqual(flow.state.draft, draft)
  await flow.submit()
  assert.equal(ids[0], ids[1])
  assert.equal(flow.state.used, true)
})

test('server conflict locks the form; expiry never silently creates another session', async () => {
  for (const status of [401, 409]) {
    const urls: string[] = []
    const flow = setup(async url => {
      urls.push(String(url))
      return json({}, status)
    }, { [sessionKey]: 'token' })
    await flow.load()
    await flow.submit()
    assert.equal(flow.state.used, status === 409)
    assert.ok(!urls.some(url => url.endsWith('/sessions') || url.endsWith('/submit')))
  }
})

test('invalid form makes no request and blocked storage cannot send', async () => {
  let calls = 0
  const flow = setup(async () => { calls++; return json({}) })
  flow.state.draft.sender_name = ' '
  await flow.submit()
  assert.equal(calls, 0)
  const state = initialContactState(); state.draft = { ...draft }
  const blocked = createContactController(state, { getItem() { throw Error('blocked') }, setItem() { throw Error('blocked') } }, async () => { calls++; return json({}) }, '')
  await blocked.submit()
  assert.equal(state.error, 'storage')
  assert.equal(state.used, false)
  assert.equal(calls, 0)
})

test('AI SDK preserves inline text/form order without leaking drafts into the chat', async () => {
  const chunks: UIMessageChunk[] = [
    { type: 'start', messageId: 'a' },
    { type: 'text-start', id: 'before' },
    { type: 'text-delta', id: 'before', delta: 'Write your message here.' },
    { type: 'text-end', id: 'before' },
    { type: 'data-contact-form', id: 'contact-form', data: { mode: 'demo' } },
    { type: 'text-start', id: 'after' },
    { type: 'text-delta', id: 'after', delta: 'Nothing will be sent yet.' },
    { type: 'text-end', id: 'after' },
    { type: 'finish', finishReason: 'stop' },
  ]
  let latest: ProfileMessage | undefined
  const stream = new ReadableStream<UIMessageChunk>({ start(controller) { chunks.forEach(chunk => controller.enqueue(chunk)); controller.close() } })
  for await (const item of readUIMessageStream<ProfileMessage>({ stream })) latest = item
  assert.deepEqual(latest?.parts.map(part => part.type), ['text', 'data-contact-form', 'text'])
  assert.ok(!JSON.stringify(latest).includes('sender_name'))
})

test('a failed session lookup can recover without a stale error', async () => {
  let calls = 0
  const flow = setup(async () => ++calls === 1 ? json({}, 503) : json({ used: false }), { [sessionKey]: 'token' })
  await flow.load()
  assert.equal(flow.state.error, 'unavailable')
  await flow.load()
  assert.equal(flow.state.error, '')
  assert.equal(flow.state.used, false)
})

test('synchronous blocked storage can recover on a later load', async () => {
  let blocked = true
  const state = initialContactState()
  const flow = createContactController(state, { getItem() { if (blocked) throw Error('blocked'); return null }, setItem() {} },
    async () => { assert.fail('loading a fresh session must not fetch contact data') }, '')
  await flow.load()
  assert.equal(state.error, 'storage')
  blocked = false
  await flow.load()
  assert.equal(state.error, '')
  assert.equal(state.loading, false)
})

test('UI is bilingual, editable, explicit about simulation and isolated from MainView', () => {
  assert.deepEqual(Object.keys(contactCopy.es), Object.keys(contactCopy.en))
  assert.deepEqual(Object.keys(contactCopy.es.errors), Object.keys(contactCopy.en.errors))
  const card = readFileSync(new URL('../src/components/chat/ContactCard.vue', import.meta.url), 'utf8')
  for (const value of ['<textarea', 'autocomplete="name"', 'required', '@submit.prevent', 'role="status"', 'role="alert"']) assert.ok(card.includes(value))
  for (const value of ['sendMessage(', 'v-html', 'localStorage']) assert.ok(!card.includes(value))
  const view = readFileSync(new URL('../src/views/MainView.vue', import.meta.url), 'utf8')
  assert.ok(view.includes('provideContactFlow(messages, apiBaseUrl, status,'))
  assert.ok(!view.includes('sender_name'))
  const content = readFileSync(new URL('../src/components/chat/ChatMessageContent.vue', import.meta.url), 'utf8')
  assert.ok(content.includes("part.type === 'data-contact-form' && showForm"))
  assert.ok(content.indexOf('<ContactCard') < content.indexOf('</template>\n    <Transition'))
  assert.ok(!card.includes('state.profile'))
  assert.ok(!card.includes('contact-details'))
})
