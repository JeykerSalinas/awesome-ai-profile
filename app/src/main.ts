import './assets/css/main.css'

import { createApp } from 'vue'
import ui from '@nuxt/ui/vue-plugin'

import App from './App.vue'
import router from './router'
import { analyticsEnabled, captureException, initAnalytics } from './services/analytics'

initAnalytics()

const app = createApp(App)

if (analyticsEnabled) {
  app.config.errorHandler = (error) => {
    captureException(error)
  }
}

app.use(router)
app.use(ui)
app.mount('#app')
