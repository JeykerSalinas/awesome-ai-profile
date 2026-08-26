<script setup lang="ts">
import { computed, ref, useTemplateRef } from "vue";
import { useChat } from "@ai-sdk/vue";
import { useDark, useEventListener, useStorage } from "@vueuse/core";
import { DefaultChatTransport } from "ai";

import ChatMessageContent from "@/components/chat/ChatMessageContent.vue";
import TechnologyTourHost from "@/components/tour/TechnologyTourHost.vue";
import TechnologyTourLauncher from "@/components/tour/TechnologyTourLauncher.vue";
import { useLocale } from "@/composables/useLocale";
import { provideFeatureDiscovery } from "@/composables/useFeatureDiscovery";
import { provideContactFlow } from "@/composables/useContactFlow";
import type { ProfileMessage } from "@/types/chat";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const input = ref("");
const technologyTour =
  useTemplateRef<InstanceType<typeof TechnologyTourHost>>("technologyTour");
const fileInput = ref<HTMLInputElement | null>(null);
type ComposerDocument = {
  localId: string;
  filename: string;
  status: "uploading" | "ready" | "error";
  serverId?: string;
};

const composerDocument = ref<ComposerDocument | null>(null);
const pendingUpload = ref<Promise<void> | null>(null);
const requestDocumentIds = ref<string[]>([]);
const uploadError = ref("");
const isDark = useDark();
const hasSeenTour = useStorage("django-tour-seen", false);
const hasInteractedSinceLoad = ref(false);
const { locale, text } = useLocale();
// const messages = ref([{"parts":[{"type":"text","text":"Why should we hire Jeyker?"}],"id":"U3u32FLC4XP4T2T2","role":"user","metadata":"__vue_devtool_undefined__"},{"id":"assistant-aea52d36459942af8fefb122effb93a0","metadata":"__vue_devtool_undefined__","role":"assistant","parts":[{"type":"step-start"},{"type":"data-source","id":"source-b66cf3d921e74cf8b19eb2d03ab0a2dc","data":{"path":"knowledge/profile.json"}},{"type":"text","text":"Jeyker Salinas is a Software Engineer who specializes in building high-quality, product-oriented applications. You should consider him for your team because he brings a unique combination of expertise that bridges modern web development and practical Artificial Intelligence.\n\nHere are the key reasons why Jeyker is a strong candidate:\n\n*   **Frontend Expertise:** He has a deep focus on frontend engineering, specifically using **Vue.js** and **TypeScript** to create scalable and maintainable architectures.\n*   **AI & RAG Integration:** Jeyker is highly proficient in developing conversational interfaces for Large Language Models (LLMs) and implementing **Retrieval-Augmented Generation (RAG)** applications.\n*   **Full-Stack Capability:** He is experienced in backend integration, particularly with **Python and FastAPI**, allowing him to work effectively across the stack.\n*   **Product Mindset:** He is not just focused on writing code; he is committed to delivering software that is user-focused and aligned with product goals.\n\nIf you are looking for an engineer who can translate complex AI capabilities into intuitive, reliable web interfaces, Jeyker would be a valuable addition to your project.","providerMetadata":"__vue_devtool_undefined__","state":"done"}]}])
const suggestionIcons = [
  "i-lucide-sparkles",
  "i-lucide-brain-circuit",
  "i-lucide-camera",
];
const suggestions = computed(() =>
  text.value.suggestions.map((label, index) => ({
    icon: suggestionIcons[index] ?? "i-lucide-message-circle",
    label,
  }))
);
const shouldPulseTourLauncher = computed(
  () => !hasSeenTour.value && !hasInteractedSinceLoad.value
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
      documents: requestDocumentIds.value,
    }),
  }),
});

provideFeatureDiscovery(messages);
provideContactFlow(messages, apiBaseUrl);
const hasMessages = computed(() => messages.value.length > 0);
const isUploading = computed(
  () => composerDocument.value?.status === "uploading"
);

async function deleteUploadedDocument(documentId: string) {
  try {
    await fetch(`${apiBaseUrl}/documents/${encodeURIComponent(documentId)}`, {
      method: "DELETE",
    });
  } catch {
    // Ignore cleanup errors for temporary uploads.
  }
}

async function submitMessage(event: Event) {
  event.preventDefault();
  const messageText = input.value.trim();
  if (
    !messageText ||
    status.value === "streaming" ||
    status.value === "submitted"
  )
    return;

  if (pendingUpload.value) {
    await pendingUpload.value;
  }

  if (composerDocument.value?.status === "error") return;

  const activeDocument = composerDocument.value;
  requestDocumentIds.value =
    activeDocument?.status === "ready" && activeDocument.serverId
      ? [activeDocument.serverId]
      : [];

  const messageParts: ProfileMessage["parts"] = [
    { type: "text", text: messageText },
  ];
  if (activeDocument?.status === "ready") {
    messageParts.unshift({
      type: "data-user-document",
      data: { filename: activeDocument.filename },
    });
  }

  input.value = "";
  composerDocument.value = null;
  uploadError.value = "";

  try {
    await sendMessage({ parts: messageParts });
  } finally {
    requestDocumentIds.value = [];
  }
}

function sendSuggestion(text: string) {
  if (status.value === "ready" || status.value === "error")
    void sendMessage({ text });
}

function stopTourPulse() {
  hasInteractedSinceLoad.value = true;
}

function markTourAsSeen() {
  hasSeenTour.value = true;
  stopTourPulse();
}

function respondToApproval(approvalId: string, approved: boolean) {
  void addToolApprovalResponse({ id: approvalId, approved });
}

async function uploadDocument(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  const previousDocument = composerDocument.value;
  if (previousDocument?.status === "ready" && previousDocument.serverId) {
    void deleteUploadedDocument(previousDocument.serverId);
  }

  const localId = crypto.randomUUID();
  composerDocument.value = {
    localId,
    filename: file.name,
    status: "uploading",
  };
  uploadError.value = "";

  const uploadTask = (async () => {
    const payload = new FormData();
    payload.append("file", file);
    payload.append("document_type", "other");
    const response = await fetch(`${apiBaseUrl}/documents`, {
      method: "POST",
      body: payload,
    });
    const result = await response.json();
    if (!response.ok)
      throw new Error(result.detail || text.value.documentUploadError);

    if (composerDocument.value?.localId !== localId) {
      await deleteUploadedDocument(result.id);
      return;
    }

    composerDocument.value = {
      localId,
      filename: result.filename,
      status: "ready",
      serverId: result.id,
    };
  })()
    .catch(async (cause) => {
      if (composerDocument.value?.localId === localId) {
        composerDocument.value = {
          localId,
          filename: file.name,
          status: "error",
        };
        uploadError.value =
          cause instanceof Error
            ? cause.message
            : text.value.documentUploadError;
      }
    })
    .finally(() => {
      if (pendingUpload.value === uploadTask) {
        pendingUpload.value = null;
      }
      target.value = "";
    });

  pendingUpload.value = uploadTask;
  await uploadTask;
}

function removeDocument(documentId: string) {
  if (composerDocument.value?.serverId === documentId) {
    composerDocument.value = null;
    uploadError.value = "";
    void deleteUploadedDocument(documentId);
  }
}

function removeComposerDocument() {
  const documentId = composerDocument.value?.serverId;
  composerDocument.value = null;
  uploadError.value = "";
  if (documentId) void deleteUploadedDocument(documentId);
}

useEventListener(window, "pointerdown", stopTourPulse, { passive: true });
useEventListener(window, "keydown", stopTourPulse);
</script>

<template>
  <main class="min-h-dvh px-3 py-3 sm:px-6 sm:py-5">
    <section
      class="mx-auto flex min-h-[calc(100dvh-1.5rem)] max-w-6xl max-h-1 flex-col overflow-hidden rounded-[5px] border border-(--django-border) bg-(--django-surface) shadow-[0_28px_100px_-45px_rgba(50,8,8,0.35)] transition-colors sm:min-h-[calc(100dvh-2.5rem)]"
    >
      <header
        class="flex items-center justify-between gap-3 border-b border-(--django-border) px-5 py-4 sm:px-8"
      >
        <div data-tour="identity" class="flex min-w-0 items-center gap-3">
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
            <p class="hidden text-xs text-(--django-muted) sm:block">
              {{ text.assistantDescription }}
            </p>
          </div>
        </div>
        <div data-tour="preferences" class="flex items-center gap-2 sm:gap-3">
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
          <TechnologyTourLauncher
            variant="icon"
            @open="technologyTour?.openTour()"
          />
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
          class="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center px-6 py-6 text-center sm:px-10"
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
          <div
            data-tour="conversation"
            class="mt-6 grid gap-3 text-left sm:grid-cols-2"
          >
            <TechnologyTourLauncher
              :pulse="shouldPulseTourLauncher"
              :seen="hasSeenTour"
              @open="technologyTour?.openTour()"
            />
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
          data-tour="conversation"
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
                :active="
                  (status === 'streaming' || status === 'submitted') &&
                  (message as ProfileMessage).id === messages[messages.length - 1]?.id
                "
                :hide-resources="
                  status === 'streaming' &&
                  (message as ProfileMessage).role === 'assistant' &&
                  (message as ProfileMessage).id === messages[messages.length - 1]?.id
                "
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
          <div v-if="composerDocument" class="mb-3 flex flex-wrap gap-2">
            <UBadge
              :key="composerDocument.localId"
              color="primary"
              variant="subtle"
              class="gap-1.5 rounded-full px-3 py-1.5"
              :title="
                composerDocument.status === 'uploading'
                  ? text.uploadingDocument
                  : text.uploadedDocument
              "
            >
              <UIcon
                :name="
                  composerDocument.status === 'uploading'
                    ? 'i-lucide-loader-circle'
                    : composerDocument.status === 'error'
                    ? 'i-lucide-file-warning'
                    : 'i-lucide-file-text'
                "
                class="size-3.5"
                :class="{
                  'animate-spin': composerDocument.status === 'uploading',
                }"
              />
              <span class="max-w-44 truncate">{{
                composerDocument.filename
              }}</span>
              <button
                type="button"
                :aria-label="text.removeDocument"
                class="grid size-4 place-items-center rounded-full hover:bg-black/10"
                @click="
                  composerDocument.serverId
                    ? removeDocument(composerDocument.serverId)
                    : removeComposerDocument()
                "
              >
                <UIcon name="i-lucide-x" class="size-3" />
              </button>
            </UBadge>
          </div>
          <input
            ref="fileInput"
            type="file"
            accept="application/pdf,.pdf"
            class="hidden"
            @change="uploadDocument"
          />
          <UChatPrompt
            data-tour="composer"
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
                {{ isUploading ? text.uploadingDocument : text.poweredBy }}
              </span>
              <div class="flex items-center gap-1">
                <UButton
                  data-tour="upload"
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
          <p
            data-tour="stack"
            class="mt-3 text-center text-xs text-(--django-muted)"
          >
            {{ text.builtWith }}
          </p>
        </div>
      </div>
    </section>
    <TechnologyTourHost
      ref="technologyTour"
      v-model:draft="input"
      @opened="markTourAsSeen"
    />
  </main>
</template>
