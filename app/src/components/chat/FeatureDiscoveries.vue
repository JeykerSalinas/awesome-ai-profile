<script setup lang="ts">
import { computed } from 'vue'
import FeatureExplainer from './FeatureExplainer.vue'
import { useFeatureDiscovery } from '@/composables/useFeatureDiscovery'
import { useLocale } from '@/composables/useLocale'
import { insightCopy } from '@/features/insights/catalog'
import type { ProfileMessage } from '@/types/chat'

const props = defineProps<{ message: ProfileMessage }>()
const discovered = useFeatureDiscovery(() => props.message)
const { locale } = useLocale()
const copy = computed(() => insightCopy[locale.value])
</script>

<template>
  <section v-if="discovered.length" :aria-label="copy.discoveries" class="space-y-2 pt-2">
    <p class="text-xs font-medium text-(--django-muted)">{{ copy.discoveries }}</p>
    <FeatureExplainer v-for="feature in discovered" :key="feature" :feature="feature" />
  </section>
</template>
