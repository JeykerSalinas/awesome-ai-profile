<script setup lang="ts">
import { RouterView } from 'vue-router'
import { useStorage } from '@vueuse/core'
import posthog from 'posthog-js'

import DemoPrivacyNotice from '@/components/privacy/DemoPrivacyNotice.vue'
import { useLocale } from '@/composables/useLocale'

const posthogConfigured = Boolean(
  import.meta.env.VITE_POSTHOG_PROJECT_TOKEN && import.meta.env.VITE_POSTHOG_HOST,
)
const { uiLocale } = useLocale()
const hasAcknowledgedDemoNotice = useStorage(
  'django-demo-notice-v1-acknowledged',
  false,
)

function acceptDemoPrivacyNotice() {
  if (posthogConfigured) posthog.capture('demo_privacy_notice_accepted')
  hasAcknowledgedDemoNotice.value = true
}
</script>

<template>
  <UApp :locale="uiLocale" :toaster="{ position: 'top-right' }">
    <RouterView />
    <DemoPrivacyNotice
      :open="!hasAcknowledgedDemoNotice"
      @accept="acceptDemoPrivacyNotice"
    />
  </UApp>
</template>
