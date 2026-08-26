<script setup lang="ts">
import { defineAsyncComponent, nextTick, ref } from 'vue'
import { useLocale } from '@/composables/useLocale'
import { appendTourQuestion, storyCopy } from '@/features/tour/story'

// Keep lazy loading, session state and announcements out of the chat view.
const TechnologyTour = defineAsyncComponent(
  () => import('./TechnologyTour.vue'),
)
const draft = defineModel<string>('draft', { required: true })
const emit = defineEmits<{ opened: [] }>()
const { locale } = useLocale()
const open = ref(false)
const loaded = ref(false)
const announcement = ref('')

function openTour() {
  loaded.value = true
  open.value = true
  emit('opened')
}

defineExpose({ openTour })

async function prepareQuestion(question: string) {
  open.value = false
  draft.value = appendTourQuestion(draft.value, question)
  // Clear first so repeated preparations are announced too.
  announcement.value = ''
  await nextTick()
  announcement.value = storyCopy[locale.value].draftReady
  document
    .querySelector<HTMLTextAreaElement>('[data-tour="composer"] textarea')
    ?.focus()
}
</script>

<template>
  <p class="sr-only" role="status">{{ announcement }}</p>
  <TechnologyTour
    v-if="loaded"
    :open="open"
    @close="open = false"
    @prepare-question="prepareQuestion"
  />
</template>
