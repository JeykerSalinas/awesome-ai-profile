<script setup lang="ts">
import { isToolUIPart } from 'ai'

import CandidatePhotoCard from '@/components/chat/CandidatePhotoCard.vue'
import ToolApprovalCard from '@/components/chat/ToolApprovalCard.vue'
import type { ProfileMessage } from '@/types/chat'

defineProps<{ message: ProfileMessage }>()

const emit = defineEmits<{
  approve: [approvalId: string]
  reject: [approvalId: string]
}>()
</script>

<template>
  <div class="min-w-0 space-y-3">
    <template v-for="(part, index) in message.parts" :key="`${message.id}-${index}`">
      <p v-if="part.type === 'text'" class="whitespace-pre-wrap text-[15px] leading-7">
        {{ part.text }}
      </p>

      <CandidatePhotoCard
        v-else-if="part.type === 'data-candidate-photo'"
        :photo="part.data"
      />

      <div
        v-else-if="part.type === 'data-technologies'"
        class="rounded-2xl border border-stone-200 bg-white/80 p-4"
      >
        <p class="mb-3 text-sm font-medium text-stone-700">{{ part.data.label }}</p>
        <div class="flex flex-wrap gap-2">
          <UBadge
            v-for="technology in part.data.items"
            :key="technology"
            color="neutral"
            variant="soft"
          >
            {{ technology }}
          </UBadge>
        </div>
      </div>

      <UCard v-else-if="part.type === 'data-project'" class="max-w-lg">
        <p class="font-semibold text-stone-900">{{ part.data.title }}</p>
        <p class="mt-2 text-sm text-stone-600">{{ part.data.description }}</p>
        <div v-if="part.data.technologies?.length" class="mt-3 flex flex-wrap gap-2">
          <UBadge
            v-for="technology in part.data.technologies"
            :key="technology"
            color="primary"
            variant="subtle"
          >
            {{ technology }}
          </UBadge>
        </div>
        <UButton
          v-if="part.data.url"
          :to="part.data.url"
          target="_blank"
          variant="link"
          trailing-icon="i-lucide-arrow-up-right"
          class="mt-2 px-0"
          label="View project"
        />
      </UCard>

      <ToolApprovalCard
        v-else-if="isToolUIPart(part) && part.state === 'approval-requested'"
        :approval-id="part.approval.id"
        :tool-name="part.type === 'dynamic-tool' ? part.toolName : part.type.replace('tool-', '')"
        :input="part.input"
        @approve="emit('approve', $event)"
        @reject="emit('reject', $event)"
      />
    </template>
  </div>
</template>
