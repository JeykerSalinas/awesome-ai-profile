import posthog from 'posthog-js'

const posthogKey = import.meta.env.VITE_POSTHOG_PROJECT_TOKEN
const posthogHost = import.meta.env.VITE_POSTHOG_HOST

export const analyticsEnabled = Boolean(posthogKey && posthogHost)

export function initAnalytics() {
  if (!posthogKey || !posthogHost) return

  posthog.init(posthogKey, {
    api_host: posthogHost,
    defaults: '2026-01-30',
  })
}

export function captureEvent(
  eventName: string,
  properties?: Record<string, unknown>,
) {
  if (!analyticsEnabled) return

  posthog.capture(eventName, properties)
}

export function captureException(error: unknown) {
  if (!analyticsEnabled) return

  posthog.captureException(error)
}
