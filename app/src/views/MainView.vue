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
const fileInput = ref<HTMLInputElement | null>(null);
const uploadedDocuments = ref<Array<{ id: string; filename: string }>>([]);
const isUploading = ref(false);
const uploadError = ref("");
const isDark = useDark();
const { locale, text } = useLocale();
// const messages = ref([{"parts":[{"type":"text","text":"Why should we hire Jeyker?"}],"id":"U3u32FLC4XP4T2T2","role":"user","metadata":"__vue_devtool_undefined__"},{"id":"assistant-aea52d36459942af8fefb122effb93a0","metadata":"__vue_devtool_undefined__","role":"assistant","parts":[{"type":"step-start"},{"type":"data-source","id":"source-b66cf3d921e74cf8b19eb2d03ab0a2dc","data":{"path":"knowledge/profile.json"}},{"type":"text","text":"Jeyker Salinas is a Software Engineer who specializes in building high-quality, product-oriented applications. You should consider him for your team because he brings a unique combination of expertise that bridges modern web development and practical Artificial Intelligence.\n\nHere are the key reasons why Jeyker is a strong candidate:\n\n*   **Frontend Expertise:** He has a deep focus on frontend engineering, specifically using **Vue.js** and **TypeScript** to create scalable and maintainable architectures.\n*   **AI & RAG Integration:** Jeyker is highly proficient in developing conversational interfaces for Large Language Models (LLMs) and implementing **Retrieval-Augmented Generation (RAG)** applications.\n*   **Full-Stack Capability:** He is experienced in backend integration, particularly with **Python and FastAPI**, allowing him to work effectively across the stack.\n*   **Product Mindset:** He is not just focused on writing code; he is committed to delivering software that is user-focused and aligned with product goals.\n\nIf you are looking for an engineer who can translate complex AI capabilities into intuitive, reliable web interfaces, Jeyker would be a valuable addition to your project.","providerMetadata":"__vue_devtool_undefined__","state":"done"}]}])
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
    body: () => ({
      locale: locale.value,
      documents: uploadedDocuments.value.map((document) => document.id),
    }),
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

async function uploadDocument(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  isUploading.value = true;
  uploadError.value = "";

  try {
    const payload = new FormData();
    payload.append("file", file);
    payload.append("document_type", "other");
    const response = await fetch(`${apiBaseUrl}/documents`, {
      method: "POST",
      body: payload,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || text.value.documentUploadError);
    uploadedDocuments.value.push({ id: result.id, filename: result.filename });
  } catch (cause) {
    uploadError.value = cause instanceof Error ? cause.message : text.value.documentUploadError;
  } finally {
    isUploading.value = false;
    target.value = "";
  }
}

function removeDocument(documentId: string) {
  uploadedDocuments.value = uploadedDocuments.value.filter((document) => document.id !== documentId);
  void fetch(`${apiBaseUrl}/documents/${encodeURIComponent(documentId)}`, {
    method: "DELETE",
  }).catch(() => undefined);
}
</script>

<template>
  <main class="min-h-dvh px-3 py-3 sm:px-6 sm:py-5">
    <section
      class="mx-auto flex min-h-[calc(100dvh-1.5rem)] max-w-6xl max-h-1 flex-col overflow-hidden rounded-[5px] border border-(--django-border) bg-(--django-surface) shadow-[0_28px_100px_-45px_rgba(50,8,8,0.35)] transition-colors sm:min-h-[calc(100dvh-2.5rem)]"
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

      <div class="relative flex min-h-0 flex-1 flex-col overflow-auto">
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
          class="sticky bottom-0 z-10 mx-auto w-full max-w-4xl bg-linear-to-b from-(--django-surface) via-(--django-surface)/50 to-(--django-surface)/0 px-4 pb-2 pt-6 backdrop-blur-[3px] sm:px-8 sm:pb-2"
        >
          <UAlert
            v-if="error"
            color="error"
            variant="soft"
            icon="i-lucide-circle-alert"
            :description="error.message"
            class="mb-3"
          />
          <UAlert
            v-if="uploadError"
            color="error"
            variant="soft"
            icon="i-lucide-file-warning"
            :description="uploadError"
            class="mb-3"
          />
          <div v-if="uploadedDocuments.length" class="mb-3 flex flex-wrap gap-2">
            <UBadge
              v-for="document in uploadedDocuments"
              :key="document.id"
              color="primary"
              variant="subtle"
              class="gap-1.5 rounded-full px-3 py-1.5"
              :title="text.uploadedDocument"
            >
              <UIcon name="i-lucide-file-text" class="size-3.5" />
              <span class="max-w-44 truncate">{{ document.filename }}</span>
              <button
                type="button"
                :aria-label="text.removeDocument"
                class="grid size-4 place-items-center rounded-full hover:bg-black/10"
                @click="removeDocument(document.id)"
              >
                <UIcon name="i-lucide-x" class="size-3" />
              </button>
            </UBadge>
          </div>
          <input ref="fileInput" type="file" accept="application/pdf,.pdf" class="hidden" @change="uploadDocument" />
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
              <span class="flex items-center gap-1.5 text-xs text-(--django-muted)">
                <UIcon name="i-lucide-sparkles" class="size-3.5 text-primary" />
                {{ isUploading ? text.uploadingDocument : text.poweredBy }}
              </span>
              <div class="flex items-center gap-1">
                <UButton
                  icon="i-lucide-paperclip"
                  type="button"
                  :aria-label="text.uploadDocument"
                  :title="text.uploadDocument"
                  :loading="isUploading"
                  color="neutral"
                  variant="ghost"
                  size="sm"
                  @click="fileInput?.click()"
                />
                <UChatPromptSubmit
                  :status="status"
                  color="primary"
                  size="sm"
                  @stop="stop()"
                  @reload="regenerate()"
                />
              </div>
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
