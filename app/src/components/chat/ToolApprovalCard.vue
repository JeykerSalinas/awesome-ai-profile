<script setup lang="ts">
defineProps<{
  approvalId: string
  toolName: string
  input: unknown
}>()

const emit = defineEmits<{
  approve: [approvalId: string]
  reject: [approvalId: string]
}>()
</script>

<template>
  <UCard class="my-4 max-w-lg border border-amber-200 bg-amber-50/70">
    <div class="flex gap-3">
      <UIcon name="i-lucide-shield-question" class="mt-0.5 size-5 shrink-0 text-amber-600" />
      <div class="min-w-0 flex-1 space-y-3">
        <div>
          <p class="text-sm font-semibold text-stone-900">Your approval is required</p>
          <p class="mt-1 text-sm text-stone-600">
            The assistant wants to run <strong>{{ toolName }}</strong>.
          </p>
        </div>
        <pre
          v-if="input && typeof input === 'object'"
          class="overflow-x-auto rounded-xl bg-white p-3 text-xs text-stone-600"
        >{{ JSON.stringify(input, null, 2) }}</pre>
        <div class="flex flex-wrap gap-2">
          <UButton icon="i-lucide-check" label="Approve" @click="emit('approve', approvalId)" />
          <UButton
            color="neutral"
            variant="soft"
            icon="i-lucide-x"
            label="Reject"
            @click="emit('reject', approvalId)"
          />
        </div>
      </div>
    </div>
  </UCard>
</template>
