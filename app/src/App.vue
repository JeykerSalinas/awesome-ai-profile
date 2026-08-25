<script setup lang="ts">
import { RouterView } from 'vue-router'

import { useLocale } from '@/composables/useLocale'

const { uiLocale } = useLocale()
</script>

<template>
  <UApp :locale="uiLocale" :toaster="{ position: 'top-right' }">
    <RouterView />
  </UApp>
</template>
