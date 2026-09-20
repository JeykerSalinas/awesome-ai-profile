<script setup lang="ts">
import { RouterView } from 'vue-router'
import { useStorage } from '@vueuse/core'

import DemoPrivacyNotice from '@/components/privacy/DemoPrivacyNotice.vue'
import { useLocale } from '@/composables/useLocale'
import { captureEvent } from '@/services/analytics'

const { uiLocale } = useLocale()
const hasAcknowledgedDemoNotice = useStorage(
  'django-demo-notice-v1-acknowledged',
  false,
)

function acceptDemoPrivacyNotice() {
  captureEvent('demo_privacy_notice_accepted')
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
