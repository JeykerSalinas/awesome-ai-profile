<script setup lang="ts">
import { computed, ref, useId } from 'vue'
import { useLocale } from '@/composables/useLocale'
import { features, featureSourceUrl, insightCopy, type FeatureId } from '@/features/insights/catalog'

const props = defineProps<{ feature: FeatureId }>()
const { locale } = useLocale()
const open = ref(false)
const id = useId()
const definition = computed(() => features[props.feature])
const content = computed(() => definition.value[locale.value])
const copy = computed(() => insightCopy[locale.value])
</script>

<template>
  <article class="feature-explainer">
    <button :id="`${id}-button`" type="button" class="feature-button" :aria-expanded="open" :aria-controls="`${id}-content`" @click="open = !open">
      <UIcon :name="definition.icon" class="size-4 shrink-0 text-primary" />
      <span class="min-w-0 flex-1 text-left">
        <span class="block text-xs font-semibold text-(--django-heading)">{{ content.title }}</span>
        <span class="block text-xs text-(--django-muted)">{{ copy.why }}</span>
      </span>
      <UIcon :name="open ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'" class="size-4 shrink-0" />
    </button>
    <div v-show="open" :id="`${id}-content`" role="region" :aria-labelledby="`${id}-button`" class="feature-content">
      <p>{{ content.why }}</p>
      <h4>{{ copy.how }}</h4>
      <p>{{ content.how }}</p>
      <ol class="feature-flow">
        <li v-for="(step, index) in content.flow" :key="index">
          <span class="feature-step">{{ index + 1 }}</span>{{ step }}
        </li>
      </ol>
      <div class="flex flex-wrap gap-1.5">
        <UBadge v-for="technology in definition.technologies" :key="technology" color="neutral" variant="subtle" size="sm">{{ technology }}</UBadge>
      </div>
      <h4>{{ copy.caveat }}</h4>
      <p class="text-(--django-muted)">{{ content.caveat }}</p>
      <a :href="featureSourceUrl(feature)" target="_blank" rel="noopener noreferrer" class="feature-source">
        {{ copy.code }} <UIcon name="i-lucide-arrow-up-right" class="size-3.5" />
      </a>
    </div>
  </article>
</template>

<style scoped>
.feature-explainer { border: 1px solid var(--django-border); border-radius: 5px; background: var(--django-surface); color: var(--django-copy); }
.feature-button { display: flex; align-items: center; gap: 0.625rem; width: 100%; padding: 0.75rem; cursor: pointer; border-radius: 5px; }
.feature-button:hover { background: var(--django-surface-soft); }
.feature-button:focus-visible, .feature-source:focus-visible { outline: 2px solid var(--ui-primary); outline-offset: 3px; }
.feature-content { border-top: 1px solid var(--django-border); padding: 1rem; font-size: 0.8125rem; line-height: 1.7; overflow-wrap: anywhere; }
.feature-content h4 { margin-top: 0.875rem; margin-bottom: 0.25rem; color: var(--django-heading); font-weight: 600; }
.feature-flow { display: grid; gap: 0.5rem; margin: 1rem 0; }
.feature-flow li { display: flex; align-items: center; gap: 0.5rem; }
.feature-step { display: grid; place-items: center; width: 1.25rem; height: 1.25rem; flex-shrink: 0; background: var(--django-surface-soft); border-radius: 50%; color: var(--ui-primary); font-size: 0.7rem; font-weight: 600; }
.feature-source { display: inline-flex; align-items: center; gap: 0.25rem; margin-top: 0.875rem; color: var(--ui-primary); text-decoration: underline; text-underline-offset: 3px; }
</style>
