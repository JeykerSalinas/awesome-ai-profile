<script setup lang="ts">
import { RouterView } from 'vue-router'
import { useStorage } from '@vueuse/core'

import DemoPrivacyNotice from '@/components/privacy/DemoPrivacyNotice.vue'
import { useLocale } from '@/composables/useLocale'

const { uiLocale } = useLocale()
const hasAcknowledgedDemoNotice = useStorage(
  'django-demo-notice-v1-acknowledged',
  false,
)
</script>

<template>
  <UApp :locale="uiLocale" :toaster="{ position: 'top-right' }">
    <RouterView />
    <DemoPrivacyNotice
      :open="!hasAcknowledgedDemoNotice"
      @accept="hasAcknowledgedDemoNotice = true"
    />
  </UApp>
</template>
