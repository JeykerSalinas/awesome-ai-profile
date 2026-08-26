<script setup lang="ts">
import { computed } from 'vue'
import { useLocale } from '@/composables/useLocale'
import { activityStatus, messageActivities } from '@/features/insights/activity'
import { insightCopy, features, toolFeatures } from '@/features/insights/catalog'
import type { AgentActivityData, ProfileMessage } from '@/types/chat'

const props = defineProps<{ message: ProfileMessage; active: boolean }>()
const { locale } = useLocale()
const copy = computed(() => insightCopy[locale.value])
const activities = computed(() => messageActivities(props.message))
const current = computed(() => [...activities.value].reverse().find(item => item.status === 'running') ?? activities.value.at(-1))
const hasTools = computed(() => activities.value.some(item => item.kind === 'tool'))
const icons = {
  running: 'i-lucide-loader-circle', completed: 'i-lucide-check',
  error: 'i-lucide-circle-alert', interrupted: 'i-lucide-circle-pause',
}
function label(activity: AgentActivityData) {
  const feature = activity.tool_name ? toolFeatures[activity.tool_name] : undefined
  return feature ? features[feature][locale.value].title : copy.value.model
}
function state(activity: AgentActivityData) {
  return activityStatus(activity, props.active)
}
</script>

<template>
  <details v-if="activities.length" class="agent-activity">
    <summary class="activity-summary">
      <UIcon name="i-lucide-workflow" class="size-4 shrink-0 text-primary" />
      <span class="font-medium">{{ copy.activity }}</span>
      <span v-if="current" class="activity-current" role="status" aria-live="polite">
        <UIcon :name="icons[state(current)]" class="size-3.5 shrink-0" :class="{ 'activity-spinning': state(current) === 'running' }" />
        <span>{{ label(current) }} · {{ copy[state(current)] }}</span>
      </span>
      <UIcon name="i-lucide-chevron-down" class="activity-chevron size-4 shrink-0" />
    </summary>
    <div class="activity-body">
      <p class="mb-3 text-xs leading-5 text-(--django-muted)">{{ copy.observed }}</p>
      <ol class="space-y-3">
        <li v-for="activity in activities" :key="activity.id" class="activity-row">
          <UIcon
            :name="icons[state(activity)]" class="mt-0.5 size-4 shrink-0"
            :class="{ 'activity-spinning text-primary': state(activity) === 'running', 'text-red-500': state(activity) === 'error' }"
          />
          <div class="min-w-0 flex-1">
            <p class="font-medium">{{ label(activity) }}</p>
            <code v-if="activity.tool_name" class="break-all text-xs text-(--django-muted)">{{ activity.tool_name }}</code>
          </div>
          <div class="shrink-0 text-right text-xs text-(--django-muted)">
            <p>{{ copy[state(activity)] }}</p>
            <p v-if="activity.duration_ms !== undefined">
              {{ (activity.duration_ms / 1000).toLocaleString(locale, { maximumFractionDigits: 2 }) }} s
            </p>
            <p v-if="activity.result_count !== undefined">{{ activity.result_count }} {{ copy.results }}</p>
          </div>
        </li>
      </ol>
      <p v-if="!active && !hasTools" class="mt-3 text-xs text-(--django-muted)">{{ copy.noTools }}</p>
    </div>
  </details>
</template>

<style scoped>
.agent-activity { border: 1px solid var(--django-border); border-radius: 5px; background: var(--django-surface-soft); color: var(--django-copy); font-size: 0.8125rem; }
.activity-summary { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; cursor: pointer; padding: 0.75rem; list-style: none; }
.activity-summary::-webkit-details-marker { display: none; }
.activity-summary:focus-visible { outline: 2px solid var(--ui-primary); outline-offset: 3px; border-radius: 5px; }
.activity-current { display: flex; align-items: center; gap: 0.375rem; min-width: 0; color: var(--django-muted); font-size: 0.75rem; }
.activity-chevron { margin-left: auto; }
details[open] .activity-chevron { transform: rotate(180deg); }
.activity-body { border-top: 1px solid var(--django-border); padding: 0.75rem; }
.activity-row { display: flex; align-items: flex-start; gap: 0.75rem; }
.activity-spinning { animation: activity-spin 1s linear infinite; }
@keyframes activity-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .activity-spinning { animation: none; } }
</style>
