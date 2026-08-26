<script setup lang="ts">
import { computed } from 'vue'
import { useLocale } from '@/composables/useLocale'
import { contactCopy } from '@/features/contact/copy'
import type { ContactChoice } from '@/features/contact/flow'

defineProps<{ busy: boolean; used: boolean; error: boolean }>()
const emit = defineEmits<{ choose: [choice: ContactChoice] }>()
const { locale } = useLocale()
const copy = computed(() => contactCopy[locale.value])
</script>

<template>
  <section class="space-y-2" :aria-label="copy.title">
    <div class="flex flex-wrap gap-2">
      <UButton type="button" icon="i-lucide-contact" variant="soft" :disabled="busy" @click="emit('choose', 'details')">{{ copy.details }}</UButton>
      <UButton type="button" icon="i-lucide-square-pen" variant="soft" :disabled="busy || used" @click="emit('choose', 'compose')">{{ copy.compose }}</UButton>
    </div>
    <p v-if="busy" role="status" class="text-xs text-(--django-muted)">{{ copy.choosing }}</p>
    <p v-if="used" class="text-xs text-(--django-muted)">{{ copy.usedNotice }}</p>
    <p v-if="error" role="alert" class="text-sm text-(--django-copy)">{{ copy.choiceError }}</p>
  </section>
</template>
