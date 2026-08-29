<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from "vue";

import { useLocale } from "@/composables/useLocale";

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{ accept: [] }>();
const dialog = ref<HTMLDialogElement | null>(null);
const { text } = useLocale();

async function syncDialog() {
  await nextTick();
  if (props.open && !dialog.value?.open) dialog.value?.showModal();
  if (!props.open && dialog.value?.open) dialog.value.close();
}

function acceptNotice() {
  emit("accept");
}

watch(() => props.open, syncDialog, { immediate: true });
onMounted(syncDialog);
</script>

<template>
  <Teleport to="body">
    <dialog
      ref="dialog"
      class="demo-notice m-auto max-h-[90dvh] w-[min(92vw,36rem)] overflow-y-auto rounded-[5px] border border-(--django-border) bg-(--django-surface) p-0 text-(--django-copy) shadow-2xl"
      aria-labelledby="demo-notice-title"
      aria-describedby="demo-notice-description"
      @cancel.prevent
    >
      <section class="p-6 sm:p-8">
        <div class="mb-5 flex items-start gap-4">
          <span
            class="grid size-11 shrink-0 place-items-center rounded-full bg-primary/10 text-primary"
            aria-hidden="true"
          >
            <UIcon name="i-lucide-shield-alert" class="size-5" />
          </span>
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
              {{ text.demoNoticeEyebrow }}
            </p>
            <h1
              id="demo-notice-title"
              class="mt-1 text-xl font-semibold text-(--django-heading)"
            >
              {{ text.demoNoticeTitle }}
            </h1>
          </div>
        </div>

        <div id="demo-notice-description" class="space-y-4 text-sm leading-6">
          <p>{{ text.demoNoticePurpose }}</p>
          <p>{{ text.demoNoticeLimits }}</p>
          <p>{{ text.demoNoticePrivacy }}</p>
          <p class="font-medium text-(--django-heading)">
            {{ text.demoNoticeWarning }}
          </p>
          <p class="text-xs text-(--django-muted)">
            {{ text.demoNoticeStorage }}
          </p>
        </div>

        <div class="mt-5 flex flex-wrap gap-x-4 gap-y-2 text-xs">
          <a
            href="https://ai.google.dev/gemini-api/terms"
            target="_blank"
            rel="noopener noreferrer"
            class="font-medium text-primary underline underline-offset-4"
          >
            {{ text.demoNoticeTerms }}
          </a>
          <a
            href="https://policies.google.com/privacy"
            target="_blank"
            rel="noopener noreferrer"
            class="font-medium text-primary underline underline-offset-4"
          >
            {{ text.demoNoticePrivacyPolicy }}
          </a>
        </div>

        <UButton
          autofocus
          block
          size="lg"
          color="primary"
          class="mt-7 justify-center"
          :label="text.demoNoticeAccept"
          @click="acceptNotice"
        />
      </section>
    </dialog>
  </Teleport>
</template>

<style scoped>
.demo-notice::backdrop {
  background: rgb(20 5 5 / 78%);
  backdrop-filter: blur(4px);
}
</style>
