import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { readUIMessageStream, type UIMessageChunk } from 'ai'
import { createContactController, initialContactState, offersContact, requestKey, sessionKey, usedKey, validDraft } from '../src/features/contact/flow.ts'
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
const profile = { name: 'Jeyker', email: 'test@example.com', phone: '+34123456789', github: 'https://github.com/JeykerSalinas' }

test('name, subject and body are mandatory; email is optional and validated when provided', () => {
  assert.ok(validDraft(draft))
  assert.ok(validDraft({ ...draft, reply_email: '' }))
  for (const key of ['sender_name', 'subject', 'message']) assert.equal(validDraft({ ...draft, [key]: ' ' }), false)
  assert.equal(validDraft({ ...draft, reply_email: 'bad' }), false)
  assert.equal(validDraft({ ...draft, subject: 'Hi\nBcc: someone' }), false)
  assert.equal(validDraft({ ...draft, message: 'x'.repeat(4001) }), false)
})

test('automatic invitation appears once, while explicit tool offers can reopen shared contact', () => {
  const user: ProfileMessage = { id: 'u', role: 'user', parts: [{ type: 'text', text: 'Hello' }] }
  const first: ProfileMessage = { id: 'a', role: 'assistant', parts: [{ type: 'text', text: 'Hi' }] }
  const next: ProfileMessage = { ...first, id: 'b' }
  assert.equal(offersContact(user, [user, first], false), false)
  assert.equal(offersContact(first, [user, first], true), false)
  assert.equal(offersContact(first, [user, first], false), true)
  assert.equal(offersContact(next, [user, first, next], false), false)
  const explicit: ProfileMessage = { ...next, parts: [{ type: 'data-contact-offer', data: { mode: 'demo' } }] }
  assert.equal(offersContact(explicit, [first, explicit], false), true)
  assert.equal(offersContact({ ...first, parts: [] }, [], false), false)
})

test('loading/viewing contact never allocates a session or submits anything', async () => {
  const paths: string[] = []
  const flow = setup(async url => { paths.push(String(url)); return json(profile) })
  await Promise.all([flow.load(), flow.load()])
  assert.deepEqual(paths, ['https://api.test/contact/profile'])
  assert.equal(flow.state.used, false)
  assert.equal(flow.values.size, 0)
})

test('double click submits the exact edited payload once, and locks the session', async () => {
  const posts: Record<string, unknown>[] = []
  const flow = setup(async (url, init) => {
    if (String(url).endsWith('/profile')) return json(profile)
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
  const flow = setup(async url => { assert.ok(String(url).endsWith('/profile')); return json(profile) }, { [usedKey]: 'true', [sessionKey]: 'token' })
  await flow.load()
  await flow.submit()
  assert.equal(flow.state.used, true)
})

test('server receipt recovers a lost submit response after reload', async () => {
  const flow = setup(async url => String(url).endsWith('/profile') ? json(profile) : json({ used: true }), { [sessionKey]: 'token' })
  await flow.load()
  assert.equal(flow.state.used, true)
  assert.equal(flow.values.get(usedKey), 'true')
})

test('network failure preserves draft and request id for safe retry', async () => {
  const ids: string[] = []
  const flow = setup(async (url, init) => {
    if (String(url).endsWith('/profile')) return json(profile)
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
      return String(url).endsWith('/profile') ? json(profile) : json({}, status)
    }, { [sessionKey]: 'token' })
    await flow.load()
    await flow.submit()
    assert.equal(flow.state.used, status === 409)
    assert.ok(!urls.some(url => url.endsWith('/sessions') || url.endsWith('/submit')))
  }
})

test('invalid form makes no request and blocked storage cannot send', async () => {
  let calls = 0
  const flow = setup(async () => { calls++; return json(profile) })
  flow.state.draft.sender_name = ' '
  await flow.submit()
  assert.equal(calls, 0)
  const state = initialContactState(); state.draft = { ...draft }
  const blocked = createContactController(state, { getItem() { throw Error('blocked') }, setItem() { throw Error('blocked') } }, async () => { calls++; return json(profile) }, '')
  await blocked.submit()
  assert.equal(state.error, 'storage')
  assert.equal(state.used, false)
  assert.equal(calls, 1)
})

test('AI SDK accepts contact markers without leaking drafts into the chat', async () => {
  const chunks: UIMessageChunk[] = [
    { type: 'start', messageId: 'a' },
    { type: 'data-contact-offer', id: 'contact-offer', data: { mode: 'demo' } },
    { type: 'finish', finishReason: 'stop' },
  ]
  let latest: ProfileMessage | undefined
  const stream = new ReadableStream<UIMessageChunk>({ start(controller) { chunks.forEach(chunk => controller.enqueue(chunk)); controller.close() } })
  for await (const item of readUIMessageStream<ProfileMessage>({ stream })) latest = item
  assert.ok(latest?.parts.some(part => part.type === 'data-contact-offer'))
  assert.ok(!JSON.stringify(latest).includes('sender_name'))
})

test('a failed profile lookup can recover without a stale error', async () => {
  let calls = 0
  const flow = setup(async () => ++calls === 1 ? json({}, 503) : json(profile))
  await flow.load()
  assert.equal(flow.state.error, 'unavailable')
  await flow.load()
  assert.equal(flow.state.error, '')
  assert.deepEqual(flow.state.profile, profile)
})

test('UI is bilingual, editable, explicit about simulation and isolated from MainView', () => {
  assert.deepEqual(Object.keys(contactCopy.es), Object.keys(contactCopy.en))
  assert.deepEqual(Object.keys(contactCopy.es.errors), Object.keys(contactCopy.en.errors))
  const card = readFileSync(new URL('../src/components/chat/ContactCard.vue', import.meta.url), 'utf8')
  for (const value of ['<textarea', 'autocomplete="name"', 'required', '@submit.prevent', 'role="status"', 'role="alert"', 'aria-expanded']) assert.ok(card.includes(value))
  for (const value of ['sendMessage(', 'v-html', 'localStorage']) assert.ok(!card.includes(value))
  const view = readFileSync(new URL('../src/views/MainView.vue', import.meta.url), 'utf8')
  assert.ok(view.includes('provideContactFlow(messages, apiBaseUrl)'))
  assert.ok(!view.includes('sender_name'))
})
