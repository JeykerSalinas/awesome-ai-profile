<script setup lang="ts">
import { computed } from 'vue'
import { useLocale } from '@/composables/useLocale'
import { chapters, storyCopy } from '@/features/tour/story'

withDefaults(defineProps<{ variant?: 'invitation' | 'icon' }>(), {
  variant: 'invitation',
})
const emit = defineEmits<{ open: [] }>()
const { locale } = useLocale()
const copy = computed(() => storyCopy[locale.value])
const chapterCount = String(chapters.length).padStart(2, '0')
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
  <button v-else type="button" class="story-invitation" @click="emit('open')">
    <span class="story-invitation-icon" aria-hidden="true"
      ><UIcon name="i-lucide-route"
    /></span>
    <span class="story-invitation-copy">
      <span class="story-invitation-eyebrow"
        >{{ copy.eyebrow }}<span>01 — {{ chapterCount }}</span></span
      >
      <span class="story-invitation-title">{{ copy.launch }}</span>
      <span class="story-invitation-detail">{{ copy.teaser }}</span>
      <span class="story-invitation-duration"
        ><UIcon name="i-lucide-clock-3" />{{ copy.duration }}</span
      >
    </span>
    <UIcon name="i-lucide-arrow-up-right" class="story-invitation-arrow" />
  </button>
</template>

<style scoped>
.story-invitation {
  position: relative;
  display: flex;
  align-items: center;
  gap: 18px;
  width: 100%;
  margin-top: 28px;
  padding: 22px;
  overflow: hidden;
  border: 1px solid var(--django-border);
  border-radius: 14px;
  background: linear-gradient(
    120deg,
    var(--django-surface),
    var(--django-surface-soft)
  );
  text-align: left;
  cursor: pointer;
  transition:
    border-color 200ms,
    box-shadow 200ms,
    transform 200ms;
}
.story-invitation:hover {
  transform: translateY(-2px);
  border-color: var(--color-django-terracotta);
  box-shadow: 0 10px 30px rgb(50 8 8 / 10%);
}
.story-invitation:focus-visible {
  outline: 2px solid var(--color-django-terracotta);
  outline-offset: 4px;
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
  font-size: 18px;
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
.story-invitation-arrow {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  color: var(--django-heading);
  transition: transform 200ms;
}
.story-invitation:hover .story-invitation-arrow {
  transform: translate(2px, -2px);
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
    transition: none;
    transform: none;
  }
}
</style>
