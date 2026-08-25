<script setup lang="ts">
import { useLocale } from '@/composables/useLocale'

defineProps<{
  approvalId: string
  toolName: string
  input: unknown
}>()

const { text } = useLocale()

const emit = defineEmits<{
  approve: [approvalId: string]
  reject: [approvalId: string]
}>()
</script>

<template>
  <UCard class="my-4 max-w-lg border border-(--django-border) bg-(--django-surface-soft)">
    <div class="flex gap-3">
      <UIcon name="i-lucide-shield-question" class="mt-0.5 size-5 shrink-0 text-amber-600" />
      <div class="min-w-0 flex-1 space-y-3">
        <div>
          <p class="text-sm font-semibold text-(--django-heading)">{{ text.approvalRequired }}</p>
          <p class="mt-1 text-sm text-(--django-copy)">
            {{ text.approvalDescription }} <strong>{{ toolName }}</strong>.
          </p>
        </div>
        <pre
          v-if="input && typeof input === 'object'"
          class="overflow-x-auto rounded-xl bg-(--django-surface) p-3 text-xs text-(--django-copy)"
        >{{ JSON.stringify(input, null, 2) }}</pre>
        <div class="flex flex-wrap gap-2">
          <UButton icon="i-lucide-check" :label="text.approve" @click="emit('approve', approvalId)" />
          <UButton
            color="neutral"
            variant="soft"
            icon="i-lucide-x"
            :label="text.reject"
            @click="emit('reject', approvalId)"
          />
        </div>
      </div>
    </div>
  </UCard>
</template>
