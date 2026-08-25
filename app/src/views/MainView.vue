<script setup lang="ts">
import { computed, ref } from 'vue'
import { useChat } from '@ai-sdk/vue'
import { DefaultChatTransport } from 'ai'

import ChatMessageContent from '@/components/chat/ChatMessageContent.vue'
import type { ProfileMessage } from '@/types/chat'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
const input = ref('')

const suggestions = [
  { icon: 'i-lucide-sparkles', label: 'Why should we hire Jeyker?' },
  { icon: 'i-lucide-braces', label: 'What has he built with Vue and TypeScript?' },
  { icon: 'i-lucide-brain-circuit', label: 'Tell me about his AI experience.' },
  { icon: 'i-lucide-camera', label: 'Show me a picture of Jeyker.' },
]

const {
  messages,
  status,
  error,
  sendMessage,
  regenerate,
  stop,
  addToolApprovalResponse,
} = useChat<ProfileMessage>({
  transport: new DefaultChatTransport<ProfileMessage>({
    api: `${apiBaseUrl}/chat/stream`,
  }),
})

const hasMessages = computed(() => messages.value.length > 0)

function submitMessage(event: Event) {
  event.preventDefault()
  const text = input.value.trim()
  if (!text || status.value === 'streaming' || status.value === 'submitted') return

  input.value = ''
  void sendMessage({ text })
}

function sendSuggestion(text: string) {
  if (status.value === 'ready' || status.value === 'error') void sendMessage({ text })
}

function respondToApproval(approvalId: string, approved: boolean) {
  void addToolApprovalResponse({ id: approvalId, approved })
}
</script>

<template>
  <main class="min-h-dvh px-3 py-3 sm:px-6 sm:py-5">
    <section
      class="mx-auto flex min-h-[calc(100dvh-1.5rem)] max-w-6xl flex-col overflow-hidden rounded-[2rem] border border-stone-200/80 bg-white/75 shadow-[0_28px_100px_-45px_rgba(50,8,8,0.35)] backdrop-blur sm:min-h-[calc(100dvh-2.5rem)]"
    >
      <header class="flex items-center justify-between border-b border-stone-200/80 px-5 py-4 sm:px-8">
        <div class="flex min-w-0 items-center gap-3">
          <img
            src="/django_design/django-app-icon-dark.svg"
            alt="Django, Jeyker's AI assistant"
            class="size-11 rounded-2xl"
          />
          <div>
            <p class="text-sm font-semibold tracking-tight text-stone-900">Django AI</p>
            <p class="text-xs text-stone-500">Jeyker's professional sidekick</p>
          </div>
        </div>
        <UBadge color="success" variant="subtle" class="rounded-full px-3 py-1">
          <span class="mr-1.5 inline-block size-1.5 rounded-full bg-green-500" />
          Available for work
        </UBadge>
      </header>

      <div class="relative flex min-h-0 flex-1 flex-col">
        <div
          v-if="!hasMessages"
          class="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center px-6 py-14 text-center sm:px-10"
        >
          <div class="mx-auto mb-7 grid size-20 place-items-center rounded-[1.75rem] bg-[#fbefce]">
            <img src="/django_design/django-app-icon-dark.svg" alt="Django" class="size-14" />
          </div>
          <UBadge color="primary" variant="subtle" class="mx-auto mb-4 rounded-full px-3 py-1">
            Interactive AI portfolio
          </UBadge>
          <h1 class="text-balance text-4xl font-semibold tracking-tight text-stone-900 sm:text-5xl">
            Meet Jeyker, <span class="text-primary">through Django.</span>
          </h1>
          <p class="mx-auto mt-5 max-w-xl text-pretty text-base leading-7 text-stone-600">
            Ask anything about his engineering experience, AI projects, favorite technologies,
            or why this résumé has its own canine assistant.
          </p>
          <div class="mt-10 grid gap-3 text-left sm:grid-cols-2">
            <button
              v-for="suggestion in suggestions"
              :key="suggestion.label"
              type="button"
              class="group flex items-center gap-3 rounded-2xl border border-stone-200 bg-white/80 px-4 py-4 text-sm text-stone-700 transition hover:border-red-200 hover:bg-red-50/50"
              @click="sendSuggestion(suggestion.label)"
            >
              <UIcon
                :name="suggestion.icon"
                class="size-5 shrink-0 text-stone-400 transition group-hover:text-primary"
              />
              <span>{{ suggestion.label }}</span>
            </button>
          </div>
        </div>

        <UContainer v-else class="flex w-full max-w-4xl flex-1 flex-col px-4 py-5 sm:px-8">
          <UChatMessages
            :messages="messages"
            :status="status"
            :assistant="{ avatar: { src: '/django_design/django-app-icon-dark.svg', alt: 'Django' } }"
            should-auto-scroll
            class="flex-1"
          >
            <template #content="{ message }">
              <ChatMessageContent
                :message="message as ProfileMessage"
                @approve="respondToApproval($event, true)"
                @reject="respondToApproval($event, false)"
              />
            </template>
            <template #indicator>
              <div class="flex items-center gap-2 text-stone-500">
                <UIcon name="i-lucide-loader-circle" class="size-4 animate-spin text-primary" />
                <UChatShimmer text="Django is thinking..." class="text-sm" />
              </div>
            </template>
          </UChatMessages>
        </UContainer>

        <div class="sticky bottom-0 mx-auto w-full max-w-4xl px-4 pb-4 pt-2 sm:px-8 sm:pb-6">
          <UAlert
            v-if="error"
            color="error"
            variant="soft"
            icon="i-lucide-circle-alert"
            :description="error.message"
            class="mb-3"
          />
          <UChatPrompt
            v-model="input"
            :error="error"
            placeholder="Ask Django about Jeyker..."
            color="neutral"
            variant="subtle"
            class="rounded-3xl border border-stone-200 bg-white shadow-lg shadow-stone-200/40"
            @submit="submitMessage"
          >
            <template #footer>
              <span class="flex items-center gap-1.5 text-xs text-stone-500">
                <UIcon name="i-lucide-sparkles" class="size-3.5 text-primary" />
                Powered by Gemini & LangChain
              </span>
              <UChatPromptSubmit
                :status="status"
                color="primary"
                size="sm"
                @stop="stop()"
                @reload="regenerate()"
              />
            </template>
          </UChatPrompt>
          <p class="mt-3 text-center text-xs text-stone-400">
            Built with Vue 3, Nuxt UI, FastAPI and the AI SDK.
          </p>
        </div>
      </div>
    </section>
  </main>
</template>
