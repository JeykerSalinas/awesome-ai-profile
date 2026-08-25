<script setup lang="ts">
import { computed, ref } from "vue";
import { useChat } from "@ai-sdk/vue";
import { useDark } from "@vueuse/core";
import { DefaultChatTransport } from "ai";

import ChatMessageContent from "@/components/chat/ChatMessageContent.vue";
import { useLocale } from "@/composables/useLocale";
import type { ProfileMessage } from "@/types/chat";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const input = ref("");
const isDark = useDark();
const { locale, text } = useLocale();

const suggestionIcons = [
  "i-lucide-sparkles",
  "i-lucide-braces",
  "i-lucide-brain-circuit",
  "i-lucide-camera",
];
const suggestions = computed(() =>
  text.value.suggestions.map((label, index) => ({
    icon: suggestionIcons[index] ?? "i-lucide-message-circle",
    label,
  }))
);

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
    body: () => ({ locale: locale.value }),
  }),
});

const hasMessages = computed(() => messages.value.length > 0);

function submitMessage(event: Event) {
  event.preventDefault();
  const text = input.value.trim();
  if (!text || status.value === "streaming" || status.value === "submitted")
    return;

  input.value = "";
  void sendMessage({ text });
}

function sendSuggestion(text: string) {
  if (status.value === "ready" || status.value === "error")
    void sendMessage({ text });
}

function respondToApproval(approvalId: string, approved: boolean) {
  void addToolApprovalResponse({ id: approvalId, approved });
}
</script>

<template>
  <main class="min-h-dvh px-3 py-3 sm:px-6 sm:py-5">
    <section
      class="mx-auto flex min-h-[calc(100dvh-1.5rem)] max-w-6xl flex-col overflow-hidden rounded-[5px] border border-(--django-border) bg-(--django-surface) shadow-[0_28px_100px_-45px_rgba(50,8,8,0.35)] transition-colors sm:min-h-[calc(100dvh-2.5rem)]"
    >
      <header
        class="flex items-center justify-between gap-3 border-b border-(--django-border) px-5 py-4 sm:px-8"
      >
        <div class="flex min-w-0 items-center gap-3">
          <img
            src="/django_design/django-app-icon-dark.svg"
            alt="Django, Jeyker's AI assistant"
            class="size-11 rounded-[5px]"
          />
          <div>
            <p
              class="text-sm font-semibold tracking-tight text-(--django-heading)"
            >
              Django AI
            </p>
            <p class="text-xs text-(--django-muted)">
              {{ text.assistantDescription }}
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2 sm:gap-3">
          <UBadge
            color="success"
            variant="subtle"
            class="hidden rounded-full px-3 py-1 sm:inline-flex"
          >
            <span
              class="mr-1.5 inline-block size-1.5 rounded-full bg-green-500"
            />
            {{ text.availableForWork }}
          </UBadge>
          <UButton
            icon="i-lucide-languages"
            :label="locale.toUpperCase()"
            :aria-label="text.switchLanguage"
            :title="text.switchLanguage"
            color="neutral"
            variant="ghost"
            class="rounded-full text-(--django-copy)"
            @click="locale = locale === 'es' ? 'en' : 'es'"
          />
          <UButton
            :icon="isDark ? 'i-lucide-sun' : 'i-lucide-moon'"
            :aria-label="isDark ? text.lightMode : text.darkMode"
            :title="isDark ? text.lightMode : text.darkMode"
            color="neutral"
            variant="ghost"
            class="rounded-full text-(--django-copy)"
            @click="isDark = !isDark"
          />
        </div>
      </header>

      <div class="relative flex min-h-0 flex-1 flex-col">
        <div
          v-if="!hasMessages"
          class="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center px-6 py-14 text-center sm:px-10"
        >
          <div
            class="mx-auto mb-7 grid size-20 place-items-center rounded-[1.75rem] bg-(--django-surface-soft)"
          >
            <img
              src="/django_design/django-app-icon-dark.svg"
              alt="Django"
              class="size-14"
            />
          </div>
          <UBadge
            color="primary"
            variant="subtle"
            class="mx-auto mb-4 rounded-full px-3 py-1"
          >
            {{ text.portfolioBadge }}
          </UBadge>
          <h1
            class="text-balance text-4xl font-semibold tracking-tight text-(--django-heading) sm:text-5xl"
          >
            {{ text.greeting }}
            <span class="text-primary">{{ text.greetingHighlight }}</span>
          </h1>
          <p
            class="mx-auto mt-5 max-w-xl text-pretty text-base leading-7 text-(--django-copy)"
          >
            {{ text.introduction }}
          </p>
          <div class="mt-10 grid gap-3 text-left sm:grid-cols-2">
            <button
              v-for="suggestion in suggestions"
              :key="suggestion.label"
              type="button"
              class="group flex items-center gap-3 rounded-[5px] border border-(--django-border) bg-(--django-surface) px-4 py-4 text-sm text-(--django-copy) transition hover:border-primary hover:bg-(--django-surface-soft)"
              @click="sendSuggestion(suggestion.label)"
            >
              <UIcon
                :name="suggestion.icon"
                class="size-5 shrink-0 text-(--django-muted) transition group-hover:text-primary"
              />
              <span>{{ suggestion.label }}</span>
            </button>
          </div>
        </div>

        <UContainer
          v-else
          class="flex w-full max-w-4xl flex-1 flex-col px-4 py-5 sm:px-8"
        >
          <UChatMessages
            :messages="messages"
            :status="status"
            :assistant="{
              avatar: {
                src: '/django_design/django-app-icon-dark.svg',
                alt: 'Django',
              },
            }"
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
              <div class="flex items-center gap-2 text-(--django-muted)">
                <UIcon
                  name="i-lucide-loader-circle"
                  class="size-4 animate-spin text-primary"
                />
                <UChatShimmer :text="text.thinking" class="text-sm" />
              </div>
            </template>
          </UChatMessages>
        </UContainer>

        <div
          class="sticky bottom-0 mx-auto w-full max-w-4xl px-4 pb-4 pt-2 sm:px-8 sm:pb-6"
        >
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
            :placeholder="text.placeholder"
            color="neutral"
            variant="subtle"
            class="rounded-[5px] border border-(--django-border) bg-(--django-surface) shadow-lg shadow-black/10"
            @submit="submitMessage"
          >
            <template #footer>
              <span
                class="flex items-center gap-1.5 text-xs text-(--django-muted)"
              >
                <UIcon name="i-lucide-sparkles" class="size-3.5 text-primary" />
                {{ text.poweredBy }}
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
          <p class="mt-3 text-center text-xs text-(--django-muted)">
            {{ text.builtWith }}
          </p>
        </div>
      </div>
    </section>
  </main>
</template>
