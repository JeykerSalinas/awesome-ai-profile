<script setup lang="ts">
import { computed } from "vue";
import { useLocale } from "@/composables/useLocale";
import { storyCopy } from "@/features/tour/story";

const props = withDefaults(
  defineProps<{
    variant?: "invitation" | "icon";
    pulse?: boolean;
    seen?: boolean;
  }>(),
  {
    variant: "invitation",
    pulse: false,
    seen: false,
  }
);
const emit = defineEmits<{ open: [] }>();
const { locale } = useLocale();
const copy = computed(() => storyCopy[locale.value]);
</script>

<template>
  <UButton
    v-if="variant === 'icon'"
    icon="i-lucide-route"
    :aria-label="copy.launch"
    :title="copy.launch"
    color="neutral"
    variant="ghost"
    class="rounded-full text-(--django-copy)"
    @click="emit('open')"
  />

  <button
    v-else
    type="button"
    class="story-invitation relative group flex items-center gap-3 rounded-[5px] border border-(--django-border) bg-(--django-surface) px-4 py-4 text-sm text-(--django-copy) transition hover:border-primary hover:bg-(--django-surface-soft)"
    :class="{
      'story-invitation--pulsing': props.pulse,
      'story-invitation--seen': props.seen,
    }"
    @click="emit('open')"
  >
    <UIcon
      name="i-lucide-route"
      class="size-5 shrink-0 text-(--django-muted) transition group-hover:text-primary"
    />

    <span class="story-invitation-title">{{ copy.launch }}</span>
  </button>
</template>

<style scoped>
.story-invitation {
  animation: none;
}
.story-invitation--pulsing {
  animation: story-invitation-pulse 2.4s ease-in-out infinite;
}
.story-invitation--seen .story-invitation-title {
  font-weight: 400;
  letter-spacing: 0;
  color: var(--django-copy);
}
.story-invitation-icon {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 48px;
  height: 58px;
  border: 1px solid var(--django-border);
  border-radius: 24px 24px 10px 10px;
  color: var(--django-heading);
  background: var(--django-surface);
}
.story-invitation-icon > * {
  width: 23px;
  height: 23px;
}
.story-invitation-copy {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  gap: 7px;
}
.story-invitation-eyebrow {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  font-size: 9px;
  font-weight: 750;
  letter-spacing: 0.14em;
  color: var(--django-muted);
}
.story-invitation-eyebrow > span {
  font-family: ui-monospace, monospace;
  font-weight: 400;
}
.story-invitation-title {
  font-size: 14px;
  font-weight: 650;
  letter-spacing: -0.025em;
  color: var(--django-heading);
}
.story-invitation-detail {
  font-size: 12px;
  line-height: 1.6;
  color: var(--django-copy);
}
.story-invitation-duration {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  color: var(--django-muted);
}

@keyframes story-invitation-pulse {
  0%,
  100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgb(229 109 88 / 0);
  }
  50% {
    transform: scale(1.015);
    box-shadow: 0 0 0 8px rgb(229 109 88 / 0.08);
  }
}
@media (max-width: 420px) {
  .story-invitation {
    padding: 16px;
    gap: 12px;
  }
  .story-invitation-icon {
    display: none;
  }
  .story-invitation-title {
    font-size: 16px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .story-invitation,
  .story-invitation-arrow {
    animation: none;
    transition: none;
    transform: none;
  }
}
</style>
