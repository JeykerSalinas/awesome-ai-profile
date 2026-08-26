import type { ProfileMessage } from '../../types/chat.ts'
import { contactCopy } from './copy.ts'

export interface ContactDraft {
  sender_name: string
  reply_email: string
  subject: string
  message: string
}
export interface ContactState {
  draft: ContactDraft
  loading: boolean
  submitting: boolean
  used: boolean
  error: string
  choosing: boolean
  choiceError: boolean
  mode: 'simulation' | 'resend'
  ready: boolean
  available: boolean
  locked: boolean
  result: 'simulated' | 'accepted' | null
}
export const sessionKey = 'django-contact-session-v1'
export const usedKey = 'django-contact-used-v1'
export const requestKey = 'django-contact-request-v1'

export function initialContactState(): ContactState {
  return { draft: { sender_name: '', reply_email: '', subject: '', message: '' },
    loading: false, submitting: false, used: false, error: '', choosing: false, choiceError: false,
    mode: 'simulation', ready: false, available: false, locked: false, result: null }
}

export function validDraft(draft: ContactDraft): boolean {
  const name = draft.sender_name.trim(), subject = draft.subject.trim(), message = draft.message.trim()
  const email = draft.reply_email.trim()
  return !!name && name.length <= 100 && !!subject && subject.length <= 160
    && !!message && message.length <= 4000 && email.length <= 254
    && !/[\x00-\x1f\x7f]/.test(name + subject + email)
    && (!email || /^[^\s@<>,;]+@[^\s@<>,;]+\.[^\s@<>,;]+$/.test(email))
}

/** Only a real agent tool marker can offer contact. Never infer it from text/turn count. */
export function offersContact(message: ProfileMessage, messages: readonly ProfileMessage[], active: boolean): boolean {
  if (message.role !== 'assistant' || active) return false
  return messages.find(item => item.role === 'assistant' && item.parts.some(
    part => part.type === 'data-contact-offer',
  ))?.id === message.id
}

export function showsContactForm(message: ProfileMessage, messages: readonly ProfileMessage[], active: boolean): boolean {
  if (message.role !== 'assistant' || active) return false
  return [...messages].reverse().find(item => item.role === 'assistant' && item.parts.some(
    part => part.type === 'data-contact-form',
  ))?.id === message.id
}

export type ContactChoice = 'details' | 'compose'
export function contactChoiceParts(offerId: string, choice: ContactChoice, locale: 'es' | 'en'): ProfileMessage['parts'] {
  return [
    { type: 'text', text: contactCopy[locale][choice === 'details' ? 'requestDetails' : 'requestCompose'] },
    { type: 'data-contact-choice', data: { choice, offer_message_id: offerId } },
  ]
}

/** A click resumes the conversation, never opens a local details panel or form. */
export function createContactChoiceHandler(state: ContactState, messages: () => readonly ProfileMessage[],
  busy: () => boolean, send: (parts: ProfileMessage['parts']) => Promise<void>, locale: () => 'es' | 'en') {
  return async (offerId: string, choice: ContactChoice) => {
    if (busy() || state.choosing || (choice === 'compose' && state.used)) return
    const offer = messages().find(message => message.id === offerId)
    if (!offer || !offersContact(offer, messages(), false)) return
    state.choosing = true
    state.choiceError = false
    try { await send(contactChoiceParts(offerId, choice, locale())) }
    catch { state.choiceError = true }
    finally { state.choosing = false }
  }
}

type Storage = Pick<globalThis.Storage, 'getItem' | 'setItem'>
type Fetcher = typeof fetch

export function createContactController(state: ContactState, storage: Storage, fetcher: Fetcher, baseUrl: string) {
  let loaded = false
  let loading: Promise<void> | undefined
  let token = ''

  async function request(path: string, init: RequestInit = {}) {
    const response = await fetcher(`${baseUrl}/contact${path}`, {
      ...init, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...init.headers },
    })
    if (!response.ok) {
      const details = await response.json().catch(() => ({}))
      const codes: Record<string, string> = { contact_mode_changed: 'mode_changed', contact_payload_locked: 'locked',
        contact_delivery_pending: 'pending', contact_rate_limited: 'rate_limited' }
      if (codes[details.detail]) throw new Error(codes[details.detail])
      if (response.status === 401) throw new Error('expired')
      if (response.status === 409) throw new Error('used')
      if (response.status === 422) throw new Error('invalid')
      throw new Error('unavailable')
    }
    return response.json()
  }

  function markUsed(result: ContactState['result'] = null) {
    state.used = true
    state.result = result
    // Server is authoritative; storage protects the visible session across reloads too.
    try { storage.setItem(usedKey, result || 'true') } catch { /* Already locked in memory and on server. */ }
  }

  function report(error: unknown) {
    state.error = error instanceof Error && ['expired', 'used', 'invalid', 'storage', 'locked', 'pending', 'mode_changed', 'rate_limited'].includes(error.message)
      ? error.message : 'unavailable'
    if (state.error === 'used') markUsed()
  }

  function load(refresh = false): Promise<void> {
    if (loading) return loading
    if (loaded && !refresh) return Promise.resolve()
    loaded = false
    state.ready = false
    state.loading = true
    loading = Promise.resolve().then(async () => {
      try {
        try {
          token = storage.getItem(sessionKey) || ''
          const used = storage.getItem(usedKey)
          state.used = ['true', 'accepted', 'simulated'].includes(used || '')
          state.result = used === 'accepted' || used === 'simulated' ? used : null
        } catch { throw new Error('storage') }
        const config = await request('/config')
        if (!['simulation', 'resend'].includes(config.mode) || typeof config.available !== 'boolean') throw new Error('unavailable')
        state.mode = config.mode
        state.available = config.available
        if (token && !state.used) {
          const result = await request('/session')
          state.locked = !!result.pending
          if (result.used) markUsed(result.receipt?.status === 'accepted' ? 'accepted' : result.receipt?.status === 'simulated' ? 'simulated' : null)
        }
        loaded = true
        state.ready = true
        state.error = ''
      } catch (error) { report(error) }
      finally { state.loading = false; loading = undefined }
    })
    return loading
  }

  async function submit() {
    if (state.submitting || state.used) return
    // Never turn a click on a loading/demo UI into permission for a real email.
    if (!state.ready || !state.available) { state.error ||= 'unavailable'; return }
    if (!validDraft(state.draft)) { state.error = 'invalid'; return }
    // Capture the exact edited form at the moment of explicit user submission.
    const draft = Object.fromEntries(Object.entries(state.draft).map(([key, value]) => [key, value.trim()]))
    const deliveryMode = state.mode
    state.submitting = true
    let attempted = false
    try {
      if (state.used) return
      if (!loaded) return
      if (state.error === 'expired' || state.error === 'storage') return
      state.error = ''
      if (!token) {
        // Check writable tab storage before allocating a server session.
        try { storage.setItem(usedKey, 'false') } catch { throw new Error('storage') }
        const result = await request('/sessions', { method: 'POST' })
        token = result.token
        try { storage.setItem(sessionKey, token) } catch { throw new Error('storage') }
      }
      let requestId: string
      try {
        requestId = storage.getItem(requestKey) || crypto.randomUUID()
        storage.setItem(requestKey, requestId)
      } catch { throw new Error('storage') }
      attempted = true
      const result = await request('/submit', {
        method: 'POST', body: JSON.stringify({ ...draft, request_id: requestId, confirmed: true, delivery_mode: deliveryMode }),
      })
      if (deliveryMode === 'simulation' ? result.status !== 'simulated' || result.delivered !== false
        : result.status !== 'accepted' || result.delivered !== null) throw new Error('unavailable')
      markUsed(result.status)
    } catch (error) {
      report(error)
      // Unknown outcome: retain exact draft; a retry uses the same request ID.
      if (attempted && deliveryMode === 'resend') state.locked = true
      if (state.error === 'mode_changed') { state.ready = false; loaded = false }
    }
    finally { state.submitting = false }
  }
  return { state, load, submit }
}
