import type { ProfileMessage } from '../../types/chat.ts'

export interface ContactDraft {
  sender_name: string
  reply_email: string
  subject: string
  message: string
}
export interface PublicContact { name: string; phone: string; email: string; github: string }
export interface ContactState {
  profile: PublicContact | null
  draft: ContactDraft
  loading: boolean
  submitting: boolean
  used: boolean
  error: string
}
export const sessionKey = 'django-contact-session-v1'
export const usedKey = 'django-contact-used-v1'
export const requestKey = 'django-contact-request-v1'

export function initialContactState(): ContactState {
  return { profile: null, draft: { sender_name: '', reply_email: '', subject: '', message: '' },
    loading: false, submitting: false, used: false, error: '' }
}

export function validDraft(draft: ContactDraft): boolean {
  const name = draft.sender_name.trim(), subject = draft.subject.trim(), message = draft.message.trim()
  const email = draft.reply_email.trim()
  return !!name && name.length <= 100 && !!subject && subject.length <= 160
    && !!message && message.length <= 4000 && email.length <= 254
    && !/[\x00-\x1f\x7f]/.test(name + subject + email)
    && (!email || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
}

/** One automatic invitation; explicit tool calls can reopen the same shared form. */
export function offersContact(message: ProfileMessage, messages: readonly ProfileMessage[], active: boolean): boolean {
  if (message.role !== 'assistant' || active) return false
  if (message.parts.some(part => part.type === 'data-contact-offer')) return true
  return messages.find(item => item.role === 'assistant' && item.parts.some(
    part => part.type === 'text' && part.text.trim(),
  ))?.id === message.id
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
      if (response.status === 401) throw new Error('expired')
      if (response.status === 409) throw new Error('used')
      if (response.status === 422) throw new Error('invalid')
      throw new Error('unavailable')
    }
    return response.json()
  }

  function markUsed() {
    state.used = true
    // Server is authoritative; storage protects the visible session across reloads too.
    try { storage.setItem(usedKey, 'true') } catch { /* Already locked in memory and on server. */ }
  }

  function report(error: unknown) {
    state.error = error instanceof Error && ['expired', 'used', 'invalid', 'storage'].includes(error.message)
      ? error.message : 'unavailable'
    if (state.error === 'used') markUsed()
  }

  function load(): Promise<void> {
    if (loading) return loading
    if (loaded) return Promise.resolve()
    state.loading = true
    loading = (async () => {
      try {
        state.profile = await request('/profile')
        try {
          token = storage.getItem(sessionKey) || ''
          state.used = storage.getItem(usedKey) === 'true'
        } catch { throw new Error('storage') }
        if (token && !state.used) {
          const result = await request('/session')
          if (result.used) markUsed()
        }
        loaded = true
        state.error = ''
      } catch (error) { report(error) }
      finally { state.loading = false; loading = undefined }
    })()
    return loading
  }

  async function submit() {
    if (state.submitting || state.used) return
    if (!validDraft(state.draft)) { state.error = 'invalid'; return }
    // Capture the exact edited form at the moment of explicit user submission.
    const draft = Object.fromEntries(Object.entries(state.draft).map(([key, value]) => [key, value.trim()]))
    state.submitting = true
    try {
      await load()
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
      const result = await request('/submit', {
        method: 'POST', body: JSON.stringify({ ...draft, request_id: requestId, confirmed: true }),
      })
      if (result.status !== 'simulated' || result.delivered !== false) throw new Error('unavailable')
      markUsed()
    } catch (error) { report(error) }
    finally { state.submitting = false }
  }
  return { state, load, submit }
}
