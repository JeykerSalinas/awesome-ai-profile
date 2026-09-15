import './assets/css/main.css'

import { createApp } from 'vue'
import ui from '@nuxt/ui/vue-plugin'
import posthog from 'posthog-js'

import App from './App.vue'
import router from './router'

const posthogKey = import.meta.env.VITE_POSTHOG_PROJECT_TOKEN
const posthogHost = import.meta.env.VITE_POSTHOG_HOST

if (!posthogKey || !posthogHost) {
  if (import.meta.env.DEV) {
    const missingVariable = !posthogKey ? 'VITE_POSTHOG_PROJECT_TOKEN' : 'VITE_POSTHOG_HOST'
    throw new Error(
      `${missingVariable} variable required by PostHog is missing or un-configured, this causes events to be silently missed. This error stops appearing once ${missingVariable} is configured`,
    )
  }
} else {
  posthog.init(posthogKey, {
    api_host: posthogHost,
    defaults: '2026-01-30',
  })
}

const app = createApp(App)

if (posthogKey && posthogHost) {
  app.config.errorHandler = (error) => {
    posthog.captureException(error)
  }
}

app.use(router)
app.use(ui)
app.mount('#app')
