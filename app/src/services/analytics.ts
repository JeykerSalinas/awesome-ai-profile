import posthog from 'posthog-js'
import { activeProfile } from '@/config/profile'

const posthogKey = activeProfile.analytics.projectToken || import.meta.env.VITE_POSTHOG_PROJECT_TOKEN
const posthogHost = activeProfile.analytics.host || import.meta.env.VITE_POSTHOG_HOST

export const analyticsEnabled = Boolean(activeProfile.analytics.enabled && posthogKey && posthogHost)

export function initAnalytics() {
  if (!analyticsEnabled) return

  posthog.init(posthogKey, {
    api_host: posthogHost,
    defaults: '2026-01-30',
    loaded: client => client.register({ profile_id: activeProfile.id }),
  })
}

export function captureEvent(
  eventName: string,
  properties?: Record<string, unknown>,
) {
  if (!analyticsEnabled) return

  posthog.capture(eventName, { ...properties, profile_id: activeProfile.id })
}

export function captureException(error: unknown) {
  if (!analyticsEnabled) return

  posthog.captureException(error)
}
